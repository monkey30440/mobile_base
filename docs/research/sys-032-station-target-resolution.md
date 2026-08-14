# SYS-032 Station Target Resolution — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-032 Station Target Resolution**：系統應使用目前場域之 Station Catalog，將使用者提交的 Station ID 解析為該 Station 預先定義之 canonical `geometry_msgs/msg/PoseStamped`；Station ID 為空、找不到對應 Station 或無法解析時，系統應拒絕該目標並回報原因。

預期操作形式類似：

```text
nav_goal station charging_station
```

本項使用使用者依MVP操作規則人工選定與確認的目前場域Station Catalog，執行ID semantics、lookup與resolution：

```text
Station ID selected by SYS-008
  -> deterministic exact lookup in current admitted Station Catalog
  -> predefined canonical geometry_msgs/msg/PoseStamped
  -> SYS-033
```

Catalog selection與同場域內容正確性由使用者負責；Catalog parser失敗由resolver沿用成熟parser原因。Canonical pose最終有效性屬SYS-033；Route Graph與path planning不在本項。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solutions | ROS 2 Jazzy `geometry_msgs/msg/PoseStamped` 5.3.8-1作為resolved target；generic YAML/config parser只可負責Catalog serialization；Navigation2 1.3.12-1作為下游pose consumer與negative evidence |
| Coverage Status | **Partially Covered** |
| Mature Coverage | canonical pose型別；通用mapping／YAML decoding building blocks；Nav2下游接受`PoseStamped` |
| Missing Native Behavior | Nav2沒有本專案Station ID、canonical Station Catalog或Station-ID-to-`PoseStamped` lookup API |
| Minimum Custom Behavior Gap | 一個薄的Station resolver：接收Station ID、拒絕empty、在current admitted Catalog做deterministic exact lookup、拒絕unknown／unresolvable、成功時原樣輸出該Station預定義canonical `PoseStamped`並交給SYS-033 |
| Configuration / Composition Gap | Station ID comparison policy；current Catalog binding；terminal ID token handoff；failure reason呈現；resolved pose handoff至SYS-033 |
| Missing Evidence | target版本；empty／unknown／unresolvable reasons；exact-match與determinism；current-Catalog isolation；pose逐欄保存；沒有把Route Graph node當Station；SYS-033 handoff |
| MVP Change Candidate | `None` |

通用parser可以讀取字串、mapping與數值，但不知道哪個欄位是Station identity、哪個Catalog是目前場域、如何做exact lookup，或什麼結果代表該Station的canonical pose。因此parser reuse不能把SYS-032提升為Fully Covered。

## 3. Nav2 Has No Native Station Target Contract

Navigation2 1.3.12的`NavigateToPose.action` goal為：

```text
geometry_msgs/PoseStamped pose
string behavior_tree
```

它沒有Station ID、Station Catalog reference或lookup result。Simple Commander的`goToPose()`同樣接收pose，而不是symbolic Station ID。因此Nav2只能消費SYS-032成功解析後的canonical pose，不能完成Station resolution本身。

`geometry_msgs/msg/PoseStamped`則提供成熟的resolved target representation：

```text
header.stamp
header.frame_id
pose.position.{x,y,z}
pose.orientation.{x,y,z,w}
```

專案應重用這個標準型別，不建立私有resolved-pose type；但Station ID到該型別的關聯仍是project-specific semantics。

## 4. Route Graph Node ID Is Not Station ID

Nav2 1.3.12 `ComputeRoute.action`可以使用`uint16 start_id`與`goal_id`選擇Route Graph nodes，也可改用start／goal poses。這些ID屬nav2_route graph topology，action的結果是Route與Path；它沒有Station Catalog或Station semantic contract。

因此不可因兩者都稱為ID，就做下列等同：

```text
Station ID != Route Graph node ID
```

- Station是使用者可提交、在目前場域Catalog中有預定義canonical pose的navigation target；
- Route node是route planning graph的拓撲節點；
- Station未必與單一route node一對一；
- Station resolution不應呼叫ComputeRoute來猜測pose；
- Station與Route Graph之間不建立runtime identity／compatibility檢查，也不由SYS-032建立隱含映射；MVP由使用者人工確認資料夾內容。

這個邊界避免把target resolution偷渡成planning。

## 5. Waypoints and Docking Do Not Fill the Gap

Nav2 Waypoint Follower接收的是一組`PoseStamped` waypoints；它仍要求caller已經持有poses，沒有提供Station ID Catalog lookup。它是多點navigation execution capability，不是SYS-032 resolver。

Nav2 Docking雖可能有dock identifier與dock database概念，但其domain是dock staging、detection、control與charging workflow，不是一般Navigation Target Station。Docking也不在目前核准範圍，因此不能為了重用一個字串ID而引入。

