# mobile_base_control

此套件補足 spec #32／decision #22／ticket #35 已確認的 M1 裝置介接缺口。
原生 `ros2_control` 與 `diff_drive_controller` 負責差速運動學、輪端里程、速度限制與命令 timeout。
Adapter 只透過 Modbus Multi-drive2.0 交換輪端命令，以及有效速度與編碼器位置回授，
不發布 TF、不計算輪端里程。`robot_localization` 仍是唯一的 `odom → base_footprint` 發布者。

## 設定檔用途

`config/m1.yaml` 是目前唯一的啟動設定，兩個 launch 預設共同使用此檔。
它保留初期驗證的工程限制與未知韌體註記，不代表已驗收的量產設定。
已確認硬體事實與未解決項目的來源仍記錄於驗證文件。

RWF 設定記錄使用者確認的裝置路徑、名義減速比 20:1、輪半徑 0.08 m、輪距 0.555 m。
有時間上限的唯讀 FC03 證據確認通訊為 230400／8N1、左 ID2／右 ID1、速度模式 0、
命令來源 4、PDO mapping 0。速度回授單位為馬達 RPM（1 RPM/count）；
編碼器解析度 2500 pulses/rev 是另一個量，不能混用。
使用者確認左馬達正 RPM、右馬達負 RPM 對應 AMR 前進：
`left_direction=+1`、`right_direction=-1`。

實際韌體身分與量產允許限制仍未解決。Commissioning 設定使用保守的工程參數，
韌體 metadata 明記 `UNIDENTIFIED`。名義幾何不代表有效幾何已標定；
軟體測試數值不能當作部署預設。證據來源見 `docs/validation/m1-software.md`。

### 目前操作設定（2026-10-08）

Operator 選定 `cmd_vel_timeout=3600` 秒、線速度限制 `0.50 m/s`、角速度限制
`0.50 rad/s`，左右 `max_motor_rpm=1600`。
以名義輪半徑0.08m、輪距0.555m、減速比20:1計算，線／角速度同時達上限時，
較快一輪約需1525RPM。1600是選定的軟體上限，不是已確認的馬達／減速機額定上限。
原生Teleop可自行提高命令速度，controller與adapter仍依設定限制／拒絕命令。
命令靜默不會短時間自動停止；須使用明確停止命令與退出／停用流程。
未收到有效命令時，長timeout可能使原生controller維持NaN reference且無里程輸出；
靜止檢查可先透過原生Teleop停止鍵送出零速度。
下方150RPM／0.3秒等歷史結果只適用當時設定，不驗收目前完整速度或timeout範圍。

### 參數與啟停行為

`gear_ratio` 是每輪一圈所需的馬達圈數；`direction` 為 +1／-1，將正輪角映射至
正／負馬達 RPM。`feedback_rpm_per_count` 將 signed16 目前速度回授換算為馬達 RPM。
Adapter 支援已驗證的速度模式、Multi-drive2.0、PDO mapping 0／1、兩個不同的
ID（1–8），以及無 alarm 的 STOP0／RUN2／WAIT或INHIBIT6。

Status6 的量測有效，但診斷為 WARN／不可移動，並拒絕非零命令，不能視為 Teleop 可用。
Activation 先驗證無 alarm 回授、讀取 index12 目標速度、要求 ISTOP0，確認目標為零後
才要求一次 SVON6，再於時間上限內輪詢就緒與目標零。
Deactivation／shutdown 只有取得新的無 alarm 證據後，才要求 ISTOP0、SVOFF7，
並驗證 inhibited 讀回；失敗回傳 ERROR。

SVOFF 可能隱含重設 alarm：已捕捉的 fault 會阻止此動作，但無法排除讀寫之間新出現的 fault。
不執行明確 alarm reset、參數修改、STO 解除或煞車操作；復原由 Operator 處理，
不自動重新啟用。Operator 須另行建立已驗證的驅動模式與硬體條件。

### 通訊協定與限制

通訊手冊 revision1.1（2025-02-03）第 37–42 頁定義：
FC03 從 index0 讀取 status／alarm／目前速度，FC10 從 index8 寫入
Multi-drive Lite command／data，使用 drive ID bitmask 定址。

目前合併讀取 Data0–6 與每個 drive 的 Error_Check：FC03 Num16、drive stride8。
使用 status、alarm、速度與位置，中間的電壓／電流 words 不新增對外發布能力。
先前 Num8／stride4 只提供速度回授。

在已檢查的平台，每個 Error_Check 是從回應起點累積至該 drive 最後資料 word 的
Modbus CRC16，以 big endian 編碼；adapter 驗證兩個檢查值。
這由不同實機唯讀回應與固定資料測試支持，不宣稱適用所有廠商韌體。
最終 frame CRC 與錯誤處理由 libmodbus 提供。
RTU 靜默間隔至少 1.75 ms 或 3.5 個字元時間，取較長者。

