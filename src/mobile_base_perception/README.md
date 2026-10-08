# mobile_base_perception

負責最小必要的 USB IMU adapter，以及可重用的原生雙 picoScan 設定，取代
`mobile_base_imu` 與 `mobile_base_lidar`。整併不新增 LiDAR 解碼器、scan 合併器、
TF publisher 或融合引擎。IMU 執行檔仍為 `usb_imu`，Python 模組改為
`mobile_base_perception.node`；既有 raw topic／frame 保留。V1 零偏補償另提供
`/imu/data`，責任與操作見下方標定章節。

## 獨立啟動與設定

在已配置硬體存取的容器內，分別執行：

```bash
ros2 launch mobile_base_perception imu.launch.py
ros2 launch mobile_base_perception dual_picoscan.launch.py
```

這些指令會開啟 IMU 裝置或啟動、設定 LiDAR，不是無硬體的檢查指令。
只檢查 launch 參數時可加上 `--show-args`。每個裝置只能啟動一個 driver；
這些 launch 不會啟動馬達 controller。

兩個 launch 分別預設讀取套件內的 `config/imu.yaml` 與 `config/lidar.yaml`。
也可明確指定其他設定檔：

```bash
perception_share="$(ros2 pkg prefix mobile_base_perception)/share/mobile_base_perception"
ros2 launch mobile_base_perception imu.launch.py imu_config:="$perception_share/config/imu.yaml"
ros2 launch mobile_base_perception dual_picoscan.launch.py lidar_config:="$perception_share/config/lidar.yaml"
```

`imu.yaml` 是 `usb_imu` 節點的原生 ROS 參數 YAML；`lidar.yaml` 是雙 LiDAR launch
參數的平面對應表。使用 `colcon build --symlink-install` 建置後，可直接修改
`src/mobile_base_perception/config/*.yaml`，再重新啟動對應 launch，不需重新建置。
執行中的 driver 不會自動重新載入設定。

相對路徑以執行指令時的工作目錄為準，並支援展開 `~`。缺檔時啟動失敗，不會選用
備用設定。原生 ROS 載入、驗證 IMU YAML，adapter 再驗證其參數；LiDAR launch
解析設定後，仍保留原生 driver 的驗證。LiDAR 命令列參數可覆寫個別 YAML 設定，
也保留完全以命令列提供設定的方式。未指定 echo／時間選項時，維持 LAST／mode1。
套件設定是可安裝的設定範例，不具備即時重新載入功能。

IMU 封包格式與 baud 已有實機被動觀測證據；韌體身分、獨立單位／軸向驗證與標定
仍有既有證據限制。0.3 秒 timeout 是初期驗證設定。raw covariance 使用既有
commissioning second moments，包含當時 bias；corrected 使用人工標定檔的
session dispersion，不能當成全溫度／長期 uncertainty。
LiDAR IP／port 必須符合實際網路，原生關閉與長時間時序驗收仍未完成。
不同平台或經驗證的調整可使用另一份設定檔。

Perception 只啟動自身的感測器節點。手動檢查模型與 scan 時，先獨立啟動
`mobile_base_description description.launch.py`，再於各自終端啟動 IMU 或雙 LiDAR；
需要時另外啟動原生 Foxglove bridge。先前的 `sensor_model` 組合 launch 已移除。
原生 SICK TF 與內建 IMU 維持停用，由 Description 負責安裝與 scan transforms。
兩個正式 scan 都使用 LAST echo 與原生 `_1` frames。核心套件驗收仍先於 #38 整合，
以及 #39／#41 產品 Bringup。

以下協定與歷史觀測保留原本的證據範圍。目前模型中的 IMU 安裝為 yaw +90°；
下方有日期的零 rpy 觀測發生於 Operator 修訂之前。Adapter 軸向設定與實體
軸向、尺度、標定仍須有適用的證據。

## IMU 零偏標定與固定補償（#50）

**IMU 零偏**是實體靜止時，角速度量測仍有非零平均值；它不是雜訊大小。
**固定補償**是在相同 IMU frame／rad/s 中減去人工標定並審查保存的三軸零偏。
運行時不自學習、不加 deadband、不把小角速度歸零；安裝旋轉仍由模型負責。

