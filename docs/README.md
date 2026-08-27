# mobile_base

## 1. 專案簡介

`mobile_base` 為一個以 ROS 2 Jazzy 為基礎開發的自主移動機器人（Autonomous Mobile Robot, AMR）底盤系統專案。

本專案遵守 V-Model、Hardware First、MVP First、Progressive Verification、Document Driven Development、Current Baseline Only、Single Source of Truth、Organic Growth 以及 Avoid Premature Structure 等核心工程原則，以需求驅動設計，以實機驗證作為主要驗證手段，建立可追溯、可驗證且可維護的系統。

本文件為專案文件入口與導航索引（System Entrypoint & Navigation Index），提供系統概觀、已驗證之里程碑狀態與角色導向文件索引。本文件不重複定義細部規格、架構細節、配置參數或驗證數據，各領域規格請依「4. 角色導向文件索引」查閱相應之權威文件。

---

## 2. 專案目標與目前里程碑

### 2.1 系統核心能力 (Capabilities)

v0.1.0 目標完成下列兩項核心系統能力（Capability）：

| ID | Capability | 說明 | 狀態 |
|---|---|---|---|
| **CAP-001** | 建立可重複使用之地圖 | 建立二維 Occupancy Grid 地圖，支援巡覽更新、地圖儲存（Map Package）與重新載入讀回驗證（對應 UC-001）。 | ✅ 實機驗證通過 |
| **CAP-002** | 自主導航至指定目標 | 支援 Station ID 站點與 Goal Pose 位姿導航、Route-assisted 三階段路徑追蹤（First Mile / On Route / Last Mile）、動態障礙物安全避讓與到站停妥判定（對應 UC-002）。 | ✅ 實機驗證通過<br>*(含已知限制)* |

### 2.2 已知限制邊界 (Known Limitation)

- **Station B → Station A 導航進度逾時**：在 `test_site` 場域實機驗證中，Station A 前往 Station B 導航已通過驗收；反向 Station B 前往 Station A 於接近目標時觀察到進度逾時（`error_code=105`，root cause undetermined）。操作注意事項請參閱 [`src/mobile_base_bringup/NAVIGATION.md`](../src/mobile_base_bringup/NAVIGATION.md)。

### 2.3 里程碑狀態總覽

| Milestone | 狀態 | 說明 |
|---|---|---|
| **Repository 與開發環境建立** | ✅ 已完成 | Docker 容器化開發與釋出環境基線就緒 |
| **文件規範與權威模型確立** | ✅ 已完成 | 需求、架構、追溯矩陣與權威模型收斂完成 |
| **CAP-001 實機驗證 (UC-001)** | ✅ 已完成 | 建圖、存檔與 MapIO 回讀驗證通過（IMP-014, IMP-015） |
| **CAP-002 實機驗證 (UC-002)** | ✅ 已完成 | 站點解析、三階段路網導航與安全防護通過（IMP-015, Phase R5） |
| **v0.1.0 MVP Baseline** | ✅ **已結案 (Closed)** | 核心能力具備，底盤具備完整建圖與自主導航能力 |

---

## 3. 系統核心架構概觀

系統劃分為 7 大子系統（S1–S7）：

- **S1 Robot Description**：提供機器人幾何模型、關節拓撲、Footprint 與靜態座標轉換。
- **S2 Perception**：負責雙光達與 IMU 原始感測資料擷取。
- **S3 State Estimation**：結合激光里程計與 IMU 提供平面狀態估測，並唯一發布動態 `odom -> base_footprint` TF。
- **S4 Mapping**：負責佔據網格建圖、地圖儲存與讀回驗證；在建圖模式下發布動態 `map -> odom` TF。
- **S5 Localization**：負責地圖載入與全域定位估測；在導航模式下唯一發布動態 `map -> odom` TF。
- **S6 Navigation**：負責目標解析與驗證、三階段路線輔助導航編排、避障安全防護與到站判定。
- **S7 Base Control**：負責差速驅動控制、馬達通訊、編碼器回授檢核、命令逾時煞停與硬體安全啟停。

