> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-001 Map Creation — Reuse Research

## 1. Research Scope

本筆記只評估目前定案的 SYS-001：

> 系統應建立可供定位與導航使用之二維 Occupancy Grid 地圖；建圖功能無法完成初始化並進入可處理建圖資料之狀態時，系統應回報失敗及原因。

評估候選為 ROS 2 Jazzy `slam_toolbox` 2.8.5-1 online asynchronous mapping。

本 requirement 中「進入可處理建圖資料之狀態」明確定義為：`slam_toolbox` 已完成 lifecycle configure 與 activate，且 mapping 所需的 subscriptions、publishers、TF helper、solver 與 services 已建立／啟用。它不表示已收到第一筆 LaserScan，也不表示第一筆 runtime input 已通過 TF／odometry 檢查。

下列事項不在 SYS-001 重複判定：

- SYS-002：Map Package 儲存；
- SYS-006：進入可處理狀態後，依有效感知與里程資料持續更新地圖；
- SYS-024：建立、儲存與重新載入結果的聚合；
- Route Graph、Station mapping 與 Navigation strategy resources。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `slam_toolbox` 2.8.5-1 online asynchronous mapping |
| Coverage Status | **Fully Covered** |
| Covered Scope | 原生完成 2D pose-graph SLAM 與 `nav_msgs/msg/OccupancyGrid` publication；managed lifecycle 提供 configure／activate 初始化邊界、transition result 與失敗 diagnostics，使 composition 可判斷是否進入 ACTIVE |
| Custom Behavior Gap | `None` |
| Configuration / Composition Gap | 選定一個有效 scan source；設定 frames／mapping parameters；提供 sensor TF 與 `odom -> base`；執行並觀察 configure／activate transition；Mapping Mode 中維持 `map -> odom` 單一 ownership |
| Missing Evidence | target image 實際安裝版本；正常 configure／activate；無效 solver/plugin/parameter 或 initialization error 的 failure injection；實際 scan/TF/odometry integration；真機地圖品質與後續 localization/navigation fitness |
| MVP Change Candidate | `None` |

`Fully Covered` 的理由是成熟套件與 ROS 2 managed lifecycle 已提供 SYS-001 所要求的 mapping capability、初始化狀態邊界及 failure diagnostics，不需要補寫 custom mapping behavior。

## 3. Mature Mapping Capability

### 3.1 Inputs and transforms

`slam_toolbox` 官方介面以 `scan_topic` 選定一個 `sensor_msgs/msg/LaserScan` input，並使用：

- scan frame 到 configured base frame 的 transform；
- configured `odom_frame` 到 `base_frame` 的 transform；
- scan timestamp 對應的 TF history。

套件以 odometry 為 LaserScan 建立 pose，再以 scan matching 與 pose-graph optimization 修正 pose。SYS-001 不需要自製 odometry ingestion API；專案只需把既有 system planar odometry 與 sensor transforms 正確組合給套件。

### 3.2 Outputs

`slam_toolbox` 原生發布：

- `map`：`nav_msgs/msg/OccupancyGrid`；
- `map -> odom`：SLAM 修正後的 global-to-local transform。

這完整提供「建立二維 Occupancy Grid」的成熟能力。地圖是否在本 AMR 與目標場域足以支援定位和導航，仍需真機 acceptance evidence；不構成 custom mapping behavior gap。

## 4. Initialization and Ready-to-process Boundary

官方 `online_async_launch.py` 啟動 lifecycle `async_slam_toolbox_node`，並提供 configure／activate 流程。2.8.5 source 中：

- configure 建立 solver、mapper、TF buffer/listener、scan subscription/filter、map publisher 與 services 等 runtime interfaces；
- activate 啟用 lifecycle publishers 與可接受資料處理的 active state；
- lifecycle callback／transition result 表示初始化是否完成；
- configuration、plugin loading 或 initialization 過程若失敗，lifecycle transition 不會成功進入預期 ACTIVE state，並由 lifecycle／exception logging 提供原因線索。

因此 SYS-001 的初始化判定為：

```text
configure succeeds
  -> activate succeeds
  -> lifecycle state ACTIVE
  -> mapping function is ready to process incoming mapping data
```

若 configure 或 activate 未成功，System Operation Coordination 可直接依 transition result 回報 Mapping initialization Failure，並保留套件／lifecycle diagnostics 作為原因。這只是 composition 使用既有 lifecycle contract，不是 custom behavior。