保留 `/imu/data_raw`；原生 EKF 使用 `/imu/data`。未提供有效標定檔時 raw 可供
標定／排查，但 corrected 不發布，diagnostics 顯示 WARN 與原因。Mapping／
Navigation 必須確認 corrected 持續更新，不能只因 EKF 有輸出就宣稱可使用。
Transport／packet 異常仍是來源 ERROR，不被 calibration warning 蓋掉。

預設 `imu.yaml` 的 `calibration_file: imu_calibration.yaml` 相對於**選定的
imu.yaml 所在目錄**解析；支援絕對路徑與 `~`。這與 `imu_config` 本身相對
目前工作目錄解析不同。缺檔／解析失敗／frame、units、來源或數值不符時不猜測
bias，不改 raw，不用零 bias fallback；修正後需重新 launch，不支援 hot reload。

### 人工流程

Operator 必須確保整段採集期間實體靜止；gyro 小值不能證明車沒動。
先保持馬達停用、底座靜止，啟動 IMU，不需 Description／Control／EKF：

```bash
ros2 launch mobile_base_perception imu.launch.py
```

另一容器 terminal，工作目錄 `/workspace`：

```bash
ros2 run mobile_base_perception calibrate_imu --stationary \
  --output src/mobile_base_perception/config/imu_calibration_new.yaml
```

工具只訂閱 `/imu/data_raw`，預設採集 60 秒、至少 200 筆；這是可調整的
commissioning 起始 window，不是暖機完成或量產精度保證。`--duration`、
`--min-samples`、`--wait-timeout`、`--max-gap` 可明確調整；詳細見 `--help`。
拒絕缺資料、非有限值、錯誤 frame、時間不連續／資料 gap、不足樣本及無法量得
三軸 dispersion；不發送任何裝置／馬達命令。

輸出 YAML 記錄 frame、rad/s、來源、UTC 日期、樣本數／時間與三軸 bias／variance。
Operator 審查採集期間確實靜止與來源／數值後，在 `config/imu.yaml` 將
`calibration_file` 改為 `imu_calibration_new.yaml`，停止 IMU，再重新 launch 套用。
既有檔案**不覆寫**。重新標定時輸出另一個檔名，審查後修改 `imu.yaml` 的
`calibration_file` 指向新檔；不以刪掉既有證據作為預設流程。
本平台已附 `imu_calibration.yaml` 的實測 commissioning 結果，只適用記錄的
裝置／條件；新裝置不能直接當成自己的標定。上述命令使用新檔名，若該檔
也已存在，必須另選名稱並同步更新 `calibration_file`。
開發 symlink-install 的 `imu.yaml` 解析到 source 目錄；上述 output 是其相鄰檔。
其他部署使用選定 config 目錄的可寫檔案或絕對路徑，不必寫入唯讀安裝目錄。

```bash
ros2 topic echo /imu/data_raw --once
ros2 topic echo /imu/data --once
ros2 topic echo /diagnostics
```

標定檔只在啟動時載入。原始角速度／stamp／frame／acceleration 保留；corrected
僅固定減去 bias 並提供同條件 dispersion，orientation 仍 unavailable。
這不是完整 bias uncertainty／covariance 標定：樣本可能相關，跨溫度、長期 bias
與 firmware 開機校正皆需另外量測。不可任意調大 covariance 掩蓋 drift。
裝置、firmware、輸出尺度／axes、安裝或靜止殘差改變時，Operator 重新判定與標定；
同一 frame 名稱不能證明同一硬體，檔案數值檢查不能自動檢出所有語意配錯。

驗收使用未參與標定的較長靜止資料、正／負慢速旋轉及重新啟動的重用結果。
報告 drift 與實際條件，不承諾 odom 絕對無漂移。不要把車動作當成標定輸入。

## USB IMU adapter（#36）

