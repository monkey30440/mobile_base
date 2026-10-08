# #37：Fast DDS 下的 LiDAR 關閉崩潰診斷

平台：AGX Thor、Ubuntu 24.04、ROS 2 Jazzy。正式 runtime／Compose 未因本次診斷更動；未安裝或測試 Cyclone DDS。

## 結論

CONFIRMED：`sick_scan_xd` 3.9.0 的全域靜態診斷 updater 保留 ROS node，直到程式的靜態解構階段才釋放。在目前 Fast DDS 環境，這個生命週期順序會觸發退出崩潰。顯式在掃描執行緒完成後、`main` 返回前釋放 updater，可消除本次最小與單光達重現案例的崩潰。

這份初始診斷當時不是已完成正式修正，也不代表所有 Fast DDS／SICK 關閉問題都已排除。
後續交付與有界回歸見 [修正驗收](lidar-shutdown-fix-20261008.md)；#37 的剩餘硬體驗收仍保留。

## Evidence

- 已安裝 `sick_scan_xd`：`3.9.0-1noble.20260902.160847`；`rmw_fastrtps_cpp` 8.4.4；Fast DDS 2.14.6。
- 正式雙光達啟停三輪：launch parent 均 0，但六個 native children 全部以 −6／−11 結束。不能僅使用 parent exit code 作為驗收。
- 無硬體流量的單一 native driver 在 SIGINT 後也重現。gdb 顯示 discovery listener 位於 `DataReaderHistory::get_first_untaken_info`／`__rmw_wait`，main 同時在退出階段解構 `diagnostic_updater` node、執行 `rmw_destroy_node`。
- 最小 C++ 案例不含 SICK 或硬體：全域持有 updater 到靜態解構，3/3 abort；在 shutdown 前釋放，3/3 exit 0；shutdown 後但 main 返回前釋放，3/3 exit 0。
- 再移除 updater、只保留全域 ROS node：晚釋放 3/3 abort，main 返回前釋放 3/3 exit 0。因此不能把缺陷只歸因於 diagnostic_updater 本身。
- 上游 tag 3.9.0，commit `a562c5d098de21f6284359f4dfea97e93bd2b4d5`：`sick_scan_common.cpp` 的 `s_diagnostics_` 為 static shared_ptr，沒有顯式 reset。
- 同版未修改原始碼 build，FL 實機三輪 SIGINT：3/3 SIGSEGV。
- 隔離因果探針只增加釋放函式，於 caller 的 `joinGenericLaser()` 後 reset 全域 updater：相同 FL 實機三輪，3/3 exit 0，日誌確認收到 scan。探針未部署至正式 image 或 repository runtime。
- 查核上游 develop，同一 static ownership 仍存在；未找到可直接採用的已發布修正。這不是證明所有上游 branches 都不存在修正。

## 另一個獨立的測試問題

Passive native launch 測試原先使用未讀取的 stdout PIPE。probe 實測 63,800／65,536 bytes，參數 future 無法完成；持續 drain 同一 pipe 後原 future 完成，確認 log backpressure 是阻塞原因。

測試改用檔案記錄並隔離案例 ROS_DOMAIN_ID 後，完整 Perception 21 項通過。DDS domain 隔離是測試 fixture 改善，尚未單獨證明它是其餘偶發 discovery 問題的根因。綠燈測試不代表 native 關閉崩潰已修正。

## 後續

保留 Fast DDS。正式處理須讓 ROS 物件在有效生命週期內明確釋放，採可追溯的 upstream 修正／build，不以 restart、吞錯、強制 kill、關掉診斷或修改 scan／TF 掩蓋問題。完成正式交付及雙光達回歸後才能關閉 #37。

原始 log、最小 C++、精確探針 diff、重現腳本與結果：[artifact](artifacts/lidar-shutdown-diagnosis-20261008.tar.gz)。

官方 source：[SICK 3.9.0 common](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scan_common.cpp)、[caller](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_generic_caller.cpp)。