手冊第 33 頁定義 signed16 JG RPM，並將低於 60 RPM 的非零命令提高至 60 RPM。
Adapter 因此拒絕這類命令，並盡力對兩輪要求零速度，避免實際速度高於要求。
平台須具備適用的減速比與命令範圍，不透過另一個運動學引擎掩蓋此限制。

## 啟動與鍵盤控制

依 repository 容器流程建置。實機 serial 裝置須映射至設定中的容器路徑，
並將裝置的主機群組加入容器的一般使用者。
此 AMR 為 `/dev/ttyUSB0`，穩定別名 `/dev/fihRobotBaseMotor`，
群組 `dialout`／GID20、權限 660。Docker 裝置映射不會自動授予 Unix 群組權限。
其他主機須確認實際群組，不直接假設 GID20。
目前 `compose.yaml` 已映射 IMU／馬達別名並加入 serial 群組；裝置可存取不等於硬體就緒。
Configure 失敗與讀回證據見架高反向驗證紀錄。

三個終端分別執行：

```bash
# 終端 1：模型與 TF；讀取設定不會開啟馬達裝置。
ros2 launch mobile_base_description description.launch.py
```

```bash
# 終端 2：啟動並啟用原生硬體與 controllers，可能 Servo ON。
ros2 launch mobile_base_control m1.launch.py
```

```bash
# 終端 3：原生鍵盤 Teleop。
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args -p stamped:=true \
  -r cmd_vel:=/base_controller/cmd_vel
```

鍵盤指令也可在 workspace 根目錄簡化為 `bash ./scripts/teleop.sh`。
此腳本只啟動 Teleop，不啟動 Description 或 Control。

檢查 controllers、輪端里程與診斷：

```bash
ros2 control list_controllers
ros2 topic echo /base_controller/odom
ros2 topic echo /diagnostics
```

Description 獨自負責完整模型與原生 `robot_state_publisher`。
兩個 launch 預設使用 Control 套件的 `config/m1.yaml`。
另一平台須在兩邊使用相同的 `hardware_config:=/absolute/target.yaml` 覆寫。
Description 加入 M1 `<ros2_control>` 宣告，不啟動硬體；Control 讀取原生
`/robot_description`，不啟動 RSP 或其他套件 launch。
Control 的 `model_file` 參數已移除，模型覆寫由 Description 負責。

只有幾何、沒有控制宣告的模型無法初始化 M1。運行中不要更換模型／設定，
也不要期待原生 topic 載入會比較兩份 YAML。
錯誤、缺失或不一致的設定是 Operator 設定錯誤，不是就緒狀態。
須保留並解決原生 logs／spawner 失敗；缺少必要模型時，Control 啟動不代表硬體／controllers 可用。

Controller 使用速度回授，`open_loop=false`、`enable_odom_tf=false`。
`/base_controller/cmd_vel` 使用 `TwistStamped`；`/base_controller/odom` 是輪端回授里程來源。
速度限制與 controller timeout 來自選定設定。

Teleop 前須取消 Navigation，等待原生任務的終止結果；Navigation 前須以 Ctrl-C 結束 Teleop。
零速度、沒有訊息、命令 timeout、controller inactive 或零值 acknowledgement，
都不能直接視為控制情境已結束或實體機器人已停止。
使用現場硬體停止方式與獨立觀察。Shutdown／deactivation 會嘗試有時間上限的停止、
停用與讀回；錯誤處理要求 ISTOP 並保留原因。通訊斷線時無法保證命令送達。

## 診斷與故障排查

使用 `/diagnostics`、原生 controller logs 與 `ros2 control list_hardware_components`。
每輪狀態包含 drive ID、設定的韌體資料、馬達 status、alarm code、回授有效性與基本原因。
通訊／CRC／短回應／timeout，以及 alarm、STO 或未知 status，會使兩輪速度／位置介面無效。
Inhibited6 的量測有效，但不可移動。
完整性錯誤使全部輪端回授無效，不把過去資料當成目前有效量測。
Controller manager 收到 ERROR 後可停用受影響 controllers。
Fault reset／煞車／STO 復原由 Operator 進行，不是 adapter 自動行為。

初始唯讀觀測中，兩輪為 WAIT／INHIBIT6、alarm0、RPM0。
後續有時間上限的零速協定驗證確認 SVON 使兩輪進入 STOP0，SVOFF 回到6，
全程 alarm0／目前RPM0／目標0。
預期移動前須確認主電源／CTRL 電源及 SERVO ON 條件；controller active 不等於 Bringup／Teleop 就緒。
實機通訊 watchdog `05-17=0` 為停用，斷線或程序消失時不能依賴 drive watchdog 停止。