同理，Mission Core、Station Registry或Web service都不是解決本項最小缺口的必要成熟方案。SYS-032只需要薄resolver，不需要通用管理framework。

## 6. Minimum Resolution Fragments

### 6.1 Input and lookup

- input必須是SYS-008已辨識的Station form；
- Station ID不得為空；
- resolver只能使用使用者目前選定的Station Catalog；
- lookup採deterministic exact ID match，不做substring、fuzzy match或「最接近名稱」推測；
- 同一input與同一current Catalog必須得到同一筆結果。

大小寫、前後空白或允許字元如何處理，必須由ID comparison policy明確固定。在policy核准前，不應默認case folding、trim或alias。無論採何種policy，lookup後不可存在多個候選；Catalog duplicate／ambiguity不得由resolver任選一筆，應回報無法解析。

### 6.2 Resolution and field preservation

命中Station後，resolver應取出該Station預先定義的canonical `PoseStamped`，並保存：

| Catalog target fragment | Resolver output |
|---|---|
| `header.frame_id` | 原樣保存，不在SYS-032做TF transformation |
| `header.stamp`或其Catalog-defined timestamp semantics | 依Catalog／operation contract保存，不自行猜測 |
| `position.x/y/z` | 原樣保存，不snap到Route Graph node |
| `orientation.x/y/z/w` | 原樣保存，不在SYS-032自行normalize或改yaw |

finite values、frame non-empty／transformability及quaternion validity全部交給SYS-033。SYS-032的「canonical」表示輸出型別與Catalog預定義target，不代表它可以跳過SYS-033。

## 7. Required Failure Reasons

最低可驗證failure fragments為：

| Failure reason | Condition | Required outcome |
|---|---|---|
| empty Station ID | terminal提交空ID，或依核准input policy後沒有ID | 拒絕；不執行lookup、不產生pose |
| Station ID not found | current admitted Catalog中沒有exact match | 拒絕；不得fallback到相似名稱、Route node或default Station |
| Station target unresolvable | exact match存在，但resolver無法取得／materialize其預定義canonical `PoseStamped` | 拒絕；保留具體resolution原因，不產生部分pose |

Catalog file不存在或syntax／schema無法由成熟parser載入時，resolver應沿用parser原因並回報`unresolvable`；duplicate IDs亦不得任選一筆。使用者負責人工確認Catalog屬於目前場域。Catalog可載入但本次ID不存在，才是SYS-032的`not found`。

Normative未要求大型error taxonomy。具體enum、CLI exit code或message transport留給後續interface設計，但三個分支必須可區分、可觀察、可測試。

## 8. Generic YAML Parsing Is Only a Serialization Aid

若Station Catalog最終採YAML，成熟YAML library可重用於：

- file syntax parsing；
- scalar／mapping／sequence decoding；
- 基本型別轉換與parser exception。

但目前尚未核准Catalog file schema，本項不選定特定parser或把某種key layout寫成architecture contract。即使parser成功，也不代表：

- Catalog已由使用者人工選定與確認；
- Station ID uniqueness成立；
- input ID能命中；
- 命中值是預定義canonical pose；
- pose欄位已通過SYS-033。

因此generic parser屬可重用mechanism或後續configuration choice，不是Station resolver的替代品。

## 9. Requirement Boundaries

| Requirement | Responsibility | SYS-032不得包含 |
|---|---|---|
| SYS-008 | 辨識terminal Station／Goal Pose form | 不lookup Station |
| Operator precondition | 人工選擇並確認目前場域Station Catalog | 不形成runtime resource-admission subsystem |
| SYS-032 | 以成熟parser載入current Catalog，做Station ID exact lookup並輸出預定義canonical pose | 不做Route planning或pose semantic validation |
| SYS-033 | 驗證resolved pose的finite values、frame／TF與quaternion | 不重做Station lookup |

```text
operator-confirmed current Station Catalog --+
                                              +--> SYS-032 parse/exact lookup --> PoseStamped --> SYS-033
Station ID --------- selected by SYS-008 -----+
```

本圖只表達責任關係，不決定05／06的component、language、package或internal API。

## 10. Configuration and Evidence Gaps

### Configuration / composition still required

- 核准實際Station terminal syntax；`nav_goal station charging_station`只是預期示例；
- 固定Station ID comparison policy，包括case、whitespace、allowed characters與alias是否禁止；
- 固定current Station Catalog的authoritative binding，避免跨場域或舊Catalog lookup；
- 固定resolver只使用目前人工選定場域資料夾中的Station Catalog；
- 固定empty／not-found／unresolvable reason的operator呈現與必要logging；
- 固定resolved canonical pose只交給SYS-033，不直接送往planning或Nav2。

