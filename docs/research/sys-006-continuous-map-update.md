> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-006 Continuous Map Update — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-006 持續更新地圖**：建圖進行期間，系統應於取得新的有效感知與里程資料後更新目前二維 Occupancy Grid；資料暫時不可用時，系統應保留目前地圖並等待後續有效資料，直到使用者完成或終止建圖。

本 requirement 要求三件事：

1. 新的有效感知與里程資料能持續加入建圖狀態；
2. 資料暫時不可用時，不破壞既有地圖，並等待後續有效資料；
3. 使用者完成或終止建圖時，停止繼續接受與更新。

SYS-001 initialization、SYS-002 save 與 SYS-024 read-back validation 不在本項重複判定。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `slam_toolbox` 2.8.5-1 online asynchronous mapping |
| Exact Released Version | ROS 2 Jazzy `slam_toolbox` 2.8.5-1；target image 實際安裝版本仍待確認與固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 以 TF MessageFilter接收scan，取得scan timestamp的odometry pose，將通過acceptance rules的新measurement加入pose graph；依`map_update_interval`以current graph產生／發布Occupancy Grid；暫時無效measurement被等待或丟棄而不清除graph；外部使用者可透過lifecycle deactivate結束或終止更新 |
| Custom Behavior Gap | `None`；不需要自製 continuous-map updater或額外的input-duration monitor |
| Configuration / Composition Gap | authoritative scan source與QoS；scan/base/odom TF；`scan_queue_size`、transform timeout、throttle/time/travel/heading/range/resolution/update parameters；active map consumer；使用者完成／終止命令到lifecycle deactivate的composition與順序 |
| Missing Evidence | target version；accepted scan-to-graph-to-map progression；TF/message-filter/odom drop observability；暫時input loss時graph/current map保留；input恢復後可繼續；publication conditions；deactivate後不再接受measurement或更新 |
| MVP Change Candidate | `None` |

`Fully Covered` 表示套件原生語意與目前 normative 一致：有效資料就繼續處理，暫時無效資料就保留既有狀態並等待，直到外部使用者要求完成或終止。這不表示每筆收到的 scan 都必須加入 graph，也不表示 `/map` 必須在沒有 subscriber 時持續發布。

## 3. Native Continuous-update Path

Jazzy 2.8.5 online async 的資料路徑為：

```text
selected LaserScan
  -> TF MessageFilter
  -> odom pose lookup at scan timestamp
  -> laser-frame metadata validation
  -> shouldProcessScan acceptance rules
  -> addScan / pose-graph update
  -> periodic OccupancyGrid rasterization and publication
```

scan subscription 使用 sensor-data QoS。`tf2_ros::MessageFilter` 以 configured `odom_frame`、`scan_queue_size` 與 `transform_timeout` 做 admission；進入 asynchronous callback 後，套件再查詢同一 scan timestamp 的 odometry pose，驗證 laser metadata，最後套用 `shouldProcessScan()`。

原生 acceptance rules 包含：

- pause state；
- `throttle_scans`；
- `minimum_time_interval`；
- `minimum_travel_distance`；
- `minimum_travel_heading`。

因此「新的有效資料」是通過 topic、TF、odometry、laser metadata 與 configured mapping policy 的 measurement，不是每一筆到達 subscription 的 scan。通過後，online async 直接處理 measurement並更新 pose graph；不需要自製 queue或map-update loop。

## 4. Internal State Versus OccupancyGrid Publication

`slam_toolbox` 的 authoritative mapping state 是 pose graph與dataset。Occupancy Grid是依 `map_update_interval` 從current pose graph重新rasterize的輸出表示：

```text
accepted measurement
        -> pose graph updated
        -> next eligible map refresh reflects current graph
```

`publishVisualizations()` 依設定週期呼叫 `updateMap()`；但 publication有明確條件：

- lifecycle map publisher必須存在且active；
- `/map` 必須至少有一個subscriber；
- mapper必須能從current graph產生Occupancy Grid。

publisher未active或沒有subscriber時，`updateMap()`直接回傳true，不重新rasterize／publish。這不代表內部pose graph消失，也不代表continuous mapping停止；只代表當下沒有需要發布的consumer。故驗收必須分開觀察：

