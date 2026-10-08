# mobile_base_description

提供移動底座的模型與座標關係。套件內包含完整所需的 URDF 與 STL；建置及執行均不依賴 repository 的 `reference/` 或任何 `/home/zzz/...` 絕對路徑。

## 目錄與來源

```text
mobile_base_description/
├── urdf/mobile_base.urdf
├── meshes/                 # 模型實際引用的 24 個底座 STL
├── launch/description.launch.py
└── test/test_model_tf.py
```

模型源自已確認的 `RWF_V2.0_QA_release.urdf` 底座子樹，並保留既有 V1 調整。上半身不在本套件範圍內。`reference/` 僅保留原始平台資料與來源追溯，不作為建置輸入；更新模型時，應明確更新套件資源並重新驗證。

STL 使用 `package://mobile_base_description/meshes/...` 引用。安裝後，模型與 meshes 位於 `share/mobile_base_description/`。檔案內容與來源 hash 見 [本輪驗證紀錄](../../docs/validation/description-self-contained-20261007.md)。

## 模型術語

- **名義輪座姿態**：使用 V1 輪座的設計位置作為模型幾何參考，不是懸吊即時量測。
- **量測輪角**：由馬達位置回授換算的驅動輪轉角；角度參考與位移標定是不同概念。

## 模型責任

- `base_footprint` 是統一的 footprint 名稱，連接 `base_link` 與底座模型。
- 原生 `robot_state_publisher` 是唯一模型 TF 發布者。
- 左前 LiDAR：roll 180°、pitch 0°、yaw +45°。
- 右後 LiDAR：roll 180°、pitch 0°、yaw −135°。
- IMU：roll／pitch 0°、yaw +90°。
- 原生 scan frames `base_lidar_link_FL_1`／`base_lidar_link_BR_1` 與安裝 links 的變換為 identity，安裝旋轉只套用一次。
- 安裝平移沿用已確認模型；精確外參標定仍是獨立驗收項目。

兩個驅動輪座 `driving_slide_joint_L/R` 使用原設計位置的名義固定姿態，不代表懸吊即時量測。輪子仍是 continuous joints，轉角由真實輪端回授提供。其他被動輪／懸吊 joints 不會因本次整理自動固定。

本套件不啟動 `joint_state_publisher`，不補零或虛構輪角，也不發布 `odom → base_footprint`；該變換由後續原生 `robot_localization` 負責。未取得活動 joint state 的分支，不保證有完整動態 TF。

## 第一階段：只驗證模型

在 repository 的 container workflow 中建置套件，載入新 overlay：

```bash
colcon build --packages-select mobile_base_description
source install/setup.bash
ros2 launch mobile_base_description description.launch.py
```

這個入口只啟動模型發布者，不啟動馬達、IMU、LiDAR、EKF 或 Navigation。模型與固定 sensor TF 可以在不操作馬達的情況下驗證。

要從 Foxglove 觀察，在另一個已載入相同 overlay 的 terminal 啟動原生 bridge：

```bash
ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
```

連線至 AMR 主機的 `ws://<主機IP>:8765`；若 Foxglove 位於同一主機，可以使用 `ws://localhost:8765`。

Foxglove 3D 設定：

1. Fixed frame 與 Display frame 選 `base_footprint`。
2. 啟用 `/robot_description` 與需要觀察的 TF。
3. Scene 的 Mesh up-axis 選 **Z-up**。Y-up 會造成純顯示上的模型旋轉，不應透過修改底座 TF 補償。
4. 確认底座外觀、IMU 與雙 LiDAR 座標方向符合已確認安裝。

此階段沒有 sensor 資料；點雲需在後續另外啟動 Perception LiDAR 才會出現。活動輪子若尚無回授，可能不顯示；這不代表固定 sensor TF 建立失敗。只運行一個模型發布者，不要重複啟動 Description。

## 後續：獨立啟動 Control

兩個入口預設讀取已安裝的 mobile_base_control/config/m1.yaml。
Description 需要已安裝的 Control 套件以取得設定，但不啟動 Control。

Terminal 1：

```bash
ros2 launch mobile_base_description description.launch.py
```

Terminal 2：

```bash
ros2 launch mobile_base_control m1.launch.py
```

Description 只讀設定，將既有 M1 `ros2_control` 宣告加入發布的 URDF；不開裝置、不啟動控制器、不執行 Servo ON。Control 透過原生 `robot_description` topic 取得模型，啟動硬體／控制器，可能執行 Servo ON；實機操作條件仍須另外確認。

兩個入口必須選同一份 profile；需要其他設定時，兩邊都以 hardware_config:=/absolute/hardware.yaml 覆寫。幾何-only 的 Description 無法供 M1 初始化使用。沒有自動比對兩份設定或 hot reload；變更模型／設定時，結束該情境再重新啟動。

`model_file` 可明確指定另一份幾何 URDF／xacro，預設是套件內模型。相對路徑由呼叫者工作目錄解析，支援 `~` 展開。提供硬體設定時，模型必須有 `left_wheel_joint`／`right_wheel_joint`，且不能已有 `ros2_control` 宣告。

模型檔缺失、XML／xacro／YAML 錯誤，以及缺失、空白、非 mapping 或含 null 值的 hardware mapping 會使模型啟動失敗。必要硬體參數是否完整、實際數值是否有效，由 Control／plugin 驗證；模型啟動成功不等於硬體就緒。

## 軟體驗證與驗收界線

```bash
colcon test --packages-select mobile_base_description
colcon test-result --verbose
```

測試使用原生 RSP、公開 `/robot_description` 與 TF，驗證模型、已安裝 mesh 資源及固定座標關係，不操作實體裝置，也不合成活動 joint state。

模型／固定 TF 的軟體驗證與先前 Operator 靜止確認可以作為各自範圍的 evidence；新的啟動情境仍需手動確認。動態輪角、估測資料鏈、實際安裝精度及 calibration 不由這些測試代替。
