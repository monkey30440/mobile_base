> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-010 Map Localization — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-010 地圖定位**：系統應根據已載入地圖與可用的感知及里程資料估測 AMR 位姿，並提供標準定位 pose 與 `map → odom` transform，供導航功能使用。當 AMR 開機位置無法可靠得知時，系統應接受使用者提供目前地圖中的 approximate initial pose，作為定位初始化輸入。

候選成熟方案固定為 ROS 2 Jazzy Navigation2 1.3.12-1 的 `nav2_amcl`與`nav2_bringup`，人工初始化採RViz Jazzy的 **2D Pose Estimate**。

SYS-010目前不要求project-defined localization-valid、convergence gate、navigation admission、定位失效分類、navigation termination或base stop。因此本研究不把這些行為加入coverage或custom gap，也不加入自動定位、固定開機點或保存上次pose。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | Navigation2 Jazzy `nav2_amcl`／`nav2_bringup` 1.3.12-1；RViz Jazzy 2D Pose Estimate |
| Coverage Status | **Fully Covered** |
| Mature Coverage | loaded Occupancy Grid + LaserScan + odometry／TF的AMCL定位；`amcl_pose`標準pose；`map → odom` TF；standard approximate-initial-pose topic／service；standard lifecycle localization composition |
| Custom Behavior Gap | **None** |
| Configuration / Composition Gap | frames、topics、QoS、AMCL motion／sensor model及threshold參數；唯一 `map → odom` owner；RViz人工操作流程；launch/lifecycle composition |
| Missing Evidence | target實際版本與configuration；map/scan/odom/TF連線；不同開機位置人工初始化；pose與TF frame/time/rate；實機定位品質與持續運作 |
| MVP Change Candidate | `None` |

AMCL本身已提供SYS-010要求的演算法、輸入介面、標準pose輸出、TF輸出與人工初始化介面。剩餘工作是configuration、composition及verification，不需要新增project-specific定位行為。

## 3. Mature Coverage

### 3.1 Loaded-map localization

`nav2_amcl`是ROS 2的2D probabilistic localization system。Navigation2 1.3.12 source顯示它：

- 接收`nav_msgs/msg/OccupancyGrid`地圖；
- 透過message-filtered `sensor_msgs/msg/LaserScan`取得感知資料；
- 由TF取得base與odometry frame之間的里程運動；
- 使用particle filter及設定的odometry／laser model更新pose estimate。

這直接覆蓋「根據已載入地圖與可用的感知及里程資料估測AMR位姿」。SYS-010中的「可用」表示AMCL只能用已到達且能依timestamp取得必要TF的資料；它沒有要求系統為缺少、過期或無法transform的每筆輸入建立額外failure policy。

### 3.2 Standard localization pose

AMCL的`amcl_pose` publisher型別為`geometry_msgs/msg/PoseWithCovarianceStamped`。發布內容包含：

- `header.stamp`及global frame；
- position與orientation pose；
- 6×6 covariance。

因此`amcl_pose`就是SYS-010要求供navigation使用的standard localization pose，不需要另定project message或轉接格式。Particle cloud是AMCL額外的觀測輸出，不是SYS-010必要contract。

### 3.3 `map → odom` transform

AMCL根據估測pose與當時的odom-to-base transform計算global-to-odom transform；`tf_broadcast=true`時透過TF發布。典型配置為：

```text
global_frame_id: map
odom_frame_id: odom
base_frame_id: <robot base frame>
tf_broadcast: true
```

Localization mode必須維持單一authority：AMCL啟用`tf_broadcast`時，由AMCL唯一擁有`map → odom`。SLAM或其他node不得同時發布相同transform。這是composition constraint，不是custom behavior。

### 3.4 Approximate initial pose

AMCL 1.3.12提供兩個標準runtime入口：

- `initialpose` subscription：`geometry_msgs/msg/PoseWithCovarianceStamped`；
- `set_initial_pose` service：`nav2_msgs/srv/SetInitialPose`。

RViz Jazzy的2D Pose Estimate工具發布`PoseWithCovarianceStamped`至`initialpose`。因此AMR開機位置不可靠時，v0.1可由使用者在目前地圖上指出大約x、y、yaw，直接完成SYS-010的初始化輸入，不需custom adapter。

人工操作的最低順序為：