系統定義兩種嚴格互斥（Mutually Exclusive）的操作模式：
1. **Mapping Mode (UC-001)**：啟用 S1, S2, S3, S4, S7，由操作員透過手動遙控巡覽建圖；S5 與 S6 嚴格禁止啟動。
2. **Navigation Mode (UC-002)**：啟用 S1, S2, S3, S5, S6, S7，由自主導航堆疊執行路網導航與安全防護；S4 嚴格禁止啟動。

> **架構權威來源**：完整資料流、TF 擁有權契約、命令安全鏈與子系統邊界請參閱 [`docs/05_architecture.md`](./05_architecture.md)。

---

## 4. 角色導向文件索引

為維持單一真相來源（Single Source of Truth），避免規格與參數重複維護，請依角色查閱相應之權威文件：

```text
                                 [docs/README.md]
                      (Root System Overview & Document Index)
                                        │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
  [General / PM]              [Software Engineer]           [Verification Engineer]
  - 01_use_cases.md           - 05_architecture.md          - traceability_matrix.md
  - 02_capabilities.md        - MAPPING.md / NAVIGATION.md  - evidence_index.md
  - 03_requirements.md        - design_baseline/m1_*.md     - tests & raw evidence
  - XX_backlog.md             │                             │
        │                      └──────────────┬──────────────┘
        └─────────────────────────────────────┼──────────────────────────────┐
                                              ▼                              ▼
                                         [Operator]                      [AI Agent]
                                 - MAPPING.md / NAVIGATION.md    - AGENTS.md
                                 - maps/test_site/               - 02_authority_model.md
```

### 4.1 General / PM / 系統工程師
- [`01_use_cases.md`](./01_use_cases.md)：使用者可操作之系統使用案例（UC-001 建圖, UC-002 導航）。
- [`02_capabilities.md`](./02_capabilities.md)：系統對外提供之功能能力定義（CAP-001, CAP-002）。
- [`03_requirements.md`](./03_requirements.md)：規範性系統需求與驗收標準（SYS-001 ~ SYS-034）。
- [`XX_backlog.md`](./XX_backlog.md)：v0.1.0 之後規劃之延續功能與研究項目。

### 4.2 Software Engineer / 軟體工程師
- [`05_architecture.md`](./05_architecture.md)：**系統架構單一權威來源**（子系統責任、資料流、TF 契約、安全攔截鏈）。
- [`design_baseline/m1_driver.md`](./design_baseline/m1_driver.md)：M1 馬達驅動器 Modbus RTU 通訊協定詳細設計基準。
- [`design_baseline/m1_hardware.md`](./design_baseline/m1_hardware.md)：`ros2_control` `SystemInterface` 與 M1Driver 整合設計基準。
- [`src/mobile_base_bringup/MAPPING.md`](../src/mobile_base_bringup/MAPPING.md)：建圖模式啟動、鍵盤遙控操作、地圖儲存與回讀驗證流程。
- [`src/mobile_base_bringup/NAVIGATION.md`](../src/mobile_base_bringup/NAVIGATION.md)：導航模式啟動、初始定位、站點導航 CLI 與安全操作流程。

### 4.3 Verification Engineer / 測試與驗證工程師
- [`verification/traceability_matrix.md`](./verification/traceability_matrix.md)：**系統需求追溯矩陣 (RTM)**（32 項 SYS 需求與原始碼、驗證方法、證據及狀態完整對映）。
- [`verification/evidence_index.md`](./verification/evidence_index.md)：**驗證證據索引與目錄**（分類索引所有 committed 實機測試日誌、遙測 CSV 與階段驗收報告）。

### 4.4 AI Agent / 自動化代理
- [`AGENTS.md`](../AGENTS.md)：儲存庫協作政策、GitNexus 使用規範與變更工作流。
- [`rework/02_authority_model.md`](./rework/02_authority_model.md)：文件權威模型與單一真相原則。

---

## 5. 文件分類與權威狀態