- 新有效measurement是否加入內部mapping state；
- 在publication條件成立時，current Occupancy Grid是否反映該state。

單看 `/map` timestamp 也不足以證明新measurement已成功加入graph，因async callback在odometry lookup之前就保存scan header。應以`new_node_event`、graph state或map內容進展搭配驗證。

## 5. Temporary Data Unavailability

套件對暫時不可用資料採「等待／丟棄該筆，保留既有graph，等下一筆」：

| Condition | Native behavior | Observable evidence |
|---|---|---|
| scan暫時沒有到`odom_frame`的TF | MessageFilter等待；超出queue／transform條件的scan不進callback | MessageFilter drop／failure diagnostics需在target composition實測 |
| scan timestamp查不到odometry pose | callback直接return；不呼叫`addScan()` | warning：`Failed to compute odom pose` |
| laser frame無法轉換／metadata無法建立 | 丟棄該scan；不呼叫`addScan()` | failed laser pose/device error或warning |
| pause、throttle、time或motion門檻不符 | 該scan不處理 | 正常acceptance behavior，不是failure |
| mapper未接受measurement | 不以該筆改變graph | 沒有清除既有graph的行為 |

這些 early return／drop 路徑沒有呼叫 reset、cleanup，也沒有替換既有 dataset。換句話說，無效measurement不會用錯誤資料覆蓋目前地圖；node保持active並等待下一筆。後續資料恢復且重新通過admission後，callback會再次走`addScan()`，繼續在原pose graph上建圖。

「保留目前地圖」在此應精確理解為：

- 內部current pose graph／dataset保持；
- 已存在的last Occupancy Grid內容不因無效input被清空；
- 若publication條件成立，timer可能再次從相同graph產生／發布相同內容；
- 不要求在沒有subscriber時仍持續重新發布相同map。

## 6. User Completion and Termination

online async node是managed lifecycle node。使用者完成或終止建圖時，外部operating flow可要求lifecycle deactivate。`on_deactivate()`會：

- interrupt並join transform與visualization threads；
- deactivate map、metadata與pose publishers；
- reset scan filter與scan subscription；
- reset mapping runtime services；
- return lifecycle success。

這提供了「直到使用者完成或終止」的標準停止機制。把terminal／operator命令接到lifecycle transition屬composition，不是custom mapping behavior。完成與終止在SYS-006都只要求停止持續更新；save與read-back分別由其他requirements處理。

`pause_new_measurements`只能暫停接受新measurement，不等同session完成或終止。正式結束應使用lifecycle deactivate，使subscription與publication threads都撤除。

## 7. No Additional Input-duration Policy Required

目前 normative明確採用wait-for-valid-input語意，沒有要求：

- 依input freshness timeout將短暫等待重新分類；
- 自動進入lifecycle error；
- 在沒有使用者命令時結束整場mapping；
- 產生額外的session result。

因此 `slam_toolbox` 沒有這些介面不構成缺口，也不應增加額外monitor。持續缺少資料時，node保持既有graph並等待，直到使用者決定完成或終止，正是目前requirement要求的行為。

## 8. LiDAR Boundary

本項沿用單一authoritative `scan_topic` composition。SYS-006只要求該source後續有效measurement能持續處理，不因AMR有兩個LiDAR就要求雙scan merge，也不指定merge algorithm／topic。其他consumer使用merged scan的決定不能推導成mapping也必須融合。

## 9. Evidence Required Before Acceptance

- 固定並記錄target image實際安裝的Jazzy `slam_toolbox` version；
- 證明selected scan frame在scan timestamp可取得scan-to-base與`odom -> base` TF；
- 量測scan input rate、accepted processing rate、MessageFilter drops、odom／laser TF failures、CPU load與map publication cadence；
- 固定並說明queue、transform timeout、throttle、minimum time/travel/heading、range、resolution與map update parameters；
- 在AMR移動且取得新有效資料後，證明pose graph與Occupancy Grid內容持續進展；
- 注入短暫scan loss、odom lookup failure與required TF unavailable，證明既有graph／map未被清空或污染；
- 恢復有效input，證明mapping可在同一session及原graph上繼續；
- 分別測試publisher inactive、沒有`/map` subscriber與正常subscriber，確認publication conditions符合source semantics；
- 驗證使用者完成／終止後lifecycle inactive，scan subscription已移除且不再產生新的mapping update。

