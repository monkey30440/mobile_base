# SYS-008 Navigation Target — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-008 Navigation Target**：系統應支援以下 Navigation Target：Station、Goal Pose。

本項只判定v0.1 terminal entry能否接收並區分兩種外部target form：

```text
terminal input
  -> Station form  -> SYS-032
  -> Goal Pose form -> SYS-009
```

本項不負責Goal Pose normalization、Station resolution、canonical pose validation、人工Navigation Resource確認或導航執行。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 `nav2_msgs/action/NavigateToPose` 1.3.12-1；Goal Pose與下游canonical target沿用`geometry_msgs/msg/PoseStamped` 5.3.8-1 |
| Coverage Status | **Partially Covered** |
| Natively Covered | Goal Pose有ROS標準`PoseStamped` representation，Nav2 `NavigateToPose.Goal.pose`原生接受該型別 |
| Not Natively Covered | Nav2核心action／Simple Commander沒有Station ID target form，也沒有Station／Goal Pose tagged input union |
| Minimum Custom Behavior Gap | 一個最小terminal-facing form discriminator／input adapter，只需接受並區分`Station`與`Goal Pose`，並把原始內容送往各自下游責任 |
| Configuration / Composition Gap | 固定terminal syntax與無歧義form discriminator；固定兩個handoff destination；Goal Pose terminal representation與Station ID文字邊界 |
| Missing Evidence | target安裝版本；兩種form能被明確區分；Station ID完整交給SYS-032；Goal Pose資料完整交給SYS-009；SYS-008不自行normalize、resolve、validate或啟動導航 |
| MVP Change Candidate | `None`；保留Station與Goal Pose兩種normative forms |

整體不能判為Fully Covered：成熟Nav2原生覆蓋pose-shaped goal，卻沒有symbolic Station ID form或兩種form的terminal discriminator。缺口只在入口分類，不需要建立Mission Core、Station Registry、新navigation server或其他通用framework。

## 3. Native Goal Pose Representation

Navigation2 1.3.12的`NavigateToPose.action` goal定義為：

```text
geometry_msgs/PoseStamped pose
string behavior_tree
```

`geometry_msgs/msg/PoseStamped`由下列欄位組成：

```text
std_msgs/Header header
geometry_msgs/Pose pose
```

Header提供`stamp`與`frame_id`，Pose提供position與quaternion orientation。這證明Goal Pose已有成熟標準representation，且與Nav2單一pose導航介面直接相容。

但這不代表SYS-008可以直接把terminal Goal Pose送進Nav2：

- terminal輸入形成canonical `PoseStamped`是SYS-009；
- canonical pose的finite values、frame transformability與quaternion validity是SYS-033；
- 只有通過後續責任與navigation admission的target才能進入導航流程。

`behavior_tree`是Nav2執行設定，不是第三種Navigation Target，也不是Station ID的承載欄位。

## 4. Nav2 Has No Native Station ID Form

Navigation2 1.3.12的公開`NavigateToPose` goal只有`PoseStamped pose`與`behavior_tree`。Simple Commander `goToPose()`同樣接收pose並送出`NavigateToPose.Goal`，沒有Station ID overload。

因此Station在SYS-008只能先被辨識為symbolic external form：

```text
Station form recognized
  -> preserve submitted Station ID
  -> hand off to SYS-032
```

下列工作不計入SYS-008 custom gap：

- Station Catalog由使用者依MVP操作規則在啟動前人工選擇與確認；
- Station ID是否為空、能否命中及其canonical pose resolution：SYS-032；
- resolved canonical pose是否有效：SYS-033；
- path planning與navigation execution：後續導航requirements。

Nav2沒有Station ID form是本次對核心Nav2 1.3.12 API surface的證據結論；不是宣稱所有第三方套件都不存在station概念。對本專案而言，也沒有證據顯示另引入大型station-management方案會比薄入口更符合MVP。

## 5. Minimum Mature-solution-first Gap

最低充分作法是保留標準ROS/Nav2 goal type，只補一個薄的terminal target entry seam：

1. 接受兩種可明確區分的輸入形式；
2. Station form保留使用者提交的Station ID並交給SYS-032；
3. Goal Pose form保留使用者提交的pose資料並交給SYS-009；
4. 不在SYS-008自行形成或驗證canonical pose；
5. 不從SYS-008直接呼叫`NavigateToPose`。

本階段不指定input seam必須實作成custom ROS message、service、CLI executable或library API；這是05／06的設計選擇。04只需記錄成熟能力覆蓋邊界和不可避免的最小behavior gap。

Relative Pose、Web Panel、Docking、Mission Core與Station Registry均不在核准範圍，不得以補SYS-008為由加入。

## 6. Requirement Boundaries

| Requirement | Responsibility | 不計入SYS-008 gap的內容 |
|---|---|---|
| SYS-008 | terminal entry接受並區分Station／Goal Pose | 不normalize、不resolve、不validate |
| SYS-009 | 將Goal Pose正規化為canonical `PoseStamped`並保留絕對位置與方向語意 | Goal Pose欄位／frame／orientation處理 |
| SYS-032 | 使用目前場域Station Catalog將Station ID解析成canonical `PoseStamped` | Station lookup、missing ID與resolution failure |
| SYS-033 | 導航前驗證canonical pose的finite values、frame與quaternion | canonical pose validity與拒絕原因 |
| Operator precondition | 人工選擇與確認場域資料夾；Station target包含Station Catalog | 不形成runtime resource-admission subsystem |

