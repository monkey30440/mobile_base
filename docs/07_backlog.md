# Backlog

本文件記錄未納入目前版本之功能、改善項目與研究議題。

---

## Documentation

### Architecture Refactoring

完成 UC-001、UC-002 後，評估調整文件結構。

```text
architecture.md
├── Overall System Architecture
├── Common Architecture
├── UC-001 Runtime Flow
└── UC-002 Runtime Flow
```

Status

- Backlog

---

## Simulation

### Isaac Sim

建立 Isaac Sim 模擬環境。

內容包含：

- Robot Import
- Sensor Simulation
- SLAM
- Navigation
- Validation

Status

- Backlog

---

## Observability

### Monitoring Platform

建立系統監控平台。

內容包含：

- Foxglove
- Fluent Bit
- InfluxDB
- OpenSearch
- Dashboard

Status

- Backlog

---

## Real-Time Motion and Odometry

### Real-Time Base Motion Control

底盤運動控制確定性與低延遲硬實時（Hard Real-Time）改造。

內容包含：

- **PREEMPT_RT Kernel & Thread Priority**：引入 Linux PREEMPT_RT 核心，設定 `ros2_control` 控制迴路執行緒為 `SCHED_FIFO` / `SCHED_RR` 即時優先級與專屬 CPU Core Affinity（CPU 隔離）。
- **Deterministic Control Loop**：固定 100 Hz（$10\text{ ms} \pm 0.5\text{ ms}$）確定性控制週期，迴路內鎖定記憶體（`mlockall`）並嚴禁動態記憶體配置（`malloc`/`free`）。
- **Low-latency Motor Bus**：馬達通訊匯流排（SocketCAN / CANopen / EtherCAT）最壞情況執行時間（WCET）約束 $< 2\text{ ms}$。
- **Real-Time Safety Stop**：急停或命令逾時（`cmd_vel_timeout`）觸發至馬達停止輸出的物理反應時間 $< 20\text{ ms}$。

Status

- Backlog

---

### Real-Time Odometry & State Estimation

里程計與感知狀態估測軟實時（Soft Real-Time）改造。

內容包含：

- **High-rate Wheel Odometry**：100 Hz+ 高頻確定性輪圈編碼器讀取與輪式里程計計算，避免時序抖動與量測滯後。
- **Low-jitter Sensor Timestamping**：IMU 高頻取樣（200 Hz+）與硬體時間戳記對齊（PTP / Hardware Timestamping）。
- **Lock-free Sensor Buffering**：狀態估測（`robot_localization` / EKF）採用無鎖佇列（Lock-free Buffer）與 Deadline QoS 保證資料管線即時性。
- **Deterministic TF Publication**：高頻發布 `odom -> base_footprint` TF 座標轉換，消除導航 Costmap 座標同步抖動。

Status

- Backlog

---

## Performance Optimization

完成 v0.1 功能驗證後進行系統效能最佳化。

內容包含：

- Control Loop Latency
- Scheduler Latency
- Thread Priority
- CPU Affinity
- DDS QoS Tuning
- PREEMPT_RT Evaluation
- `cyclictest` 核心與中斷延遲基準測試

Status

- Backlog

---


## Future Features

### Fleet Management

- Multi-AMR
- Dispatcher
- Task Allocation

Status

- Backlog

---

### Auto Charging

- Battery Monitor
- Charging Task
- Docking

Status

- Backlog

---

### Elevator Integration

- Elevator Control
- Floor Transition

Status

- Backlog

---

### Dynamic Obstacle Avoidance

- Dynamic Obstacle Detection
- Dynamic Replanning

Status

- Backlog

---

### OTA

- Remote Update
- Version Management

Status

- Backlog

---

### CI/CD

- Build Pipeline
- Test Pipeline
- Deployment Pipeline

Status

- Backlog