## 5. What ACTIVE Does and Does Not Prove

ACTIVE 證明建圖元件已完成初始化並進入可處理狀態。它不證明：

- scan publisher 已存在；
- 已收到第一筆 LaserScan；
- scan timestamp 可取得完整 TF／odometry；
- 第一筆 scan 已加入 pose graph；
- Occupancy Grid 已開始或持續更新；
- 地圖品質已適合定位與導航。

這些不是 SYS-001 本句「無法完成初始化並進入可處理狀態」的失敗條件。尤其是 node ACTIVE 後沒有 scan、或 scan 因 runtime TF／odometry 不可用而無法處理，不得倒推為 SYS-001 initialization failure；開始後的有效 input 與持續更新責任應在 SYS-006 評估。

## 6. Failure Reporting Boundary

最低符合方式是：

- composition 取得 configure／activate transition success or failure；
- failure 時不得宣告 Mapping Mode initialization success；
- 對操作員回報 initialization failed；
- 保留 lifecycle callback、plugin、parameter 或 exception log 所提供的原因。

原生 terminal logs 在此可作為 initialization failure 的原因 diagnostics，因為 normative boundary 已限定在 configure／activate。ACTIVE 後的 runtime input 狀況則由其他 requirement 與 integration evidence 處理。

## 7. Online Asynchronous Selection

Jazzy 套件提供官方 `online_async_launch.py`，使用 lifecycle `async_slam_toolbox_node` 與 `mapper_params_online_async.yaml`。對操作員以 `teleop_twist_keyboard` 巡覽場域的 live Mapping Mode，online asynchronous 是合理成熟候選。

這只確認 reuse candidate，不把官方範例參數值升格為 requirement。resolution、range、travel threshold、map update interval、queue 與 solver tuning 必須依實際 LiDAR、odometry、車速、CPU 與場域證據選定。

同步模式仍是套件提供的替代方式，但目前沒有 SYS-001 evidence 要求逐筆保存和處理所有 scan，因此不需要增加 synchronous-mode 義務。

## 8. Teleoperation and LiDAR Boundaries

### 8.1 Teleoperation

```text
teleop_twist_keyboard -> manual velocity command -> Motion Control -> AMR motion

LaserScan + TF/odometry -> slam_toolbox -> OccupancyGrid + map -> odom
```

`teleop_twist_keyboard` 只是 Mapping Mode 的 external command source，不是 mapping algorithm，也不構成 custom mapping gap。

### 8.2 Independent scan source first

`slam_toolbox` 以單一 `scan_topic` 選定 input。SYS-001 只要求 composition 選定一個對建圖有效且足夠的 scan source，不因 AMR 有兩個 LiDAR 就要求融合：

- 不在 SYS-001 指定 merged scan；
- 不把 RF2O 對 merged scan 的需求推廣到 Mapping；
- 只有真機地圖品質證據顯示選定的單一來源不足時，才重新評估 Mapping 的 scan composition。

## 9. Mapping Mode and TF Ownership

Mapping Mode 中由 `slam_toolbox` 擁有 `map -> odom`；Navigation Mode 中由 localization owner 擁有。兩者不得同時發布：

```text
Mapping Mode:    slam_toolbox owns map -> odom
Navigation Mode: localization owner owns map -> odom
```

只有 configure／activate 成功後，System Operation Coordination 才能把 Mapping function 視為已完成初始化。具體 operating-mode prerequisites 與 cleanup ordering 屬後續 architecture/subsystem design。

## 10. Evidence Required Before Acceptance

### Initialization evidence

- 記錄 target image 實際安裝的 Jazzy `slam_toolbox` version；
- 證明正常 configure／activate 後 lifecycle state 為 ACTIVE；
- 注入無效 solver/plugin、錯誤必要參數或可重現的 initialization failure，證明 transition 不會被誤報為成功；
- 證明 operation layer 在 transition failure 時回報 initialization Failure，且 terminal/lifecycle diagnostics 可指出原因；
- 證明 configure／activate failure 時不宣告 Mapping function ready。

### Integration and map-fitness evidence

- 驗證 selected scan topic、scan frame、`odom -> base` 與 sensor static TF；
- 使用實體 AMR 與目標場域完成人工巡覽；
- 檢查必要場域覆蓋，以及牆面／固定障礙物重影、破碎與扭曲；
- 檢查 free／occupied／unknown 表達合理；
- 後續 requirements 再證明 continuous update、Map Package storage/reload 與 localization/navigation fitness。