不在此定義Catalog filename、YAML keys、schema version、class、service/action或package layout。

### Evidence required before acceptance

- 記錄target image實際安裝的Navigation2、`nav2_msgs`與`geometry_msgs`版本；
- 對empty Station ID驗證拒絕、reason及無lookup side effect；
- 對不存在ID驗證exact-match failure，不發生fuzzy／default fallback；
- 注入matched-but-unresolvable target，確認拒絕且不產生partial pose；
- 使用大小寫、前後空白、substring及相似名稱測試核准的ID comparison policy；
- 以同一ID與Catalog重複lookup，證明deterministic result；
- 切換場域後證明只查詢current admitted Catalog，不命中舊場域Station；
- 逐欄比較Catalog預定義pose與resolver output，證明frame、stamp、position與orientation保存；
- 證明Route Graph node ID與Station ID沒有隱含等同或fallback；
- 證明resolved pose交給SYS-033，且SYS-032不執行planning／navigation。

## 11. Primary-source Evidence

### 11.1 Nav2 single-pose contract

- **Evidence Type:** upstream exact-tag source
- **Source:** [`NavigateToPose.action` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)
- **Exact Version / Revision:** Navigation2／`nav2_msgs` 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** goal以`geometry_msgs/PoseStamped pose`表示；沒有Station ID、Station Catalog或lookup API。
- **Limitations:** action只證明下游pose compatibility，不完成SYS-032。
- **Access Date:** 2026-08-14

### 11.2 Route node ID negative evidence

- **Evidence Type:** upstream exact-tag source
- **Source:** [`ComputeRoute.action` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputeRoute.action)
- **Exact Version / Revision:** Navigation2／`nav2_route` 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** route request可使用`uint16 start_id/goal_id`或poses，結果為Route與Path；ID屬Route Graph computation contract。
- **Limitations:** source沒有Station Catalog semantics；route node ID不可視為Station ID。
- **Access Date:** 2026-08-14

### 11.3 Waypoint negative evidence

- **Evidence Type:** upstream exact-tag interface
- **Source:** [`FollowWaypoints.action` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowWaypoints.action)
- **Exact Version / Revision:** Navigation2／`nav2_waypoint_follower` 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** caller提供`geometry_msgs/PoseStamped[] poses`；介面沒有Station ID lookup。
- **Limitations:** waypoint execution不是Station target resolution，且本項不引入Waypoint Follower。
- **Access Date:** 2026-08-14

### 11.4 Canonical pose representation

- **Evidence Type:** ROS 2 Jazzy interface source and build-farm metadata
- **Sources:** [`PoseStamped.msg` at common_interfaces 5.3.8](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/PoseStamped.msg)；[`Pose.msg`](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/Pose.msg)；[`Header.msg`](https://github.com/ros2/common_interfaces/blob/5.3.8/std_msgs/msg/Header.msg)；[ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `geometry_msgs` 5.3.8-1
- **Observed Scope:** standard type承載frame、stamp、position與quaternion orientation。
- **Limitations:** message definition沒有Station identity或Catalog lookup semantics。
- **Access Date:** 2026-08-14

### 11.5 Jazzy binary release metadata

- **Evidence Type:** ROS build-farm status
- **Source:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** Navigation2、`nav2_msgs`、`nav2_route`、`nav2_waypoint_follower` 1.3.12-1；`geometry_msgs` 5.3.8-1
- **Observed Scope:** confirms assessed packages are available in the Jazzy binary release line.
- **Limitations:** repository availability does not prove target installation。
- **Access Date:** 2026-08-14

## 12. Recommended 04 Record

```text
SYS-032 Station Target Resolution
Candidate Mature Solution: geometry_msgs/PoseStamped 5.3.8-1 canonical output + generic Catalog parser mechanisms; Nav2 1.3.12-1 as downstream consumer
Coverage Status: Partially Covered
Covered Scope: canonical pose representation; generic serialization parsing; downstream PoseStamped compatibility
Custom Behavior Gap: thin Station resolver for empty check, mature-parser invocation, deterministic exact ID lookup in current operator-selected Catalog, unknown/unresolvable rejection reasons, pose field preservation, and SYS-033 handoff
Configuration / Composition Gap: terminal syntax; ID comparison policy; current Catalog binding; manual site-folder precondition; reason presentation; SYS-033 handoff
Evidence Gap: target versions; three failure fragments; exact deterministic lookup; current-Catalog isolation; field preservation; no Route-node equivalence; no planning execution
MVP Change Candidate: None
```

custom code只應補project-specific Station semantics；不得擴張成Station Registry、Mission Core、Docking、Waypoint execution或Route planning framework。
