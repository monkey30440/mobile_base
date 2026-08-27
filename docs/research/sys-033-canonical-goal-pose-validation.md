> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-033 Canonical Goal Pose Validation — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-033 Canonical Goal Pose Validation**：系統應於導航開始前驗證 canonical `geometry_msgs/msg/PoseStamped`。其位置與方向數值應為有限值、座標框架不得為空且應可轉換至目前導航使用之全域座標框架、方向 quaternion 應有效；驗證失敗時，系統應拒絕該目標並回報原因。只有通過驗證的 canonical `PoseStamped` 才可提供給後續導航流程。

輸入只來自：

```text
SYS-009 Goal Pose Normalization --+
                                   +--> SYS-033 --> admitted canonical PoseStamped
SYS-032 Station Resolution -------+
```

本項不檢查map bounds、occupancy、path feasibility、人工Navigation Resource確認或localization；這些分別屬SYS-011／SYS-014、operator precondition與SYS-010。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solutions | ROS 2 Jazzy `geometry_msgs/msg/PoseStamped` 5.3.8-1；C++ standard `std::isfinite`；geometry2 `tf2`／`tf2_ros` 0.36.22-1的quaternion length與Buffer transform APIs；Navigation2 1.3.12-1作為下游negative comparison |
| Coverage Status | **Partially Covered** |
| Mature Coverage | pose欄位結構；finite primitives；quaternion norm primitives；frame/time transformability query、timeout與TF error detail |
| Missing Native Behavior | 沒有單一成熟API同時完成全部SYS-033 checks、形成project-level pass/fail+reason，並保證失敗goal不會提供給後續導航 |
| Minimum Custom Behavior Gap | 一個薄的combined canonical-pose validator／gate，依固定順序組合finite、frame、TF與quaternion primitives；任何失敗輸出明確原因且不forward，全部通過才forward原canonical pose |
| Configuration / Composition Gap | current navigation global frame；timestamp interpretation；TF timeout；quaternion unit tolerance；failure priority／reason呈現；SYS-009／032 ingress與downstream gate placement |
| Missing Evidence | target版本；每一failure fragment；TF timeout／error detail；quaternion boundaries；all-pass forwarding；任一fail零downstream submission；輸入pose不被validation改寫 |
| MVP Change Candidate | `None` |

成熟primitive足以避免自製數學與TF機制，但把它們組成normative要求的一次性admission contract仍是project-specific薄邏輯，因此不能判為Fully Covered。

## 3. Standard Message Defines Structure, Not Validity

`geometry_msgs/msg/PoseStamped`只定義：

```text
std_msgs/Header header
geometry_msgs/Pose pose
```

展開為frame、timestamp、position與quaternion orientation欄位。Generated ROS message可以承載空字串、NaN／Inf與任意四個orientation數值；message definition沒有宣告finite、non-empty frame、TF connectivity或unit-quaternion constraint。

因此「已是typed `PoseStamped`」不能作為SYS-033 PASS。SYS-009或SYS-032成功產生canonical type後，仍必須經本項validator。

## 4. Reusable Validation Primitives

### 4.1 Finite-number checks

C++ standard `<cmath>`提供`std::isfinite`，可逐一檢查：

```text
position.x, position.y, position.z
orientation.x, orientation.y, orientation.z, orientation.w
```

任何NaN、positive infinity或negative infinity都必須拒絕。此primitive完全成熟；project gap只在完整enumeration、failure reason與gate composition。若後續採其他語言，應使用該runtime等價的IEEE finite predicate；本筆記不決定language。

### 4.2 Frame non-empty and transformability

最低檢查為：

1. `header.frame_id`非空；
2. 取得current navigation global frame；
3. 依核准timestamp policy，用`tf2_ros::Buffer::canTransform()`查詢source frame到global frame；
4. 使用有限timeout，並保留`errstr`或tf2 exception detail作為失敗原因。

tf2可區分lookup、connectivity、extrapolation、timeout等transform failure detail。`transform()`可實際轉換typed `PoseStamped`，但SYS-033 normative只要求「可轉換」；本項不應擅自改寫canonical pose。若source frame已是current global frame，仍應依核准policy處理同frame與timestamp語意，而不是繞過其他checks。

### 4.3 Quaternion validity

`tf2::Quaternion`提供`length2()`／`length()`、`normalize()`與`normalized()`。SYS-033可重用norm primitive判斷orientation：

- 四個components先通過finite check；
- norm不得為零或接近不可定義範圍；
- norm必須落在核准的unit-quaternion tolerance內。

`normalize()`能產生unit quaternion，但SYS-033是validator，不是repair step。對超出核准tolerance的輸入直接normalize後放行，會把「invalid應拒絕」改成靜默修正；因此這裡主要重用`length2()`／`length()`做判定。tolerance數值必須經後續設計與實機／整合證據固定，本研究不提前指定。

## 5. Minimum Combined Validation Contract

最低充分validation fragments為：

