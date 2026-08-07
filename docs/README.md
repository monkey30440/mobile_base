# mobile_base

## 1. 專案簡介

`mobile_base` 為一個以 ROS 2 為基礎開發的自主移動機器人（Autonomous Mobile Robot, AMR）底盤專案。

本專案採用 V-Model 作為開發流程，以需求驅動設計，以實機驗證作為主要驗證方式，逐步建立一套可追溯、可驗證且可維護的系統。

本文件為專案入口文件，提供專案目標與文件索引。各層級之正式規格已依職責拆分為獨立文件，見「9. 文件索引」。

---

## 2. 專案目標

v0.1 目標完成下列兩項系統能力（Capability）：

| ID | Capability |
|---|---|
| CAP-001 | 建立可重複使用之地圖 |
| CAP-002 | 自主導航至指定目標 |

完成上述兩項能力後，v0.1 即完成開發。

---

## 3. Use Cases

目前 Baseline 包含以下兩個 Use Case。

| ID | 名稱 | 對應 Capability |
|---|---|---|
| UC-001 | 建立地圖 | CAP-001 |
| UC-002 | 導航至指定目標 | CAP-002 |

移動任務以 AMR 目前定位結果作為起始位置，使用者指定任務目標。

除上述內容外，其餘功能列入 Backlog。

---

## 4. 開發原則

本專案遵守以下原則。

- V-Model
- Hardware First
- MVP First
- Progressive Verification
- Document Driven Development
- Current Baseline Only
- Single Source of Truth
- Organic Growth
- Avoid Premature Structure

---

## 5. 開發流程

所有功能皆依下列流程完成。

```text
Use Case
    ↓
Capability
    ↓
Requirement
    ↓
Architecture
    ↓
Design Baseline
    ↓
Implementation
    ↓
Hardware Verification
    ↓
Feature Freeze
```

- **Design Baseline**：Use Case、Capability、Requirement、Architecture 與 Subsystem 設計已完成確認，作為目前應實作之基準，但尚未實作或驗證。
- **Feature Freeze**：對應功能已完成實作並通過 Hardware Verification，穩定至可視為目前版本基準。

僅完成文件層級設計時，應標示為 Design Baseline；唯有完成實作與實機驗證後，才可標示為 Feature Freeze。

完成 Feature Freeze 後，方可開始下一項功能。

---

## 6. Repository

```text
mobile_base/
├── Dockerfile
├── compose.yaml
├── docs/
│   ├── README.md
│   ├── 01_use_cases.md
│   ├── 02_capabilities.md
│   ├── 03_requirements.md
│   ├── 04_architecture.md
│   ├── 05_subsystem.md
│   └── 06_backlog.md
└── maps/
    └── template/
        ├── map.pgm
        ├── map.yaml
        ├── route_graph.geojson
        └── stations.yaml
```

Repository 結構依需求自然成長，不預先建立未使用之目錄或檔案。

`maps/template/` 為 Map Package 目錄結構範本，供建立新場域地圖時參考，非實際場域資料。

---

## 7. 目前開發里程碑

| Milestone | 狀態 |
|-----------|------|
| Repository 建立 | ✅ |
| 文件建立 | 進行中 |
| CAP-001 | 未開始 |
| CAP-002 | 未開始 |

---

## 8. 文件管理

本文件採 Living Document 方式維護。

當文件內容逐漸增加且形成明確職責時，再拆分為獨立 Markdown 文件。

正式文件僅保留目前有效且已確認之內容，不保留討論過程或已淘汰方案。

所有需求、設計、實作與驗證皆應具有完整追溯關係。

---

## 9. 文件索引

| 文件 | 內容 |
|---|---|
| [`01_use_cases.md`](./01_use_cases.md) | Use Case 定義（使用者可操作之系統功能） |
| [`02_capabilities.md`](./02_capabilities.md) | Capability 定義（系統對外提供之能力） |
| [`03_requirements.md`](./03_requirements.md) | System Requirement 定義與 UC/CAP 追溯表 |
| [`04_architecture.md`](./04_architecture.md) | 軟體架構、資料流與子系統責任劃分 |
| [`05_subsystem.md`](./05_subsystem.md) | 各子系統之目的、邊界、介面、參數與驗證項目 |
| [`06_backlog.md`](./06_backlog.md) | 未納入目前版本之功能與研究議題 |

本文件（`README.md`）僅作為專案入口，不重複上述文件之內容；各文件為其對應主題之 Single Source of Truth。