```text
載入目前地圖
  → 啟動 localization lifecycle
  → 使用 RViz 2D Pose Estimate 提供 approximate initial pose
  → AMCL 依後續可用 scan／odom／TF 更新並發布 pose 與 map → odom
```

本項只要求接受approximate initial pose，不把「收到initial pose」擴張成額外的convergence或admission contract。

### 3.5 Lifecycle composition

`nav2_bringup/launch/localization_launch.py`以標準方式啟動：

- `map_server`；
- `amcl`；
- `lifecycle_manager_localization`。

Lifecycle Manager依序configure／activate `map_server`與`amcl`。AMCL只在ACTIVE時處理其runtime callbacks及啟用lifecycle publishers。因此可直接重用標準launch結構；ACTIVE是AMCL可工作的process state，不是SYS-010額外要求的定位品質判定。

## 4. Native Runtime Constraints Are Not Custom Gaps

AMCL正常運作受輸入與TF條件限制：

- 尚未取得map、scan或必要TF時，無法進行相應filter update；
- LaserScan timestamp無法轉換至必要frame時，tf2 message filter可drop該筆資料並產生warning／diagnostic；
- 尚未初始化時，AMCL不應發布無依據的pose／`map → odom`；
- lifecycle未ACTIVE時，不進行正常runtime processing／publication；
- movement未達`update_min_d`／`update_min_a`等條件時，不一定為每筆scan更新filter；`save_pose_rate`、`transform_tolerance`及publish behavior也受參數控制。

這些是成熟套件的input、TF、lifecycle及parameter semantics。它們應被配置與驗證，但最新SYS-010未要求另做input watchdog、failure classifier、localization-valid boolean或導航失效處置，所以不構成custom behavior gap。下游Nav2如何因robot pose／TF不可用而拒絕或中止某次navigation，也屬下游runtime behavior，不應偷渡回SYS-010。

## 5. Configuration and Composition Gaps

- 固定`global_frame_id=map`、`odom_frame_id=odom`及實際robot base frame；
- 固定map與scan topics、remapping及namespace；
- 確認map subscription與LaserScan subscription的QoS和publisher相容；
- 確認odom-to-base TF可依scan timestamp取得，且整棵TF tree無多重publisher；
- 固定AMCL differential-drive odometry model與實車相符的noise參數；
- 固定laser model、beam／likelihood參數、update thresholds、resampling與transform tolerance；
- 確認`tf_broadcast=true`，並保證只有AMCL發布`map → odom`；
- 固定initial pose使用目前map frame、合理covariance與RViz人工操作說明；
- 以`nav2_bringup` localization launch或等價composition管理map server與AMCL lifecycle。

上述皆屬使用成熟套件所需的configuration／composition，不需新增定位演算法、message type或project adapter。

## 6. Evidence Required Before Acceptance

- 記錄target image實際安裝的`nav2_amcl`、`nav2_bringup`、`nav2_msgs`、RViz與`geometry_msgs`版本；
- 證明目前Map Package的Occupancy Grid可由map server提供並被AMCL接收；
- 證明兩個LiDAR的實際selected localization scan及其QoS／frame／timestamp符合AMCL輸入；若上游選用merged scan，只驗證AMCL收到的單一selected scan，不在SYS-010重做merge選型；
- 證明wheel／fused odometry所形成的`odom → base` TF可在scan timestamp取得；
- 用`ros2 topic info -v`、sample message及frequency evidence確認`amcl_pose`型別、publisher、frame、stamp與更新行為；
- 用TF工具確認AMCL是唯一`map → odom` publisher，並量測transform rate、age及連續性；
- 在多個不固定開機位置，以RViz 2D Pose Estimate提供不同approximate x、y、yaw，確認AMCL開始更新pose與TF；
- 在無initial pose、missing scan、missing odometry TF及timestamp／QoS不相容情境，記錄AMCL原生no-output、drop及log behavior，作為operational troubleshooting evidence；
- 在實體場域比較定位pose與可觀察ground truth／landmarks，驗證靜止、直行、旋轉及路線行駛時的品質；threshold與acceptance criteria留待verification設計定案。

## 7. Primary-source Evidence

### 7.1 AMCL algorithm inputs, outputs and lifecycle

