# SYS-009 Goal Pose Normalization — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-009 Goal Pose Normalization**：系統應接受使用者透過終端提交以公尺表示之絕對 `x`、`y`，以及以度表示之 `yaw-deg` Goal Pose，並將其正規化為目前導航全域座標框架中的 canonical `geometry_msgs/msg/PoseStamped`；系統應保留其絕對位置與方向語意，將 `yaw-deg` 轉換為 quaternion，並依操作規則設定 frame 與 timestamp。必要欄位缺失或無法解析時，系統應拒絕該目標並回報原因。

研究範圍只有：

```text
terminal absolute x[m], y[m], yaw-deg[degree]
  -> parse required values
  -> degrees to radians
  -> yaw to quaternion
  -> apply frame/stamp operation policy
  -> canonical geometry_msgs/msg/PoseStamped
```

SYS-008只負責辨識Goal Pose form；SYS-032處理Station；SYS-033負責canonical pose的finite／frame-TF／quaternion最終有效性。Navigation Resources由使用者依MVP操作規則人工確認，不構成SYS-009責任。Relative Pose不在範圍。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solutions | ROS 2 Jazzy `geometry_msgs/msg/PoseStamped` 5.3.8-1；`tf2`／`tf2_geometry_msgs` 0.36.22-1的`Quaternion::setRPY()`、`normalize()`與`toMsg()`；標準CLI argument parser能力 |
| Coverage Status | **Partially Covered** |
| Mature Coverage | canonical pose型別；公尺／弧度ROS慣例；yaw-to-quaternion與quaternion normalization；typed ROS message construction；CLI required／numeric argument parsing mechanisms |
| Missing Native Behavior | ROS 2/Nav2沒有原生`nav_goal pose --x ... --y ... --yaw-deg ...`命令，可同時套用本專案frame/stamp policy並產生SYS-009結果 |
| Minimum Custom Behavior Gap | 一個薄的terminal CLI／normalization adapter，將required absolute `x/y/yaw-deg`組裝成canonical `PoseStamped`，並在缺失或無法解析時拒絕及回報parser原因 |
| Configuration / Composition Gap | command syntax；current navigation global frame來源；timestamp policy；2D `z/roll/pitch`填值規則；成功結果交給SYS-033的composition |
| Missing Evidence | target版本；required flags；numeric parse failures；degrees-to-radians與known-angle quaternion；x/y與absolute semantics保留；frame/stamp policy；canonical output handoff |
| MVP Change Candidate | `None` |

成熟套件已覆蓋資料型別、角度與quaternion運算，不必自製數學或pose message；但仍缺少把專案指定terminal contract串成單一操作的薄膠合層，因此不能判為Fully Covered。

## 3. Canonical Pose Representation

`geometry_msgs/msg/PoseStamped`的標準結構是：

```text
std_msgs/Header header
geometry_msgs/Pose pose
```

其必要輸出欄位為：

```text
header.stamp
header.frame_id
pose.position.{x,y,z}
pose.orientation.{x,y,z,w}
```

這個型別已完整承載目前導航全域座標框架中的絕對位置與方向，不需要專案私有pose type。Navigation2 1.3.12的`NavigateToPose.Goal.pose`同樣使用`PoseStamped`，因此SYS-009 canonical output不需要再轉成另一種Nav2 goal representation。

## 4. Required Normalization Mapping

假設CLI形式類似：

```text
nav_goal pose --x 2.0 --y 3.0 --yaw-deg 90
```

最低充分mapping為：

| Terminal input / policy | Canonical `PoseStamped` field | Required behavior |
|---|---|---|
| `--x` metres | `pose.position.x` | 原值保留，不加robot current position |
| `--y` metres | `pose.position.y` | 原值保留，不加robot current position |
| 2D operation convention | `pose.position.z` | 依固定2D規則填值，通常為`0.0` |
| `--yaw-deg` degrees | `pose.orientation` | degree轉radian後，以roll=`0`、pitch=`0`建立yaw quaternion |
| current navigation global frame policy | `header.frame_id` | 使用操作當下選定的navigation global frame，不由使用者輸入相對frame |
| timestamp policy | `header.stamp` | 依核准操作規則填入，不在adapter任意猜測 |

絕對語意的關鍵是`x=2.0, y=3.0`代表global frame中的座標，而不是「從機器人目前位置再走2 m、3 m」。adapter不得讀取robot current pose後相加，也不得把輸入轉成Relative Pose。

## 5. Degrees to Quaternion Using Mature tf2

ROS REP-103規定角度使用radians，yaw是繞Z軸的旋轉；CLI契約則刻意使用degrees方便操作。因此必要轉換是：