| Fragment | PASS condition | Failure reason fragment |
|---|---|---|
| Position finite | `x/y/z`全部finite | `non-finite position`，指出欄位 |
| Orientation finite | quaternion四個components全部finite | `non-finite orientation`，指出欄位 |
| Frame present | `frame_id`非空 | `empty frame` |
| Quaternion non-degenerate | norm可計算且不為零／不可定義 | `invalid quaternion norm` |
| Quaternion unit validity | norm在核准tolerance內 | `quaternion not unit` |
| Frame transformability | 在pose timestamp與TF timeout policy下，可轉到current navigation global frame | `transform unavailable`，附source、target、time與tf2 detail |

validator必須具有all-or-nothing gate：

```text
all fragments PASS -> forward the unchanged canonical PoseStamped
any fragment FAIL  -> reject + reason; forward nothing
```

檢查順序與多重錯誤時的priority需固定，使同一輸入得到deterministic result；但本研究不提前規定具體priority或一次回報一個／多個reason。

## 6. Nav2 Goal Initialization Is Not Full SYS-033 Admission

Navigation2 1.3.12 `NavigateToPoseNavigator::goalReceived()`先載入behavior tree，再呼叫`initializeGoalPose()`。後者：

- 取得current robot pose；
- 嘗試將goal pose轉到configured global frame；
- transform失敗時記錄source／target frame並回傳false；
- 成功後把transformed goal放進behavior-tree blackboard。

這是有用的下游defense，但沒有完整覆蓋SYS-033：

1. goal已提交到Nav2 action processing後才執行，不滿足「只有通過者才可提供給後續導航」的project gate；
2. source沒有在`goalReceived()`／`initializeGoalPose()`逐欄執行position與orientation finite checks；
3. source沒有形成SYS-033的zero／non-unit quaternion validation與project tolerance；
4. 它還檢查current robot pose與behavior tree file，這些不是SYS-033 target validity fragments；
5. 原生log／false return不是本專案完整、穩定的combined reason contract。

因此不可直接把Nav2 runtime rejection當成SYS-033 Fully Covered。SYS-033應在任何`NavigateToPose` submission之前完成；Nav2保留自己的transform check作為defense-in-depth。

## 7. Explicit Exclusions

下列條件不得加入SYS-033：

- goal是否在map image bounds內；
- goal cell是否free、occupied或unknown；
- robot footprint是否能放在goal；
- 是否存在可行route或path；
- planner／controller能否到達；
- Map Package 或 Route Graph 是否 admitted；
- localization是否有效。

這些是map／planning／obstacle、operator precondition或SYS-010邊界。canonical pose可通過SYS-033但之後因無路可達而失敗；這不表示SYS-033漏驗證。

## 8. Configuration and Evidence Gaps

### Configuration / composition still required

- 固定current navigation global frame的authoritative來源；
- 固定`header.stamp`為zero／latest或explicit time時的TF查詢語意；
- 固定TF query timeout，避免無限等待；
- 固定unit-quaternion tolerance與zero／near-zero判定方式；
- 固定validation順序、failure reason identifiers、operator文字及必要logging；
- 固定SYS-009／SYS-032 outputs只能先進SYS-033，再進後續navigation；
- 保持validator read-only，不在失敗時normalize quaternion或transform／改寫pose。

本筆記不決定threshold數值、language、class、node、service/action、package或internal API。

### Evidence required before acceptance

- 記錄target image實際安裝的`geometry_msgs`、`tf2`、`tf2_ros`、`tf2_geometry_msgs`與Navigation2版本；
- 對position及orientation每個欄位分別注入NaN、+Inf、-Inf，確認拒絕與field-specific reason；
- 測試empty frame、unknown frame、disconnected TF tree、past／future extrapolation及timeout，確認拒絕並保留source／target／time與tf2 detail；
- 測試zero、near-zero、unit、tolerance boundary及明顯non-unit quaternion；
- 對SYS-009與SYS-032各提供一筆valid pose，證明全部通過後原訊息逐欄不變地forward；
- 證明任何單項failure都不建立下游navigation goal；
- 證明多重failure依固定priority得到deterministic reason；
- 證明map bounds、occupancy、path feasibility、人工Navigation Resource確認與localization沒有被誤納入SYS-033；
- 保留Nav2原生transform rejection測試作為downstream defense evidence，但不充當SYS-033唯一證據。

## 9. Primary-source Evidence

### 9.1 PoseStamped structure

