# Control 長 timeout 停止驗證（2026-10-08）

Operator 明確保留 m1.yaml：cmd_vel_timeout3600秒、線／角速度限制0.50，motor ceiling150RPM。
本次沒有實體轉輪或Servo ON，只使用pseudo-terminal Modbus peer與原生controller。

## 軟體結果

指令：pytest test_workflow.py -k 'long_timeout or native_hardware_deactivation_stops or native_launch_shutdown_stops'。
最終3passed、31deselected，12.62秒。

新增3600秒timeout案例：先在controller可接收後明確發布零速，模擬非零命令後
靜默0.7秒仍保留非零；明確零速後命令歸零；再次模擬非零後SIGINT關閉Control，
peer最後targets[0,0]且disabled，觀測SVOFF7、未alarm reset。
另兩項既有測試驗證native hardware deactivation與launch shutdown。
測試幾何／RPM等是既有受控fixture，不驗收現行0.50速度或真實尺度。
沒有等待3600秒，也沒有加速時鐘跨過3600秒；一小時到期邊界仍未驗證。

首次新增案例在startup等待odom失敗：controller在尚無有效command時回報NaN reference。
單筆零速亦因activation時序不足而未初始化。改為有上限地發布零速直到取得odom，
再執行案例後通過。此修改只在測試fixture，不新增runtime自動命令publisher。
原生長timeout初始化需有效命令；靜止驗證可用原生Teleop停止鍵送出零速。

## 實機唯讀結果

讀取前無controller／motor serial owner。只送FC03，2026-10-08T02:29:26Z讀回：
ID1與ID2皆status6／alarm0／目前RPM0；index12兩輪target0。
完整frame與per-drive CRC通過。此為當下靜止證據，不是實體停止過程驗證。

## 界線

未驗證實機Teleop退出／Control關閉時的輪子停止過程、物理timeout時序或通訊失聯停止。
不關閉#35、不移除#38依賴。現行設定的歷史0.3秒timeout證據仍不適用。

## 後續實機 Teleop 驗證

Operator確認仍架高且在旁可立即停止後，以當時150RPM上限、3600秒timeout，
執行兩段原生鍵盤測試。使用scripts/teleop.sh，原生z鍵27次將0.5m/s降至
0.0290748685m/s，各段約2秒。不直接以0.5m/s測試，不修改drive參數。

第一段k停止鍵：命令歸零、兩輪新鮮回授歸零，觀測約0.144秒。
第二段原生Ctrl-C退出：捕捉退出零命令、两輪回授歸零，觀測約0.173秒。
兩個數值是此次工具觀測延遲，不是最壞情況或實體目視停止deadline。
Teleop／Control／Description全部exit0；Control log保留hardware lifecycle清理。
獨立FC03在2026-10-08T02:33:52Z確認ID1/2 status6、alarm0、目前與目標RPM0。
未取得Operator對這兩段物理停止的另外回覆，不把馬達回授當作獨立目視證據。

全Control軟體套件34 ROS案例＋4 C++案例通過，colcon報告42計數（含wrappers／
既存其他套件結果），0errors/failures/skips；不宣稱42個Control實際案例。

原始observer、公開topic traces、native logs與當時profile封存於
[artifacts/control-teleop-stop-20261008.tar.gz](artifacts/control-teleop-stop-20261008.tar.gz)。
封存程式是歷史證據，不是可直接無人執行的操作入口。

## 1600RPM修訂

隨後Operator同意左右software ceiling1600RPM；3600秒／0.50m/s／0.50rad/s保留。
名義最大組合要求1524.903RPM，安裝設定範圍檢查與6項相關測試通過。
上述實機低速停止trial發生於150RPM設定，不能當作1600RPM滿速驗收。
參考PELB的02-01=3000RPM只在來源0/2/3生效，而目前来源4；
01-04=4188RPM為無載參考轉速。1600是Operator選定software ceiling，硬體額定上限未知。
#35仍有現行滿速範圍、3600秒邊界、獨立物理停止／尺度及適用故障證據待核對。

## Operator補充確認

Operator後續明確回覆「兩段都有轉動，最後都停止」，因此本次低速k停止鍵與
鍵盤退出都有獨立現場停止觀察。此確認補足上方等待回覆的項目，不擴張為
1600RPM滿速、timeout-only或失聯物理停止驗收。

## 3600秒命令年齡邊界與權威模型補充

新增test_3600_second_command_age_boundary，使用真实native controller與模擬Modbus：
cmd_vel_timeout3600秒，publish stamp為當下減3598秒。
到期前至少一秒維持非零，約兩秒後歸零；斷言1.8–3.0秒內收到零命令。
單項通過，4.57秒。沒有修改runtime clock，沒有實機動作；驗證的是命令stamp年齡
達3600秒的native timeout行為，不是連續運行一小時的可靠性。
本結果補足先前未驗證的timeout年齡邊界。

原始權威URDF中driving_wheel_joint_L/R均有limit velocity15.7rad/s。
以Operator確認gear20:1換算約2998.5motorRPM；1600RPM對應8.378rad/s輪速，
低於模型宣告。這支持名義軟體範圍，不等於實際馬達額定／負載或量產最高速度驗收。
先前僅檢查PELB/driver手冊而稱完全沒有範圍依據的說法不完整，以上補正。

## 實際平台不一致 — 待Operator決定

/proc/device-tree/model實際回報NVIDIA Jetson AGX Thor Developer Kit，uname aarch64。
容器Ubuntu24.04.3；controller_manager4.48.0、diff_drive_controller4.42.1、libmodbus3.1.10。
目前不能將此主機上的測試宣稱為AGX Orin平台驗收。
#35原acceptance指定AGX Orin；需Operator確認是正式平台修訂，或開發／測試主機。
未關閉#35或解除#38 dependency，也未更改V1 hardware facts。