```text
yaw_rad = yaw_deg * pi / 180
```

成熟C++ building blocks可表達後續步驟：

```text
tf2::Quaternion q
q.setRPY(0.0, 0.0, yaw_rad)
q.normalize()
geometry_msgs quaternion = tf2::toMsg(q)
```

`setRPY()`使用fixed-axis roll／pitch／yaw，yaw對應Z軸；`normalize()`產生unit quaternion；`tf2::toMsg()`轉成`geometry_msgs/msg/Quaternion`。這些能力已由Jazzy geometry2提供，所以custom gap不是自行實作旋轉數學，而是很薄的input-to-message composition。

語言尚未定案。上述C++ API用來證明成熟能力存在，不代表05／06必須採C++；若後續選Python，可採ROS支援的等價quaternion能力或直接使用標準數學，但仍須保留相同可驗證mapping。

## 6. Terminal Parsing and Failure Reasons

ROS 2 CLI以argument parser建立command與verb options；成熟parser可將`--x`、`--y`、`--yaw-deg`設為required numeric arguments。最低SYS-009 failure behavior為：

| Input failure | Required outcome |
|---|---|
| 缺少`--x`、`--y`或`--yaw-deg` | parser拒絕，不建立canonical pose，顯示缺少的required argument |
| value無法解析為數字 | parser拒絕，不建立canonical pose，顯示對應argument與invalid numeric value |
| command/form不符合Goal Pose syntax | parser拒絕並顯示usage／原因；form辨識責任仍屬SYS-008 |

一般CLI parsing framework可以提供required/type conversion、usage、stderr與non-zero exit；但是ROS 2 Jazzy沒有現成Nav2 verb能直接完成這個專案專屬syntax、frame/stamp policy與canonical handoff，所以仍需要thin adapter。

`NaN`或`Inf`在某些numeric parsers可能可以形成floating-point value；這不是「無法解析」。是否為finite、frame是否有效以及quaternion最終是否有效，都由SYS-033拒絕，SYS-009不應重複建立semantic validator。

## 7. Minimum Adapter Responsibilities

薄adapter只需負責：

1. 提供Goal Pose terminal command與`--x`、`--y`、`--yaw-deg`三個required numeric arguments；
2. 對missing／unparseable input停止處理並呈現parser reason；
3. 將degrees乘以`pi / 180`轉為radians；
4. 使用成熟quaternion能力，以roll／pitch為0、yaw為輸入建立orientation並normalize；
5. 建立`PoseStamped`，原樣填入absolute x/y並依2D規則填z；
6. 從operation policy取得current navigation global frame與timestamp並填入header；
7. 把canonical message交給SYS-033，不直接啟動導航。

不屬adapter責任：

- Station Catalog或Station ID：SYS-032；
- finite、TF transformability、frame non-empty與quaternion final validity：SYS-033；
- Map Package／Route Graph／configuration由使用者在啟動前人工選擇與確認；
- relative displacement、path planning或`NavigateToPose` execution；
- Web Panel、Mission Core、Docking或通用command framework。

本筆記不決定adapter語言、package、node topology、service/action/internal API或file layout。

## 8. Configuration and Evidence Gaps

### Configuration / composition still required

- 核准實際command name與flags；本筆記中的`nav_goal pose`只是預期syntax示例；
- 定義current navigation global frame的authoritative operation-policy來源；
- 定義timestamp使用command acceptance time、zero／latest語意或其他核准規則；
- 固定2D `z=0`、roll=`0`、pitch=`0`規則；
- 固定parse error的terminal呈現、exit status與必要operation logging；
- 固定canonical output交給SYS-033的composition，不直接送往Nav2。

### Evidence required before acceptance

- 記錄target image實際安裝的`geometry_msgs`、`tf2`、`tf2_geometry_msgs`及CLI runtime版本；
- 對缺少各required flag逐一測試，確認拒絕、具體原因與non-zero result；
- 對`--x`、`--y`、`--yaw-deg`逐一注入unparseable text，確認拒絕及argument-specific reason；
- 用`0°`、`90°`、`-90°`、`180°`驗證degree-to-radian與quaternion結果；比較quaternion時接受`q`與`-q`表示相同rotation；
- 證明x/y數值逐值保留，且不與robot current pose相加；
- 證明z、roll、pitch、frame與stamp符合核准operation policy；
- 證明成功輸出typed canonical `PoseStamped`並交給SYS-033；
- 以NaN／Inf、empty／unknown frame等案例證明最終semantic rejection由SYS-033負責；
- 證明CLI沒有Relative Pose模式或未核准的Web／Mission／Docking入口。

## 9. Primary-source Evidence

