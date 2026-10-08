# 原生元件修正的建置

目前 `sick_scan_xd` 與 `slam_toolbox` 使用固定上游原始碼加 downstream patch；
launch 使用 base image 的原生套件加下述最小 source patch。其他 ROS 套件維持 apt 安裝。

- Upstream：SICKAG/sick_scan_xd，3.9.0。
- Commit：`a562c5d098de21f6284359f4dfea97e93bd2b4d5`。
- Patch：`patches/sick-scan-xd-shutdown.patch`。
- 初始化中止：`patches/sick-scan-xd-stop-during-init.patch`。
- 安裝 prefix：`/opt/mobile_base/sick_scan_xd`。
- 執行環境：Fast DDS，沒有切換 RMW。

## 修正責任

V1 元件需能正常停止並再次啟動。原生版本以 static shared_ptr 保存 diagnostic updater，
同時保留 ROS node；在本平台的程式靜態解構階段釋放它，會觸發 Fast DDS teardown 崩潰。
patch 增加明確釋放入口，在 caller 已停止 scanner 並 join worker 後執行。
另外保留 rclcpp 的原生 deferred SIGINT／SIGTERM handler，使用 Jazzy 的 Context
pre-shutdown callback，在 context 仍有效時通知 scanner 停止並 join。
停止旗標使用 atomic bool，供 callback 與 scanner workers 跨執行緒讀寫。
不在 asynchronous signal handler 中等待 worker 或操作 middleware 資源。
此修改針對另行取得的死鎖堆疊：主執行緒持有 DDS mutex 時被 SICK handler 中斷，
handler 等待 worker，而 worker 也等待 middleware mutex。
保留執行期间的 updater／重連行為、native topics／frames／QoS／診斷，不增加 ROS node。

範圍是 ROS 2 Jazzy standalone caller 的 SIGINT／SIGTERM 關閉路徑；既有 catch 路徑、C API、其它 driver execution paths
沒有因本修正獲得完整驗證，不宣稱上游全部資源生命週期均已修正。
因果證據見 [診斷紀錄](../docs/validation/lidar-shutdown-diagnosis-20261008.md)。

## 更新

Docker build 檢查 tag 實際 commit，patch 無法套用時會失敗，不會靜默使用未修正版。
安裝目錄的 `source-version.txt` 記錄 commit 和 patch SHA256；apt package inventory
只表示已安裝 binary 套件，不能用來宣稱目前執行的 SICK executable 來自 apt。
以 `ros2 pkg prefix sick_scan_xd` 與 native child command line 核對實際來源。

若上游發布相同問題的正式修正，應比較 source、重跑公開 shutdown regression 與
雙光達資料／TF／reconnect 回歸，再決定更新或恢復 binary install。
不得僅移除 patch、吞掉 crash、加入自動 restart 或以 SIGKILL 冒充正常退出。

## launch 的 SIGINT 事件排程修正（#51）

Python 的預設 SIGINT handler 會同步拋出 `KeyboardInterrupt`。原生
`LaunchService.run()` 捕捉例外後重跑 event loop，但例外若打斷 asyncio
callback 排程，可能遺失消費 Shutdown event 的 task wakeup。此時 launch
已收到 SIGINT，卻不會通知 child；增加 timeout 不能修正遺失的排程。

`patches/ros-launch-sigint.patch` 只在 `LaunchService.run()` 期間，且 caller
使用 Python 預設 handler 時，避免同步例外；SIGINT 仍透過原生
`AsyncSafeSignalManager` 的 wakeup fd 在事件迴圈內處理並轉送 child。
`finally` 還原原 handler，caller 自訂的 handler 保持其責任。
這不是忽略停止訊號，也不新增 launcher wrapper 或監控 node。

Docker build 先核對 `launch_service.py` 的 SHA256（與官方 3.4.8 相同），
再套用 patch；原生 source 改變時 build 會失敗，需重新研究與驗證。
`/opt/mobile_base/launch/source-version.txt` 保存 patch 與修正版檔案 SHA256。
package inventory 仍表示 binary 基線，不能代替該檔案的來源紀錄。

回歸測試在實際 `LaunchService` 與 asyncio 的 task wakeup 排程邊界注入
SIGINT，驗證停止事件不遺失、child 正常退出及 handler 還原：

```bash
python3 -m pytest docker/test/test_launch_shutdown.py -q
```

自然重現、binary 升級的反證與驗證界線見
[研究紀錄](../docs/research/lidar-middleware-shutdown-20261008.md)。

## LiDAR 初始化途中停止（#51）

原生 `MsgPackThreads::runThreadCb()` 可能已進入重新初始化的外層迴圈，
隨後收到停止要求，使內層 UDP receiver 建立迴圈被跳過；此時 receiver
仍為 null，原版卻繼續建立 converter 並存取 `udp_receiver->Fifo()`。
自然 SIGINT 的 GDB stack 與固定時序注入都重現相同的 null dereference。

`sick-scan-xd-stop-during-init.patch` 只在 UDP receiver 建立迴圈後、IMU
receiver／converter 建立前，檢查是否有 receiver。沒有時結束工作迴圈，
走既有 join／cleanup；不改變正常初始化、資料、重連或 TF 的責任。

回歸測試使用 AArch64 GDB 與該原生 logging seam 固定停止時序，並讓
真正的 SIGINT／context shutdown 執行。GDB 是除錯／測試依賴，不加入
正式 image 的 runtime 依賴；缺少 GDB 或平台不符時此項明確 skip：

```bash
python3 -m pytest docker/test/test_native_receiver_shutdown.py -q
```

Docker build 同樣核對 pinned SICK commit、檢查 patch 能否套用，並記錄
patch SHA256。兩項 #51 修正是不同故障的補足，不能以 launch 測試通過
替代 native driver 的初始化／停止驗證。