- **Evidence Type:** upstream exact-tag source and official Nav2 configuration documentation
- **Sources:** [`amcl_node.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_amcl/src/amcl_node.cpp)；[`amcl_node.hpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_amcl/include/nav2_amcl/amcl_node.hpp)；[AMCL configuration guide](https://docs.nav2.org/configuration/packages/configuring-amcl.html)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** source定義Occupancy Grid、LaserScan、odometry／TF integration、particle-filter updates、`amcl_pose`／particle publication、initial-pose inputs、lifecycle callbacks及global-to-odom calculation/publication；official guide記錄frames、topics、models、QoS-related options及`tf_broadcast`。
- **Limitations:** successful target-hardware configuration and localization quality require project evidence。
- **Access Date:** 2026-08-14

### 7.2 Standard localization pose and initial-pose interfaces

- **Evidence Type:** upstream exact-version ROS interface sources
- **Sources:** [`PoseWithCovarianceStamped.msg` at common_interfaces 5.3.8](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/PoseWithCovarianceStamped.msg)；[`SetInitialPose.srv` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/srv/SetInitialPose.srv)
- **Exact Version / Revision:** `geometry_msgs` 5.3.8-1；Navigation2／`nav2_msgs` 1.3.12-1
- **Observed Scope:** standard message包含header、pose及covariance；standard service包含initial `PoseWithCovarianceStamped`及result。
- **Limitations:** interface definition alone does not prove project frames、QoS or real-hardware localization quality。
- **Access Date:** 2026-08-14

### 7.3 RViz manual initial pose

- **Evidence Type:** upstream ROS 2 Jazzy RViz source
- **Source:** [`initial_pose_tool.cpp` on RViz Jazzy branch](https://github.com/ros2/rviz/blob/jazzy/rviz_default_plugins/src/rviz_default_plugins/tools/pose/initial_pose_tool.cpp)
- **Exact Version / Revision:** RViz Jazzy branch as accessed 2026-08-14; target binary version remains evidence
- **Observed Scope:** 2D Pose Estimate publishes a `PoseWithCovarianceStamped` initial estimate on the configured initial-pose topic。
- **Limitations:** operator accuracy、selected fixed frame and covariance configuration require operational evidence。
- **Access Date:** 2026-08-14

### 7.4 Standard localization launch

- **Evidence Type:** upstream exact-tag launch source and official lifecycle documentation
- **Sources:** [`localization_launch.py` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bringup/launch/localization_launch.py)；[Lifecycle Manager configuration](https://docs.nav2.org/configuration/packages/configuring-lifecycle.html)；[`lifecycle_manager.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_lifecycle_manager/src/lifecycle_manager.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** standard bringup組合map server、AMCL及localization lifecycle manager，並管理lifecycle activation。
- **Limitations:** launch composition does not prove project topic／TF wiring or localization quality。
- **Access Date:** 2026-08-14

### 7.5 Jazzy release metadata

- **Evidence Type:** ROS build-farm status and upstream release metadata
- **Sources:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)；[Navigation2 release 1.3.12](https://github.com/ros-navigation/navigation2/releases/tag/1.3.12)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12-1；`geometry_msgs` 5.3.8-1
- **Observed Scope:** confirms assessed package versions in the Jazzy release line。
- **Limitations:** repository metadata does not prove the target image has those exact binaries installed。
- **Access Date:** 2026-08-14

## 8. Recommended 04 Record

```text
SYS-010 Map Localization
Candidate Mature Solution: nav2_amcl and nav2_bringup 1.3.12-1; RViz Jazzy 2D Pose Estimate
Coverage Status: Fully Covered
Covered Scope: loaded-map + LaserScan + odometry/TF pose estimation; standard amcl_pose; map->odom TF; manual approximate-initial-pose topic/service; lifecycle localization composition
Custom Behavior Gap: None
Configuration / Composition Gap: frames, topics, QoS, AMCL model/threshold parameters, unique map->odom ownership, RViz manual operation, launch/lifecycle composition
Evidence Gap: target versions and configuration; map/scan/odom/TF wiring; arbitrary-start manual initialization; pose/TF frame/time/rate; real-hardware localization quality and continuity
MVP Change Candidate: None
```

SYS-010應直接採用成熟AMCL能力。後續若新增project localization-valid、navigation admission或定位失效處置，必須先回到03形成新的normative requirement，再進行reuse assessment；不得在本項以custom gap預先加入。