此獨立 V1 adapter 依據
`reference/tdk_ros2_imu/HandBoard_IMU_V1_Quick_Guide.md` 的 HandBoard V1 協定：
59 bytes、AA55 標頭、14 個 little-endian float32，以及 bytes 0–57 的 XOR 檢查。
使用加速度索引 0–2、角速度索引 5–7，拒絕錯誤標頭、檢查碼及所有非有限封包數值。
可重新同步任意讀取區塊；每次 poll 後最多保留 58 bytes，每次讀取上限為 4096 bytes。

不匯入 reference implementation；該實作過去的驗證不能代替此 adapter 的證據。
不使用橋接器推算的角度，也不提供融合或 TF。

### 參數與運作

傳輸、轉換與 timeout 所需資料都必須由設定提供。Runtime 不自行猜測 serial 路徑、
baud、韌體協定、尺度、安裝軸向或 sample timeout。預設 launch 載入的 YAML
提供這些參數；參數缺失或無效時，`/diagnostics` 回報 ERROR，不開啟 port、不發布量測。

| 參數 | 意義 |
|---|---|
| `port` | 實際可存取的穩定 USB serial 路徑；此平台使用 `/dev/fihRobotBaseIMU`，容器映射屬於操作環境設定 |
| `baud` | POSIX 支援的 serial baud；指南範例為 115200，實際平台仍須驗證 |
| `protocol_profile` | 確認平台韌體符合指南後才使用 `handboard_v1` |
| `acceleration_scale` | 每個封包單位對應的正有限 m/s²；指南以 g 表示，使用 9.81 轉換 |
| `gyro_scale` | 每個封包單位對應的正有限 rad/s；指南以 deg/s 表示 |
| `axes` | 保持右手座標系的帶正負號排列；每個 ROS 輸出軸選取裝置軸 1／2／3。非軸對齊安裝應由硬體／frame 設計處理，不在此近似 |
| `sample_timeout` | 距離最後有效量測的正有限秒數，須依實際資料流與使用端需求選定 |

輸出 `imu/data_raw` 為 `sensor_msgs/Imu`，frame 為 `base_imu_link`。
時間戳使用 ROS 主機接收時間；封包沒有感測器採樣時間戳，延遲與同步尚未驗證。
Orientation covariance 第一項為 -1（不可用）；加速度 covariance 全零（未知）。
角速度 covariance 預設也全零，遵循 ROS 未知 covariance 的慣例。

可選的 `angular_velocity_variances` 是恰好三個元素的 ROS double array，對應已發布的
`base_imu_link` x／y／z 軸，單位為 `(rad/s)^2`，已完成單位與軸向轉換。
YAML 請使用浮點數。全零表示未知；非零設定必須全部為正有限值。
混合零值、負值、非有限值或長度錯誤會在開啟 serial 前拒絕設定。
數值僅填入 covariance 對角索引 0／4／8，非對角元素為零。
Adapter 不會再次縮放、排列這些變異數，也不驗證標定。
估測端不得假設已具備標定 covariance 或 orientation。

原生 `diagnostic_updater` 提供 port／profile、錯誤封包數、有效樣本數、樣本年齡、
時間／covariance 限制，以及設定、通訊、封包／資料與有效樣本 timeout 錯誤。
後續有效樣本可恢復封包／資料狀態，計數器仍保留紀錄。
斷線或開啟失敗時須修正原因並重新啟動節點；不會自動改用其他 port、重試或發布快取量測。
「有效橋接樣本」只表示設定的解碼器接受該樣本，不代表硬體健康或已標定。

### 軟體測試證據

在開發容器中使用系統 Jazzy Python 建置與測試：

```bash
colcon build --packages-select mobile_base_perception --symlink-install
colcon test --packages-select mobile_base_perception
colcon test-result --verbose
```

測試使用文件中的固定封包範例與 Linux pseudo-terminal，透過真實 ROS topics 與原生
Diagnostics 驗證無效樣本抑制、timeout 和資料流斷線。測試中的 115200、9.81、
pi/180、identity axes、0.25 秒都是受控範例，不是已接受的實機設定。
測試不存取實體 serial port。

