# 原生 LiDAR 修正的建置

目前 `sick_scan_xd` 使用固定上游原始碼加 downstream patch，其他 ROS 套件維持 apt 安裝。

- Upstream：SICKAG/sick_scan_xd，3.9.0。
- Commit：`a562c5d098de21f6284359f4dfea97e93bd2b4d5`。
- Patch：`patches/sick-scan-xd-shutdown.patch`。
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