- **Evidence Type:** ROS 2 Jazzy interface source and build-farm metadata
- **Sources:** [`PoseStamped.msg` at common_interfaces 5.3.8](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/PoseStamped.msg)；[`Pose.msg`](https://github.com/ros2/common_interfaces/blob/5.3.8/geometry_msgs/msg/Pose.msg)；[`Header.msg`](https://github.com/ros2/common_interfaces/blob/5.3.8/std_msgs/msg/Header.msg)；[ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `geometry_msgs` 5.3.8-1
- **Observed Scope:** message定義frame、timestamp、position與quaternion orientation欄位，但不宣告SYS-033 validity constraints。
- **Limitations:** typed message不等於validated canonical goal。
- **Access Date:** 2026-08-14

### 9.2 Finite-number primitive

- **Evidence Type:** ISO C++ working draft
- **Source:** [C++ working draft `<cmath>` synopsis and classification functions](https://eel.is/c++draft/c.math)
- **Exact Version / Revision:** current public ISO C++ working draft; target compiler／standard-library version remains runtime evidence
- **Observed Scope:** standard floating-point classification includes `isfinite` for rejecting infinite／NaN values。
- **Limitations:** primitive不列舉PoseStamped fields，也不形成project failure contract。
- **Access Date:** 2026-08-14

### 9.3 tf2 quaternion primitives

- **Evidence Type:** upstream exact-version source／Jazzy API
- **Sources:** [`tf2::Quaternion` source at geometry2 0.36.22](https://github.com/ros2/geometry2/blob/0.36.22/tf2/include/tf2/LinearMath/Quaternion.hpp)；[`tf2` Jazzy API index](https://docs.ros.org/en/jazzy/p/tf2/genindex.html)
- **Exact Version / Revision:** geometry2／`tf2` 0.36.22-1
- **Observed Scope:** exposes quaternion length、length-squared、normalize與normalized operations。
- **Limitations:** library不替專案選unit tolerance；normalize capability不表示invalid input應被修復放行。
- **Access Date:** 2026-08-14

### 9.4 tf2 transformability and errors

- **Evidence Type:** upstream exact-version source
- **Sources:** [`tf2_ros::Buffer` at geometry2 0.36.22](https://github.com/ros2/geometry2/blob/0.36.22/tf2_ros/include/tf2_ros/buffer.hpp)；[`tf2_ros buffer.cpp` at 0.36.22](https://github.com/ros2/geometry2/blob/0.36.22/tf2_ros/src/buffer.cpp)；[`tf2 exceptions.hpp` at 0.36.22](https://github.com/ros2/geometry2/blob/0.36.22/tf2/include/tf2/exceptions.hpp)
- **Exact Version / Revision:** geometry2／`tf2_ros` 0.36.22-1
- **Observed Scope:** supports `canTransform` with time／timeout／error string and typed transforms；lookup、connectivity、extrapolation等exception categories提供failure detail。
- **Limitations:** TF success不涵蓋finite或quaternion validity，也不形成combined admission result。
- **Access Date:** 2026-08-14

### 9.5 Nav2 goal initialization comparison

- **Evidence Type:** upstream exact-tag source
- **Sources:** [`NavigateToPose.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/NavigateToPose.action)；[`navigate_to_pose.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bt_navigator/src/navigators/navigate_to_pose.cpp)；[`BtActionServer` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_server_impl.hpp)；[`SimpleActionServer` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_util/include/nav2_util/simple_action_server.hpp)
- **Exact Version / Revision:** Navigation2 1.3.12 / Jazzy binary release 1.3.12-1
- **Observed Scope:** navigator action processing attempts current-pose acquisition and goal transformation aftersubmission；failed initialization terminates Nav2 processing。
- **Limitations:** does not supply complete finite/quaternion checks or an upstream project gate that prevents invalid canonical poses from being submitted。
- **Access Date:** 2026-08-14

### 9.6 Jazzy binary release metadata

- **Evidence Type:** ROS build-farm status
- **Source:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `geometry_msgs` 5.3.8-1；geometry2／`tf2`／`tf2_ros`／`tf2_geometry_msgs` 0.36.22-1；Navigation2 1.3.12-1
- **Observed Scope:** confirms assessed ROS packages are available in the Jazzy binary release line.
- **Limitations:** repository availability does not prove target installation。
- **Access Date:** 2026-08-14

## 10. Recommended 04 Record

```text
SYS-033 Canonical Goal Pose Validation
Candidate Mature Solution: geometry_msgs/PoseStamped 5.3.8-1 + std::isfinite + tf2/tf2_ros 0.36.22-1 primitives; Nav2 1.3.12-1 downstream defense
Coverage Status: Partially Covered
Covered Scope: pose structure; finite predicates; quaternion norm operations; frame/time transformability, timeout and TF error details
Custom Behavior Gap: thin combined validator/gate that applies every required fragment, rejects with stable reason, forwards unchanged pose only on all-pass
Configuration / Composition Gap: navigation global frame; timestamp policy; TF timeout; quaternion tolerance; failure priority/reasons; ingress/downstream gate placement
Evidence Gap: target versions; every failure fragment; TF error cases; quaternion boundaries; deterministic reasons; unchanged all-pass forwarding; zero downstream submission on failure
MVP Change Candidate: None
```

custom code只應組合成熟primitive形成最小admission gate；不得加入map、occupancy、planning、resource或localization checks。
