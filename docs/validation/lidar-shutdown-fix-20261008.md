# #37：原生 LiDAR 關閉修正與有界驗收

平台：AGX Thor、Ubuntu 24.04、ROS 2 Jazzy、Fast DDS。未切換或測試 Cyclone DDS。

## 決策與根因

採用 SICK 3.9.0，固定 commit `a562c5d098de21f6284359f4dfea97e93bd2b4d5`，
只修正已取得因果證據的 ROS 2 standalone caller 關閉路徑。
原生 apt 套件保留為依賴／比較基線；實際 executable 由 source overlay 提供。
Docker build 檢查 commit、patch 可套用性，並在 `source-version.txt` 記錄 patch SHA256。

1. 全域 static diagnostic updater 保留 ROS node 到程式靜態解構，觸發本平台 Fast DDS teardown 崩潰。
   scanner workers 停止並 join 後、main 返回前，明確釋放 updater。
   原始最小與同版未修改 source 的 RED/GREEN 證據見 [初始診斷](lidar-shutdown-diagnosis-20261008.md)。
2. 原生自訂 asynchronous signal handler 中等待 worker，可能中斷持有 DDS mutex 的主執行緒，
   同時 worker 等待該 mutex，形成死鎖。gdb 堆疊包含 signal handler、thread join 與 rmw_create_service。
   保留 rclcpp deferred signal handling，以 Context pre-shutdown callback 在 context 有效時停止並 join scanner；
   跨執行緒停止旗標改為 atomic。修正後早期 SIGINT 12 輪／24 children 全正常退出。

沒有關閉診斷、吞掉 crash、加入 restart、scan 重寫、merger、額外 TF node 或產品 Bringup。

## 最終映像與實機驗證

- 驗證 image：`sha256:566d8ff74d6b82a2d112451298c45bcb19b41d5e72bdc62cf3f21fc2273dc552`。
- Patch SHA256：`4d6039faf162af3f204283cd5f49c1e126f5f2f0459dfe1a91b651466261f3f4`。
- 實際 prefix：`/opt/mobile_base/sick_scan_xd/sick_scan_xd`；child argv 指向該 prefix。
- 隔離驗證容器不映射馬達或 IMU，不發送馬達指令；實機 LiDAR domain 196。
- Description 與 Perception 獨立 launch，三輪各 25 秒：兩台各約 25 Hz、每輪約 614 筆 scan，
  原生 `/lidar/fl/scan`／`/lidar/br/scan`、`base_lidar_link_FL_1`／`base_lidar_link_BR_1`、BEST_EFFORT 不變。
  穩定期間 timestamps 無倒退，每筆 scan 都可取得 base_footprint 到 scan frame 的 TF。
  唯一固定 TF owner 是 RSP，三輪六個 children 均正常退出，沒有 controller_manager。
- 原生 SOPAS serial readback：FL `25350157`、BR `25450354`。
  以原生服務停止 FL ScanDataEnable，再 Run，觸發真實 native UDP timeout／reconnect；
  FL 最大 gap 10.120 秒，恢復後收到 373 筆；BR 持續收到 626 筆，最大 gap 0.044 秒。
  兩個 children 正常退出。這是資料流中斷，不等同實體拔線或 power-cycle。
- 串流中的 SIGTERM：再觀察 25 秒後，從 launch log 取得兩個 native child PID 並核對 cmdline，
  直接向兩個 children 發送 SIGTERM；兩個 children 與自然結束的 launch parent 均正常退出。
  初始探針的 proc children 不可用及 parent 清理競態紀錄保留；不是 driver 新補丁。

## 軟體驗證與測試環境問題

- 正式 image 的 launch tests 11 項通過，包括三輪無輸入 SIGINT 正常退出。
- workspace 四套件 build 通過；Perception 24 項、Control workflow 35 項、Description 與 Control unit tests 通過。
- 首次全套測試有一項既有 Bringup map_server change_state future timeout；
  該輪與實機觀察共用 domain 196。獨立 domain 96 重跑 Bringup，10 項通過。
  最終 colcon 彙總 77 tests、0 errors、0 failures。保留首次失敗，不宣稱已證明 timeout 根因。
- 原先未 drain 的 stdout PIPE 會填滿，測試改用檔案記錄；native passive 無輸入會反覆重建 services，
  所以參數測試使用有來源／授權記錄的官方 compact fixture loopback，關閉測試仍保留無輸入場景。
- 先前 debug 容器混用 root／一般使用者造成 ROS log 權限失敗；最終驗證使用乾淨非 root 容器。
  這些 fixture 問題不能計作 driver runtime regression，也不能用 fixture 取代實機證據。

## Review 與範圍

比較基準由使用者指定為 `dce855a`，review 使用 staged prospective diff。

### Standards

0 項硬性違規；1 項非阻擋 heuristic：兩個測試重複 logfile／停止／child-exit assertions。
目前兩種場景不新增共用抽象；日後增加場景時再評估。

### Spec

0 項確定實作偏差；提出的 SIGTERM proof gap 已由串流中的 native SIGTERM evidence 補足。
沒有宣稱早期啟動期間的 SIGTERM 已驗證。
既有 catch、C API、其他執行路徑、精確 calibration、實體 power-cycle、長時間運行尚未完整驗證。
本次通過不代表量產可靠性或全部 V1 驗收；#37 的剩餘硬體驗收仍應明確保留，不移除 #38 dependencies。

最終原始 logs、腳本、provenance、失敗與修正證據存於 `artifacts/lidar-shutdown-fix-20261008.tar.gz`；
SOPAS access token 已遮蔽。初始探針與最終 image 證據分開，不以初版綠燈代替最終修正版。
Artifact SHA256：`540a21ff3ed6d5e9a96c21e632dba5c6342288b3ac26d1a2c9415310d8319af0`。

完成上述驗證及 review 後已重新建立正式 `mobile_base` 開發容器；核對 image ID、
`ros2 pkg prefix sick_scan_xd` 與 `source-version.txt` 都指向本次驗證版本。
預設只執行 sleep，沒有自動啟動 Perception、Control 或馬達。

官方來源：[SICK caller](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_generic_caller.cpp)、
[Jazzy rclcpp signal handling](https://github.com/ros2/rclcpp/blob/28.1.16/rclcpp/src/rclcpp/signal_handler.cpp)、
[Context pre-shutdown ordering](https://github.com/ros2/rclcpp/blob/28.1.16/rclcpp/src/rclcpp/context.cpp)。