### 9.1 PoseStamped canonical structure

- **Evidence Type:** ROS 2 Jazzy interface source and build-farm metadata
- **Sources:** [`PoseStamped.msg` at common_interfaces 5.3.8](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/PoseStamped.msg)；[`Pose.msg`](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/Pose.msg)；[`Header.msg`](https://github.com/ros2/common_interfaces/blob/5.3.8/std_msgs/msg/Header.msg)；[ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `geometry_msgs` 5.3.8-1
- **Observed Scope:** standard stamped pose包含frame、timestamp、position與quaternion orientation。
- **Limitations:** message type不執行CLI parsing或SYS-033 validation。
- **Access Date:** 2026-08-14

### 9.2 Angle and frame conventions

- **Evidence Type:** ROS standard
- **Source:** [REP-103 Standard Units of Measure and Coordinate Conventions](https://www.ros.org/reps/rep-0103.html)
- **Exact Version / Revision:** REP-103, current accepted ROS convention
- **Observed Scope:** linear units使用metres、angular units使用radians；yaw為繞Z軸旋轉。
- **Limitations:** requirement額外指定terminal yaw以degrees輸入，因此adapter仍須明確轉換。
- **Access Date:** 2026-08-14

### 9.3 tf2 quaternion construction and ROS conversion

- **Evidence Type:** upstream exact-version source／Jazzy API
- **Sources:** [`tf2::Quaternion` source at geometry2 0.36.22](https://github.com/ros2/geometry2/blob/0.36.22/tf2/include/tf2/LinearMath/Quaternion.hpp)；[`tf2` Jazzy API index](https://docs.ros.org/en/jazzy/p/tf2/genindex.html)；[`tf2::toMsg(Quaternion)` Jazzy API](https://docs.ros.org/en/jazzy/p/tf2_geometry_msgs/generated/function_namespacetf2_1a3c63d973aea4be899806b134ef25ab81.html)
- **Exact Version / Revision:** geometry2／`tf2`／`tf2_geometry_msgs` 0.36.22-1 in the assessed Jazzy binary release
- **Observed Scope:** `setRPY()`、`normalize()`與`toMsg()`提供yaw radians到ROS quaternion的成熟building blocks。
- **Limitations:** APIs不提供本專案terminal syntax、frame/stamp policy或handoff。
- **Access Date:** 2026-08-14

### 9.4 ROS 2 CLI parsing framework

- **Evidence Type:** upstream exact-release source and build-farm metadata
- **Sources:** [`ros2cli command framework` 0.32.11](https://github.com/ros2/ros2cli/blob/0.32.11/ros2cli/ros2cli/command/command.py)；[`ros2action send_goal` parser example](https://github.com/ros2/ros2cli/blob/0.32.11/ros2action/ros2action/verb/send_goal.py)；[ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `ros2cli`／`ros2action` 0.32.11-1
- **Observed Scope:** ROS CLI verbs definearguments through an argument parser；mature parsing mechanisms provide typed input and error reporting patterns.
- **Limitations:** no assessed standard verb implements`nav_goal pose --x --y --yaw-deg`plus project frame/stamp policy.
- **Access Date:** 2026-08-14

### 9.5 Downstream type compatibility

- **Evidence Type:** upstream exact-tag source
- **Source:** [`NavigateToPose.action` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** downstreamgoal uses`geometry_msgs/PoseStamped pose`，所以canonical output不需要專案私有navigation target type。
- **Limitations:** type compatibility不授權SYS-009繞過SYS-033直接執行導航。
- **Access Date:** 2026-08-14

## 10. Recommended 04 Record

```text
SYS-009 Goal Pose Normalization
Candidate Mature Solution: geometry_msgs/PoseStamped 5.3.8-1 + tf2/tf2_geometry_msgs 0.36.22-1 + standard CLI argument parsing
Coverage Status: Partially Covered
Covered Scope: canonical type; metres/radians convention; yaw-to-quaternion construction and normalization; typed argument parsing mechanisms
Custom Behavior Gap: thin terminal CLI/normalization adapter for required absolute x/y/yaw-deg, degree conversion, frame/stamp policy, PoseStamped construction, parser reason, and SYS-033 handoff
Configuration / Composition Gap: command syntax; authoritative global frame; timestamp policy; 2D z/roll/pitch; error presentation; SYS-033 handoff
Evidence Gap: target versions; required/malformed arguments; known-angle quaternions; x/y absolute preservation; frame/stamp/2D policy; typed output; no direct navigation
MVP Change Candidate: None
```

custom code應只補上述薄seam；不要把SYS-033 validation或通用mission／web／station framework塞進SYS-009。