Launch 拒絕平台參數時，從權威證據補齊。Serial 失敗時檢查映射、權限與通訊設定。
速度／status 讀取失敗時檢查 Multi-drive2.0 模式、IDs／bitmask 與適用韌體／手冊版本。
命令被拒絕時檢查最低 RPM、減速比／方向與速度限制；理解原因與硬體條件後才恢復。

## 驗證證據界線

軟體測試在外部 serial 邊界使用 pseudo-terminal Modbus peer，搭配真實原生 controller
與公開 ROS topics；幾何、IDs、RPM、timeout 為受控測試輸入。
有時間上限的協定測試驗證正負尺度／方向、最低速度拒絕、fault／STO 無效性與 inhibited 狀態。
即使最終 Modbus CRC 正確，prefix check 損壞仍會被拒絕。
這些不驗證實際韌體相容、編碼器回授、輪向、位移、實體停止或經標定里程。

**REQUIRES HARDWARE VALIDATION（需要硬體驗證）：** 平台啟動、有效輪端回授、
移動方向／位移、alarms／斷線、timeout／shutdown 停止及 Teleop 交接。
**REQUIRES CALIBRATION（需要標定）：** 有效輪半徑／輪距、有效減速比／尺度／極性、
限制／timeout 與後續里程性能。實際版本與結果記錄於驗證文件；軟體完成不等於硬體驗收。

Commissioning 可選參數 `controller.native_hardware_execution_budget_us` 將平均值／標準差的
WARN／ERROR 微秒門檻交給原生 controller-manager 硬體診斷。
省略或 `null` 保留 upstream 預設。統計門檻不證明 deadline；週期／overrun 診斷仍啟用，
真正的 ERROR 阻止 commissioning 動作。RS485 時序依據與中斷造成的歷史暫存資料遺失見驗證紀錄。

一次架高 0.1 m/s、兩秒測試由現場確認兩輪前進並停止；暫時 300 RPM／0.1 m/s 設定與
原始證據已封存。較早 0.03 m/s 測試沒有觀察到輪子移動；2026-10-07 另行進行
0.03 m/s、兩秒與十秒測試，Operator 確認輪子移動並停止。
歷史症狀未重現，原因仍未知。命令停止發布的獨立證據支持原生 timeout 在清理前歸零，
但實體 timeout 停止的獨立時間確認仍未解決。
詳見 `docs/validation/m1-low-speed-timeout-20261007.md`。
Repository commissioning 設定維持 150 RPM／0.03 m/s；上述測試不建立最低可靠速度、
量產限制、經標定里程，或斷線／單獨 timeout 的實體停止驗收。

## 真實輪角回授

已確認的 mode0 Index／Pos 回授修正
`docs/validation/real-static-estimation-20261007.md` 記錄的位置缺失／NaN 問題。
同一個 Multi-drive read 取得 Data0–6 與各 drive prefix check；只有一個 serial owner，
不新增 runtime TF 或 JointState publisher。
完整底座至輪子 TF 還需要模型處理中間輪座。
V1 Description 使用 Operator 確認的名義固定輪座；M1 不量測懸吊位移。
原生 JointState broadcaster 發布位置，原生 RSP 消費該資料。
原生 diff_drive_controller 仍使用速度回授（`position_feedback=false`），里程責任不變。

設定須提供 `position_format: 0`、每輪的 `position_steps_per_motor_revolution`
與 `encoder_pulses_per_motor_revolution`。
Configure 在 Servo ON 前讀取各 ID 的實際 `02-14` 與 `01-06`，不一致就拒絕。
僅支援已驗證的 mode0，不猜測 mode1。
RWF commissioning 使用每馬達圈 10000 steps、單相編碼器 2500 pulses，
依據實際 registers 與分數進位檢查，不代表獨立機械標定。

第一個有效樣本使用裝置 counter 原點，不是標定後的機械輪角零位。
後續 signed16 Index 進位由真實 count 差值展開。
Pulse 超出範圍，或跳變超出設定 RPM 與有限回應時序容差，會使所有輪端回授無效，
並鎖存 position fault，直到明確重新 configure。
運行中偵測到 reset 不會默默重設參考；若 reset 差值看似合理移動，協定無法區分。
電源／reset 復原須明確進入新的 configure 階段。
運行中不要修改 drive 格式或 encoder 參數；configure／reconnect 建立新的裝置原點參考，
不宣稱跨 reset 連續性。實體 signed-index overflow 與斷電 reset 行為尚未硬體驗收。

## 套件與驗證階段（2026-10-07）

此套件取代 `mobile_base_m1`，plugin 為 `mobile_base_control/M1System`。
協定與公開原生 Control 流程測試保留在本套件，先獨立啟動同設定的 Description，
再使用已安裝的 `m1.launch.py`；測試可透過明確 `hardware_config` 提供受控設定。
核心裝置驗收先於 #38 局部估測整合，以及 #39／#41 產品 Bringup。
此元件入口不提供經標定 covariance 或已接受的正式部署模型。