仍須完成適用的硬體驗證：韌體／協定／baud、靜止重力、依安裝軸向受控旋轉、
發布頻率／延遲／時鐘行為，以及重連／錯誤情境。接受估測性能前，須標定 bias、
噪聲／covariance 與安裝姿態。實際韌體、尺度與獨立軸向證據仍未解決。
明確回報未知 covariance，不捏造數值；軟體測試不代表硬體驗收或 Feature Freeze。

### 連接裝置觀測（2026-10-02）

經授權，以指南中的 115200 對 `/dev/fihRobotBaseIMU` 進行有時間上限的唯讀擷取：
3.001 秒收到 539 個 XOR 正確的 59-byte AA55 封包，約 179.6 packets/s，
另有一個無效候選封包。第一組封包加速度約為 (-0.00823, 0.00457, 0.99653)。

這只確認觀測到的封包格式／布局相容，不確認韌體身分、單位、安裝軸向、時間戳精度、
bias 或標定。未發送 serial 命令或寫入韌體。此觀測與 adapter 軟體測試不同；
實際經標定的 ROS／估測運行仍待完成。

### 安裝確認與被動取樣（2026-10-07）

當時 Operator 確認 IMU 安裝座標符合權威 URDF；當時 `base_imu_link` 相對
`base_link` 的 joint rpy 為零，因此選用 adapter axes `[1,2,3]`。
此為歷史設定描述，目前模型已改為 yaw +90°；上述確認不構成對韌體封包軸向慣例
或旋轉時 gyro 正負號的獨立驗證。

115200 下的五秒被動擷取，在 5.008 秒內收到 869 個有限且 XOR 正確的封包，
約 173.5 packets/s，無無效候選封包。平均封包加速度約為
(-0.00822, 0.00231, 0.99595)，符合指南約 +1g Z 的讀值。
平均封包 gyro 約為 (0.03662, -0.00212, -0.04443)。

這些是觀測值，不是經標定的 bias、covariance、尺度、採樣頻率或時序精度。
受控方向旋轉與尺度驗證仍待完成；未發送馬達命令或 serial 資料命令。
擷取程式、原始 bytes 與附時間戳摘要保存在
`docs/validation/artifacts/imu-passive-20261007.tar.gz`。
程式使用獨占 serial 存取，未修改正式 adapter 或融合 runtime。

Diagnostics 區分角速度 covariance 已提供、未知或設定無效，同時保留尚未驗證標定的
限制。不提供部署 covariance 數值；標定與估測驗收仍是不同要求。

## LiDAR 預設原始設定檔

此開發 workspace 可直接修改主機上的：

`/home/zzz/mobile_base/src/mobile_base_perception/config/lidar.yaml`

或容器內同一份 bind-mounted 檔案：

`/workspace/src/mobile_base_perception/config/lidar.yaml`

以原生 symlink 安裝建置：

```bash
colcon build --packages-select mobile_base_perception --symlink-install
source install/setup.bash
ros2 launch mobile_base_perception dual_picoscan.launch.py
```

安裝的 config 是原始檔的 symlink，因此 YAML 修改於重新 launch 時生效，不必重新建置。
一般非 symlink 安裝則複製設定作為部署快照；直接修改原始檔的方式需要 symlink 建置。
Launch 沒有寫死主機路徑。無參數 launch 會設定、啟動已記錄的 .52／.53 感測器。
仍支援命令列覆寫。

完全由命令列提供設定時，可明確指定內容為 `{}` 的 YAML；ROS launch CLI 不接受
空的 `lidar_config` argument。指定檔案缺失仍會失敗，不會改用備用設定。
LiDAR driver 使用 Docker 內的修正版 `sick_scan_xd` overlay；詳見下段。

## 原生 LiDAR driver 的關閉修正

