> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-023 Robot Description Reuse Assessment Evidence

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的下列定案需求，不修改或重新解釋需求：

> **SYS-023 機器人描述**：系統應提供機器人幾何、座標系與關節定義，供感知、定位、建圖與導航使用。

研究問題是：ROS 2 Jazzy 的成熟方案能否提供 SYS-023 所需的描述與發布機制，以及仍有哪些專案資料與驗證缺口。

本筆記不是 Architecture 或 Subsystem 決策，也不使用 `05_architecture.md`、`06_subsystem.md` 作為設計依據。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | URDF + `robot_state_publisher`；Xacro 作為可選的 URDF 維護工具 |
| Exact Version / Platform | ROS 2 Jazzy；Ubuntu 24.04 Noble；`urdf` 2.10.1-2、`robot_state_publisher` 3.3.4-1、`xacro` 2.1.1-1（2026-08-13 Jazzy rosdistro release metadata） |
| Coverage Status | **Fully Covered**（成熟方案能力層級） |
| Covered Scope | 以 URDF 表達 robot model；從 URDF kinematic tree 與 `JointState` 發布 fixed／movable joint transforms；以 Xacro 維護及產生 URDF |
| Known Constraints | URDF/Xacro 只提供格式與工具；機器人的真實尺寸、link、joint、frame、collision、mesh 與 joint state source 仍是專案資料與整合責任 |
| Uncovered Gap | 無 Custom Behavior Gap；存在 Configuration/Data Asset 工作與 Integration Evidence Gap |
| Missing Evidence | 實際部署套件版本尚未 pin；參考 URDF 尚未驗證可安裝、可解析、TF 無斷鏈／重複 owner，亦未驗證四類 downstream consumer |
| MVP Change Candidate | None |

`Fully Covered` 只表示成熟方案已提供 SYS-023 所需的標準表示與發布能力，不表示本專案的 `mobile_base_description` 已完成，也不表示實機整合已驗證。

## 3. Requirement Fragments

| Fragment | Mature coverage | Remaining project evidence |
|---|---|---|
| 提供機器人幾何定義 | URDF 可表示 robot model；visual/collision/inertial 等實際內容由專案模型填入 | 實際尺寸、mesh、collision footprint 與安裝位置正確性 |
| 提供座標系定義 | URDF link/joint kinematic tree 搭配 `robot_state_publisher` 可發布 `/tf_static` 與 `/tf` | frame 命名、樹狀連通性、唯一 TF owner 與實機 mounting transform |
| 提供關節定義 | URDF 定義 fixed/movable joints；`JointState` 驅動 movable-joint transforms | joint type、axis、origin、limits 與 authoritative joint-state source 正確性 |
| 可供感知、定位、建圖與導航使用 | ROS 2 使用 `robot_description` 與 tf2 提供標準模型／transform 機制 | 各 consumer 能在正確時間取得所需 frame，且語意與幾何均正確 |

## 4. Primary-source Evidence

### 4.1 URDF parser and format