## 10. Primary-source Evidence

### 10.1 Exact Jazzy release

- **Evidence Type:** ROS bloom release metadata
- **Source:** [`slam_toolbox-release`](https://github.com/SteveMacenski/slam_toolbox-release)
- **Exact Version / Revision:** Jazzy `2.8.5-1`, released 2026-04-29
- **Observed Scope:** confirms upstream 2.8.5 was released into ROS 2 Jazzy.
- **Limitations:** does not prove the target image installed version.
- **Access Date:** 2026-08-14

### 10.2 Official algorithm and API contract

- **Evidence Type:** upstream official README
- **Source:** [`slam_toolbox` 2.8.5 repository and README](https://github.com/SteveMacenski/slam_toolbox/tree/2.8.5)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** documents scan/odometry-driven pose graph processing, asynchronous mapping, Occupancy Grid publication, `/scan`, required TF, `map_update_interval`, acceptance parameters and pause service.
- **Limitations:** package documentation does not prove target-AMR timing, TF completeness or map-content progression.
- **Access Date:** 2026-08-14

### 10.3 Scan admission and temporary-failure behavior

- **Evidence Type:** upstream source code
- **Sources:** [`slam_toolbox_common.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)；[`slam_toolbox_async.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_async.cpp)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** constructs sensor-data subscription and TF MessageFilter; async callback saves scan header, logs and returns on missing odom pose or invalid laser, and otherwise applies acceptance rules then calls `addScan()`.
- **Limitations:** MessageFilter drop observability and recovery behavior must be verified in the actual target composition.
- **Access Date:** 2026-08-14

### 10.4 OccupancyGrid refresh conditions

- **Evidence Type:** upstream source code
- **Source:** [`slam_toolbox_common.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)
- **Exact Version / Revision:** upstream tag `2.8.5`, `publishVisualizations()` and `updateMap()`
- **Observed Scope:** timer invokes map refresh; `updateMap()` returns without rasterization/publication if lifecycle publisher is absent/inactive or has zero subscribers, otherwise rasterizes current graph and publishes Occupancy Grid／metadata.
- **Limitations:** publication timestamp alone is not evidence that a measurement was accepted into the graph.
- **Access Date:** 2026-08-14

### 10.5 Lifecycle completion／termination

- **Evidence Type:** upstream source code
- **Source:** [`slam_toolbox_common.cpp`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/src/slam_toolbox_common.cpp)
- **Exact Version / Revision:** upstream tag `2.8.5`, `on_activate()`／`on_deactivate()`
- **Observed Scope:** activate creates scan interfaces and publication threads; deactivate interrupts threads, deactivates publishers and removes scan filter/subscription/services.
- **Limitations:** external operating flow must request the transition when the user completes or terminates mapping.
- **Access Date:** 2026-08-14

### 10.6 Official asynchronous composition

- **Evidence Type:** upstream launch and configuration
- **Sources:** [`online_async_launch.py`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/launch/online_async_launch.py)；[`mapper_params_online_async.yaml`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/config/mapper_params_online_async.yaml)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** official composition starts the lifecycle async node and configures mapping mode, one scan topic, frames, transform timeout, queue, measurement acceptance parameters and map update interval.
- **Limitations:** example values are not automatically valid deployment values for this AMR.
- **Access Date:** 2026-08-14

## 11. Recommended 04 Record

```text
SYS-006 Continuous Map Update
Candidate Mature Solution: ROS 2 Jazzy slam_toolbox 2.8.5-1 online asynchronous mapping
Coverage Status: Fully Covered
Covered Scope: valid scan/TF/odometry admission; pose-graph continuation; periodic conditional OccupancyGrid refresh; temporary invalid-input drop/wait with current graph retention; user-requested lifecycle completion/termination
Custom Behavior Gap: None
Configuration / Composition Gap: authoritative scan; TF/odometry; async acceptance/update parameters; active map consumer; operator command to lifecycle deactivate
Evidence Gap: accepted-data-to-map progression; temporary-loss retention and recovery; publication conditions; no post-deactivate updates
MVP Change Candidate: None
```

建議完成SYS-006 record後才進入SYS-007；不要在本項加入SLAM initialization、storage或read-back behavior。