沒有 scan 或 runtime TF／odometry 不可用，不列入 SYS-001 initialization failure injection；這些條件屬 SYS-006 與 integration evidence。

目前 `maps/template/map.pgm` 為空檔，`maps/template/map.yaml` 也沒有內容，只是目錄 placeholder；`docs/m1_bringup_validation` 聚焦 M1 motor/drive bringup。兩者都不是 SYS-001 PASS evidence。

## 11. Primary-source Evidence

### 11.1 Mapping interfaces and products

- **Evidence Type:** Exact-tagged upstream package README/API
- **Source:** [`slam_toolbox` 2.8.5](https://github.com/SteveMacenski/slam_toolbox/tree/2.8.5)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** one `sensor_msgs/LaserScan` input、configured odom-to-base TF、scan matching／pose-graph mapping、`nav_msgs/OccupancyGrid` and `map -> odom` outputs.
- **Limitations:** capability documentation does not prove this AMR's deployment configuration or map quality.
- **Access Date:** 2026-08-14

### 11.2 Lifecycle implementation

- **Evidence Type:** Exact-tagged upstream source
- **Sources:** [`slam_toolbox_common.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)；[`online_async_launch.py`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/launch/online_async_launch.py)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** official launch creates lifecycle `async_slam_toolbox_node` and drives configure／activate；common callbacks establish mapping interfaces and activate lifecycle publishers.
- **Limitations:** lifecycle ACTIVE represents initialized/ready-to-process, not receipt or successful processing of runtime sensor data.
- **Access Date:** 2026-08-14

### 11.3 Asynchronous runtime processing

- **Evidence Type:** Exact-tagged upstream source
- **Sources:** [`slam_toolbox_async.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_async.cpp)；[`get_pose_helper.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/get_pose_helper.cpp)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** after activation, incoming scans are evaluated against odometry pose and laser metadata before processing.
- **Limitations:** rejected or absent runtime inputs do not retroactively mean lifecycle initialization failed; their continuing-update effect belongs to SYS-006.
- **Access Date:** 2026-08-14

### 11.4 Managed lifecycle semantics

- **Evidence Type:** Official ROS 2 design specification
- **Source:** [Managed nodes lifecycle design](https://design.ros2.org/articles/node_lifecycle.html)
- **Observed Scope:** configure／activate callbacks control transitions into Inactive／Active and return transition outcomes; callback failure/error prevents the requested successful state progression and supports supervision.
- **Limitations:** generic lifecycle states do not validate application-specific runtime sensor availability or map quality.
- **Access Date:** 2026-08-14

### 11.5 Jazzy package and release evidence

- **Evidence Type:** Official ROS 2 package documentation and bloom metadata
- **Sources:** [`slam_toolbox` Jazzy documentation](https://docs.ros.org/en/jazzy/p/slam_toolbox/)；[`slam_toolbox-release`](https://github.com/SteveMacenski/slam_toolbox-release)
- **Exact Version / Revision:** Jazzy 2.8.5-1 released 2026-04-29
- **Observed Scope:** confirms the assessed package/API and its Jazzy release line.
- **Limitations:** does not prove which version is installed in the target image.
- **Access Date:** 2026-08-14

## 12. Recommended 04 Record

```text
SYS-001 Map Creation
Candidate Mature Solution: ROS 2 Jazzy slam_toolbox 2.8.5-1 online asynchronous mapping
Coverage Status: Fully Covered
Covered Scope: lifecycle initialization to ACTIVE/ready-to-process plus LaserScan and TF/odometry to 2D OccupancyGrid and map -> odom
Custom Behavior Gap: None
Configuration / Composition Gap: selected scan source, frame/TF and mapping parameters, configure/activate supervision, exclusive map -> odom ownership
Evidence Gap: target version, lifecycle initialization success/failure injection, scan/TF integration, and real-hardware map fitness
MVP Change Candidate: None
```

完成 SYS-001 coverage record 後才進入 SYS-002；不得在此加入持續更新失敗、storage、reload validation 或完整 Mapping Result。
> Historical research note: any RF2O references describe the superseded pre-2026-08-26 baseline. Current production odometry is Kinematic-ICP.