| 文件路徑 | 文件分類 | 權威狀態 | 說明 |
|---|---|---|---|
| [`01_use_cases.md`](./01_use_cases.md) | 需求層 | **ACTIVE / CANONICAL** | 使用案例規範 |
| [`02_capabilities.md`](./02_capabilities.md) | 需求層 | **ACTIVE / CANONICAL** | 系統能力規範 |
| [`03_requirements.md`](./03_requirements.md) | 需求層 | **ACTIVE / CANONICAL** | 規範性系統需求 (SYS-001~034) |
| [`05_architecture.md`](./05_architecture.md) | 架構層 | **ACTIVE / CANONICAL** | 全系統與子系統架構單一權威 |
| [`design_baseline/m1_driver.md`](./design_baseline/m1_driver.md) | 設計層 | **ACTIVE / CANONICAL** | M1 通訊協定設計基準 |
| [`design_baseline/m1_hardware.md`](./design_baseline/m1_hardware.md) | 設計層 | **ACTIVE / CANONICAL** | M1 ros2_control 整合設計基準 |
| [`src/mobile_base_bringup/MAPPING.md`](../src/mobile_base_bringup/MAPPING.md) | 操作層 | **ACTIVE / CANONICAL** | 建圖操作指南 |
| [`src/mobile_base_bringup/NAVIGATION.md`](../src/mobile_base_bringup/NAVIGATION.md) | 操作層 | **ACTIVE / CANONICAL** | 導航操作指南 |
| [`verification/traceability_matrix.md`](./verification/traceability_matrix.md) | 驗證層 | **ACTIVE / CANONICAL** | 需求追溯矩陣 |
| [`verification/evidence_index.md`](./verification/evidence_index.md) | 驗證層 | **ACTIVE / CANONICAL** | 驗證證據索引目錄 |
| [`XX_backlog.md`](./XX_backlog.md) | 規劃層 | **ACTIVE / CANONICAL** | 後續 Backlog 追蹤 |
| [`verification/README.md`](./verification/README.md) | 驗證層 | **SUPERSEDED** | 舊版驗證說明（由 `evidence_index.md` 取代） |
| [`04_reuse_assessment.md`](./04_reuse_assessment.md) | 評估層 | **HISTORICAL** | 成熟方案評估記錄（非現行規格） |
| [`07_implementation.md`](./07_implementation.md) | 過程層 | **HISTORICAL** | 歷史實作過程記錄（非現行規格） |
| `docs/research/*.md` (32 files) | 調研層 | **HISTORICAL** | 早期技術可行性調研筆記 |
| `docs/handoff/*.md` (5 files) | 過程層 | **HISTORICAL** | 開發交接記錄 |
| `docs/*checklist.md` (4 files) | 過程層 | **HISTORICAL** | 歷史階段查核表 |
| `docs/m1_bringup_validation/` | 驗證層 | **HISTORICAL** | 早期馬達 Bringup 記錄 |

---

## 6. 儲存庫結構

```text
mobile_base/
├── AGENTS.md                          # 協作政策與 AI Agent 工作流規範
├── Dockerfile                         # 開發環境容器定義
├── Dockerfile.release                 # 釋出環境容器定義
├── compose.yaml                       # 開發環境 Docker Compose 服務
├── compose.release.yaml               # 釋出環境 Docker Compose 服務
├── maps/                              # 場域地圖與路網資源
│   ├── test_site/                     # 實機測試場域資源 (map, stations, route_graph)
│   └── template/                      # 場域資源範本目錄
├── scripts/                           # 釋出與工具腳本
├── src/                               # ROS 2 套件原始碼與自動化測試
└── docs/                              # 專案規範、架構、設計基準與驗證文件
    ├── README.md                      # 專案文件入口與導航索引 (本文件)
    ├── 01_use_cases.md                # 使用案例規範
    ├── 02_capabilities.md             # 系統能力規範
    ├── 03_requirements.md             # 系統需求規範 (SYS-001~034)
    ├── 05_architecture.md             # 系統架構單一權威
    ├── XX_backlog.md                  # 後續 Backlog 追蹤
    ├── design_baseline/               # M1 通訊與硬體介面詳細設計基準
    ├── verification/                  # 需求追溯矩陣與驗證證據索引目錄
    ├── evidence/                      # 結構化驗證階段報告
    └── rework/                        # 文件收斂計畫與權威模型
```
