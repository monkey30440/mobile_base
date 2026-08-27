> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-034 Manual Movement Control — Reuse Research

## 1. Research Scope

本筆記評估目前定案的 SYS-034：

> 建圖期間，系統應接受使用者提供之手動速度命令以控制 AMR 移動巡覽環境；該移動控制應遵守既有底盤運動控制、運動限制、命令逾時與安全啟停需求。未提供手動速度命令或命令停止時，建圖程序不應因此終止。

評估候選為 ROS 2 Jazzy 官方套件 `teleop_twist_keyboard` 2.4.1-1。

本 requirement 的必要 fragments 包含：

1. **手動速度命令接收**：建圖期間接受使用者透過終端鍵盤操作產生之速度命令。
2. **底盤運動控制對接**：命令對接既有底盤運動控制（SYS-022），依差速輪運動學驅動 AMR 移動。
3. **安全規範服從**：手動移動嚴格遵守底盤運動限制（SYS-028）、命令逾時（SYS-027）與安全啟停（SYS-030），不繞過安全閘門或建立硬體直控旁路。
4. **命令閒置／停止語意**：未輸入命令、命令停止或逾時時，底盤停止，建圖程序（SYS-006）維持運作，不中斷 Mapping session。

下列事項不在 SYS-034 重複判定：

- SYS-001 / SYS-006：Occupancy Grid 建立與持續更新；
- SYS-022：差速輪運動學與速度命令執行；
- SYS-027：運動命令逾時停止政策；
- SYS-028：底盤運動限制與速度/加減速限幅；
- SYS-030：底盤安全啟停與驅動器就緒閘門；
- UC-002 / Navigation Mode 相關之自主路徑規劃與控制。

---

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `teleop_twist_keyboard` |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04 (arm64 Jetson)；Debian package `ros-jazzy-teleop-twist-keyboard` 2.4.1-1noble.20260612.132037（upstream 2.4.1） |
| Coverage Status | **Fully Covered** |
| Covered Scope | 捕捉終端 raw TTY 按鍵輸入，映射為標準 ROS 2 速度命令；原生支援 `stamped` 參數以發布 `geometry_msgs/msg/TwistStamped`（或預設 `Twist`），精確契合下游 controller command contract；支援線速度與角速度步進調整與方向控制；操作員輸入非移動鍵或中斷結束時主動發布零速；按鍵閒置停止發布時由下游 `diff_drive_controller` 原生逾時停止機制（SYS-027）接管保護；速度命令通過既有 S7 安全與限幅鏈（SYS-028／SYS-030）；建圖程序獨立維持（SYS-006） |
| Custom Behavior Gap | `None` |
| Configuration / Composition Gap | 容器內執行時配置 TTY／stdin；依 controller input contract 設定 `stamped:=true` 及 topic remapping（`cmd_vel:=...`）；Mapping Mode 下單一 command producer 無衝突，不需 command mux 或 custom node |
| Missing Evidence | target Jetson/AMR 實機鍵盤操作移動驗證；操作員停止按鍵後主動發布零速與逾時停止之分層驗證；建圖巡覽過程中 Occupancy Grid 持續更新端對端驗證 |
| MVP Change Candidate | `None` |

`Fully Covered` 的理由是成熟套件已直接提供鍵盤手動速度命令生成與標準 Twist / TwistStamped 發布能力，並與既有 `ros2_control` + `diff_drive_controller` 架構完全相容，不需要自製 teleop node、mode manager 或 safety gateway。

---

## 3. Mature Solution Analysis

### 3.1 Input / Output and Interface Compatibility

- **節點與輸入**：`teleop_twist_keyboard` 以 raw TTY 讀取終端鍵盤輸入（`i`, `,`, `j`, `l`, `u`, `o`, `m`, `.`, `k`, `q`, `z`, `w`, `x`, `e`, `c` 等）。
- **輸出介面與下游相容性**：
  - `teleop_twist_keyboard` 2.4.1 宣告有 read-only 參數 `stamped`（bool, default `False`）與 `frame_id`（string, default `""`）。
  - 當 `stamped: false` 時發布 `geometry_msgs/msg/Twist`；當 `stamped: true` 時發布包含目前節點 clock timestamp 與指定 frame_id 之 `geometry_msgs/msg/TwistStamped`。
  - ROS 2 Jazzy `ros2_controllers` 4.42.1 之 `diff_drive_controller` 在非 chained 模式下訂閱 `geometry_msgs/msg/TwistStamped`。
  - 因此，透過傳遞參數 `stamped:=true` 與 topic remapping（`cmd_vel:=/diff_drive_controller/cmd_vel`），成熟套件可直接輸出符合目標控制器契約之速度命令，屬標準 ROS 2 composition / launch configuration，不產生 custom gap。

### 3.2 Stop and Timeout Semantics

系統的手動移動停止與逾時保護具備明確分層：

1. **操作員主動停止（Active Zero Command）**：
   - 當操作員按下非移動按鍵（如 `k` 或空白鍵）時，`teleop_twist_keyboard` 即時計算 `x = y = z = th = 0.0` 並發布零速命令至 `cmd_vel`。
   - 當操作員按下 `CTRL-C` 退出時，節點在 `finally:` 清理區塊主動發布一次零速命令，並復原 terminal settings 後乾淨關閉。
   - 下游 `diff_drive_controller` 收到零速命令後，依配置之減速度限制執行主動煞停。
2. **鍵盤閒置與陳舊命令保護（Stale Command Protection via SYS-027）**：
   - 當操作員停止按鍵（放開鍵盤），`getKey()` 阻塞於標準輸入，節點不再發布新訊息。
   - 下游 `diff_drive_controller` 依據 `SYS-027` 規範之 `cmd_vel_timeout`（非零值），在超過逾時門檻未收到新 timestamp 之有效命令時，自動將 reference velocity 歸零並使底盤煞停。
3. **安全規範服從（SYS-028 / SYS-030）**：
   - `diff_drive_controller` 之 `SpeedLimiter`（SYS-028）強制約束最大速度與加減速度。
   - `M1Hardware` SystemInterface（SYS-030）把關通訊、無警報與驅動器就緒閘門。
   - 手動速度命令完全受制於上述安全鏈，無任何直接控制驅動器的旁路。
4. **建圖狀態維持（SYS-006）**：
   - 建圖節點（`slam_toolbox`）獨立運作，底盤處於停止或無速度命令狀態時維持現有地圖，Mapping session 不會因手動命令停止而終止。

### 3.3 Command Arbitration and Mux Consideration

- 在 UC-001 Mapping Mode 期間，Nav2 自主導航未啟動，不存在其他自主移動命令生產者。
- `teleop_twist_keyboard` 為 Mapping Mode 下唯一的 command source。
- 因此無需引入 `twist_mux` 或自訂仲裁機制，避免不成熟的過早設計（Avoid Premature Structure）。

---

## 4. Exact-version Evidence

- **Debian Package**：`ros-jazzy-teleop-twist-keyboard`
- **Version**：`2.4.1-1noble.20260612.132037`
- **Architecture**：`arm64`
- **Container Baseline**：`Dockerfile` 第 17 行明載 `ros-jazzy-teleop-twist-keyboard`，在目前 Docker 映像檔中已完成安裝並驗證可用。
- **Source Inspection**：`/opt/ros/jazzy/lib/python3.12/site-packages/teleop_twist_keyboard.py` 證實原生支援 `Twist`/`TwistStamped`、`speed`/`turn` 參數、`cmd_vel` 發布與 `finally:` 零速安全清理。