Docker 建置固定 SICK 3.9.0／commit `a562c5d098de21f6284359f4dfea97e93bd2b4d5`，
套用 `docker/patches/sick-scan-xd-shutdown.patch`，安裝至
`/opt/mobile_base/sick_scan_xd`。修正只在掃描執行緒結束後明確釋放全域診斷 updater，
避免 ROS node 留到 middleware 靜態解構階段才銷毀。同時保留 rclcpp 原生 deferred
SIGINT／SIGTERM handler，透過 Context pre-shutdown hook 在有效 context 中停止 scanner，
避免自訂 signal handler 中的 join／middleware mutex 死鎖。不改 scan、TF 或 QoS。
apt 版仍保留作為依賴／基線，但一般容器 Bash 會先載入修正版 overlay。

```bash
docker compose build mobile_base
docker compose up -d mobile_base
docker compose exec mobile_base bash
ros2 pkg prefix sick_scan_xd
cat /opt/mobile_base/sick_scan_xd/source-version.txt
```

prefix 應為 `/opt/mobile_base/sick_scan_xd/sick_scan_xd`。
版本紀錄包含上游 commit 與 patch SHA256。啟動指令仍是
`ros2 launch mobile_base_perception dual_picoscan.launch.py`。
裸用 `/opt/ros/jazzy/setup.bash` 並未選用這個 overlay；其他執行環境也必須明確載入
`/opt/mobile_base/sick_scan_xd/local_setup.bash`。

正式修正針對 Jazzy standalone caller 的 SIGINT／SIGTERM／scanner join 路徑；不宣稱解決所有上游異常路徑、
所有 middleware 版本或長期可靠性。更新上游版本時須重新核對 patch 並跑啟停回歸。

## LaserScan 距離範圍 metadata

兩台 LiDAR 的唯讀 OrdNum 均為 `1134608`，對應
[官方 Core-1 datasheet](https://www.sick.com/media/pdf/1/81/581/dataSheet_PICS150-01000-Core-1_1134608_en.pdf)
的有效工作範圍 0.05–25 m。`config/lidar.yaml` 因此明確設定
`laserscan_range_min: 0.05`、`laserscan_range_max: 25.0`。
這表示感測器有效量測上下限，不是每一幀最近／最遠的物體距離，
也不代表已驗證 25 m 實體量測精度。

SICK 3.9.0 原生 publisher 以當幀 extrema 填上下限；SLAM 快取首幀 bounds 後，
可能漏掉後续較遠或較近的有效點。Docker 既有 source overlay 另套用
`docker/patches/sick-scan-xd-range-bounds.patch`，讓 segment／fullframe 使用
明確配置的 bounds；原始 ranges、角度、frame、時間戳與點雲保持不變。
這兩個參數是本次 confirmed gap 的最小來源修正，apt 原生版本沒有這項能力。
0/0 保留原生行為，供未配置的 upstream 型號／軟體 fixture 使用；本平台正式設定
使用上述已確認的 Core-1 值。若換型號，需先確認其有效範圍再更改設定。
設定非法時啟動報錯；新增或移除這份來源修正須重建 image、重建 container，
並驗證原生輸出及 Mapping，而非只重建 workspace。

## 實機 IMU 容器存取

主機須存在 `/dev/fihRobotBaseIMU`。`compose.yaml` 映射該裝置，並授予 serial
群組權限；目前 Compose 也包含馬達裝置映射，但 IMU launch 不會啟動馬達。

```bash
export SERIAL_GID=$(stat -c '%g' /dev/fihRobotBaseIMU)
docker compose up -d mobile_base
docker compose exec mobile_base bash
ros2 launch mobile_base_perception imu.launch.py
```

裝置缺失會在 `/diagnostics` 回報通訊錯誤，不會發布虛構 IMU 資料。
新增映射需重建容器；USB 拔插後先確認主機裝置，再重建容器並重新啟動 driver。
同一裝置只啟動一個 driver。

### #38 IMU commissioning uncertainty

`config/imu.yaml` 的角速度 variance 起始值取自既有靜止實測 second moments
about zero，單位為 `(rad/s)^2`；Operator 已同意用於 commissioning 資料鏈驗證。
這些值包含當時 bias，並非已標定 variance、bias 補償或漂移上限；標定留後續。
模型負責安裝旋轉，driver 不重複套用 yaw +90°。本地 EKF 只選用 yaw rate，
不融合不可用 orientation 或 acceleration。