責任關係為：

```text
Station input  -- SYS-008 --> SYS-032 --+
                                           +--> canonical PoseStamped --> SYS-033
Goal Pose input -- SYS-008 --> SYS-009 --+

The operator separately confirms the selected site folder and required navigation resources before startup.
```

此圖只表達責任與資料流，不提前決定05／06的component placement或實際gate scheduling。

## 7. Configuration and Evidence Gaps

### Configuration / composition still required

- 定義terminal如何無歧義標示`Station`或`Goal Pose`；
- 定義Station ID在SYS-008 interface boundary的基本文字承載方式，但不在此判斷是否存在；
- 定義Goal Pose terminal representation，使其資料可完整交給SYS-009，但不在此制定normalization rules；
- 固定Station handoff至SYS-032、Goal Pose handoff至SYS-009；
- 確保兩條分支最後都經SYS-033；Navigation Resources由使用者依操作規則人工確認；
- Nav2 `behavior_tree`使用預設或既有核准設定，不暴露為target form。

### Evidence required before acceptance

- 記錄target image實際安裝的`nav2_msgs`、Navigation2與`geometry_msgs`版本；
- 從terminal分別提交Station與Goal Pose，證明receiver可靠且無歧義地分類；
- 證明Station ID內容沒有遺失或改寫，且只交給SYS-032；
- 證明Goal Pose資料沒有遺失或被SYS-008正規化，且只交給SYS-009；
- 證明unsupported／ambiguous form不會被任選為其中一類；其拒絕方式須在後續interface設計固定；
- 證明SYS-008不進行Station lookup、pose validation、Navigation Resource確認或`NavigateToPose` submission；
- 以整合證據確認SYS-009／SYS-032的canonical outputs最終可經SYS-033後送到Nav2標準action。

## 8. Primary-source Evidence

### 8.1 NavigateToPose goal contract

- **Evidence Type:** upstream exact-tag source
- **Source:** [`NavigateToPose.action` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** goal只有`geometry_msgs/PoseStamped pose`與`string behavior_tree`；沒有Station ID或tagged target variant。
- **Limitations:** action definition不負責本專案terminal entry、normalization、resolution或validation。
- **Access Date:** 2026-08-14

### 8.2 PoseStamped representation

- **Evidence Type:** ROS 2 Jazzy interface source and build-farm metadata
- **Sources:** [`PoseStamped.msg` on common_interfaces Jazzy branch](https://github.com/ros2/common_interfaces/blob/jazzy/geometry_msgs/msg/PoseStamped.msg)；[`Pose.msg`](https://github.com/ros2/common_interfaces/blob/jazzy/geometry_msgs/msg/Pose.msg)；[`Header.msg`](https://github.com/ros2/common_interfaces/blob/jazzy/std_msgs/msg/Header.msg)；[ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `geometry_msgs` 5.3.8-1 in the assessed Jazzy release snapshot
- **Observed Scope:** standard representation包含timestamp、frame、position與quaternion orientation。
- **Limitations:** message structure本身不執行SYS-009 normalization或SYS-033 validation，也不定義terminal syntax。
- **Access Date:** 2026-08-14

### 8.3 Nav2 public client shape

- **Evidence Type:** upstream exact-tag source
- **Source:** [`BasicNavigator.goToPose()` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_simple_commander/nav2_simple_commander/robot_navigator.py)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** public single-goal method接受pose並建立`NavigateToPose.Goal`；沒有Station ID overload。
- **Limitations:** assessed scope是core Nav2 action／client，不是所有可能的third-party packages。
- **Access Date:** 2026-08-14

### 8.4 Jazzy binary release metadata

- **Evidence Type:** ROS build-farm status
- **Source:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** Navigation2／`nav2_msgs` 1.3.12-1；`geometry_msgs` 5.3.8-1
- **Observed Scope:** confirms the assessed packages are available in the Jazzy binary release line.
- **Limitations:** repository availability does not prove the versions installed in the target image.
- **Access Date:** 2026-08-14

## 9. Recommended 04 Record

```text
SYS-008 Navigation Target
Candidate Mature Solution: ROS 2 Jazzy Navigation2 nav2_msgs/action/NavigateToPose 1.3.12-1 with geometry_msgs/msg/PoseStamped 5.3.8-1
Coverage Status: Partially Covered
Covered Scope: native Goal Pose representation and downstream standard NavigateToPose goal type
Custom Behavior Gap: minimal terminal-facing form discriminator/input adapter for Station vs Goal Pose; no normalization, resolution, validation or resource confirmation
Configuration / Composition Gap: terminal form syntax; Station handoff to SYS-032; Goal Pose handoff to SYS-009; later SYS-033 validation; operator-confirmed site folder is an external precondition
Evidence Gap: target versions; unambiguous form discrimination; branch-specific data preservation and handoff; no premature processing or Nav2 submission
MVP Change Candidate: None
```

完成SYS-008 record後才進入下一個requirement；不得用本項建立未核准的mission、station-management、web或docking scope。
