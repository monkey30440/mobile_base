# Reference material

此目錄保存硬體權威資料與允許參考的既有實作，並非現行 V1 runtime。
V1 需求與決策入口見 [issue tracker](../docs/agents/issue-tracker.md)。

## Hardware sources

- `FIH_AMR_ROBOT_V2.0_0731/`：原始 URDF 與 meshes，作為底座幾何來源。
- M1 manuals：裝置操作與 Modbus 通訊規格。
- IIM-42652 datasheet 與 picoScan150 operating instructions：感測器規格。

原始硬體資料保留原貌；部署模型與配置依已確認 V1 決策另行適配。

## IMU reference

`tdk_ros2_imu/` 保存既有已驗證實作的協定、轉換、測試與操作經驗。
其中的 README／launch 命令用於理解或重現該 reference，不代表 V1 啟動方式。
`COLCON_IGNORE` 將它排除於一般 workspace 建置。

V1 USB IMU adapter 仍須獨立設計與驗證；此處的設計、診斷門檻、
covariance 與既有驗證結果不自動成為新 V1 contract 或驗證證據。

## Container reference

此處的 `Dockerfile` 與 `compose.yaml` 是舊容器配置參考，並非現行建置入口。
其中的相對 build context、volume 與 source 路徑不適用於目前目錄配置。

根目錄的 `Dockerfile` 與 `compose.yaml` 目前是空白占位檔，
尚未提供可建置或啟動的容器環境；其正式內容留後續已授權工作建立。