- **Evidence Type:** Official exact-version documentation and release metadata
- **Source:** [URDF Jazzy documentation](https://docs.ros.org/en/jazzy/p/urdf/)；[Jazzy rosdistro `urdf` entry](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml#L13289-L13307)
- **Exact Version / Revision:** `urdf` release `2.10.1-2` in current Jazzy rosdistro metadata; the generated Jazzy docs page identifies the documented API series as 2.10.x
- **Target Platform:** ROS 2 Jazzy; release platforms include Ubuntu Noble in the [Jazzy distribution metadata](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml#L4-L10)
- **Observed or Documented Scope:** The official package documentation defines URDF as an XML format representing a robot model and provides its C++ parser.
- **Limitations:** This proves that a mature model format and parser exist. It does not prove that the project model contains correct geometry, frames, joints, collision geometry, or sensor mounting transforms.
- **Access Date:** 2026-08-13

### 4.2 `robot_state_publisher`

- **Evidence Type:** Official Jazzy tutorial, upstream source documentation, and Jazzy release metadata
- **Source:** [ROS 2 Jazzy: Using URDF with robot_state_publisher](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/URDF/Using-URDF-with-Robot-State-Publisher.html)；[`robot_state_publisher` upstream README](https://github.com/ros/robot_state_publisher/blob/jazzy/README.md)；[Jazzy rosdistro entry](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml#L9685-L9700)
- **Exact Version / Revision:** Jazzy branch; release `3.3.4-1` in current Jazzy rosdistro metadata
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** The node consumes a URDF kinematic tree and `sensor_msgs/msg/JointState`, publishes fixed joints to transient-local `/tf_static`, publishes updated movable joints to `/tf`, and republishes the model on `robot_description` in the default mode.
- **Limitations:** It computes transforms from supplied model and joint data. It does not validate physical dimensions, choose system frame semantics, provide actual encoder feedback, establish the mobile base's world pose, or prove downstream integration.
- **Access Date:** 2026-08-13

### 4.3 Xacro

- **Evidence Type:** Official upstream documentation and Jazzy release metadata
- **Source:** [`xacro` upstream README](https://github.com/ros/xacro/blob/ros2/README.md)；[Jazzy rosdistro entry](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml#L13805-L13819)
- **Exact Version / Revision:** `xacro` release `2.1.1-1`; upstream `ros2` branch
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** Xacro is an XML macro language that can generate shorter and more maintainable robot-description XML.
- **Limitations:** Xacro is an authoring/preprocessing tool. It neither publishes TF nor proves that expanded URDF is syntactically valid, physically correct, or compatible with project consumers.
- **Access Date:** 2026-08-13

### 4.4 `joint_state_publisher` is not a mandatory runtime dependency

- **Evidence Type:** Official package documentation and Jazzy release metadata
- **Source:** [`joint_state_publisher` Jazzy API documentation](https://docs.ros.org/en/jazzy/p/joint_state_publisher/modules.html)；[`joint_state_publisher` upstream README](https://github.com/ros/joint_state_publisher/blob/ros2/README.md)；[Jazzy rosdistro entry](https://github.com/ros/rosdistro/blob/master/jazzy/distribution.yaml#L4683-L4701)
- **Exact Version / Revision:** Jazzy release `2.4.3-1` in current rosdistro metadata; upstream `ros2` branch
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** The package can publish values for movable joints described by URDF and can be paired with `robot_state_publisher`, including cases where joints lack encoder data.
- **Limitations:** It does not provide authoritative physical joint feedback. On the real AMR, movable joints with hardware/controller feedback must use the authoritative feedback producer selected later by Architecture. Therefore it is useful for model inspection or explicitly non-authoritative defaults, but is not required merely to satisfy SYS-023.
- **Access Date:** 2026-08-13

### 4.5 Standard launch composition is available

- **Evidence Type:** Official Jazzy package documentation
- **Source:** [`urdf_launch` 0.1.2 Jazzy documentation](https://docs.ros.org/en/jazzy/p/urdf_launch/)
- **Exact Version / Revision:** `urdf_launch` 0.1.2 / Jazzy
- **Target Platform:** ROS 2 Jazzy / Ubuntu 24.04 Noble
- **Observed or Documented Scope:** The package offers standard launch composition that loads a URDF/Xacro model and starts one `robot_state_publisher`; its display flow optionally starts RViz and a joint-state publisher.
- **Limitations:** It is a convenience candidate, not necessary coverage. It does not decide project package layout, model ownership, runtime composition, or whether optional display tools belong in production.
- **Access Date:** 2026-08-13

## 5. Local Read-only Evidence

The user-designated source material exists at:

```text
ref/FIH_AMR_ROBOT_V2.0_0731/
├── urdf/RWF_V2.0_0731.urdf
└── meshes/*.STL and base_link.obj
```

Read-only inspection found:

- one URDF containing 84 links and 83 joints;
- `base_link`, left/right driving-wheel links, `base_imu_link`, and two base LiDAR links;
- fixed joints for the IMU and two LiDAR frames;
- visual, collision, inertial, mesh, joint origin and joint-axis data;
- the future package name `mobile_base_description` is not yet present under `src/` in this workspace snapshot.

These observations only prove that reusable source assets exist. They do **not** prove:

- the file resolves mesh paths after installation into a ROS package;
- Xacro/URDF parsing succeeds on the target image;
- its geometry matches the current physical AMR;
- every link and joint is needed by the mobile-base MVP;
- the TF tree is connected and has no duplicate producer;
- sensor `frame_id` values match the model;
- perception, localization, mapping and navigation can consume it correctly.

No local `check_urdf` or `xacro` executable was available in the current host shell, so no parser/runtime validation is claimed.

## 6. Gap Classification

### Configuration / Data Asset Work

```text
Requirement Fragment: Provide the actual AMR geometry, frame, and joint definitions.
Existing Coverage: URDF/Xacro representation and robot_state_publisher runtime behavior are mature.
Configuration Limitation: Generic packages cannot know project-specific dimensions, frames, joints, meshes, or installation layout.
Composition Limitation: Standard composition still requires one authoritative project model and the correct JointState source.
Minimum Missing Behavior: None; the missing work is project-owned model data, packaging, configuration, and validation.
Required Inputs: Approved physical geometry, frame semantics, joint semantics, sensor mounting transforms, and selected joint-state authorities.
Required Outputs: Installable robot description; robot_description; valid /tf_static and /tf segments required by consumers.
Constraints: Do not introduce duplicate TF producers; do not use joint_state_publisher as fake physical feedback.
Required Verification: Parse/install test, TF structural and semantic checks, model visualization, sensor-frame consistency, downstream integration, and real-hardware dimension/mounting validation.
Architecture Decision Needed: Select the authoritative model owner, runtime publisher composition, TF ownership boundaries, and which movable joints receive authoritative feedback.
```

### Evidence Gap

- Pin and record the exact package versions installed in the target Docker image or deployment environment.
- Validate the converted `mobile_base_description` package on the target ROS 2 Jazzy platform.
- Prove that the exact TF and geometry required by perception, localization, mapping and navigation are available and semantically correct.

## 7. Handoff to 04 Assessment

Recommended 04 conclusion:

- **Coverage Status:** `Fully Covered` at mature-solution capability level.
- **Candidate composition:** URDF + `robot_state_publisher`; Xacro is optional but recommended for maintainability.
- **Custom gap:** `None`.
- **Non-custom gaps:** project model asset/configuration work and integration evidence.
- **Architecture consideration:** 05 must later select the authoritative description owner and TF/joint-state ownership without treating `joint_state_publisher` as real feedback.
- **MVP simplification:** no SYS-023 simplification is justified by mature-package availability.

