# mobile_base

## 1. 專案簡介

`mobile_base` 為一個以 ROS 2 為基礎開發的自主移動機器人（Autonomous Mobile Robot, AMR）底盤專案。

本專案採用 V-Model 作為開發流程，以需求驅動設計，以實機驗證作為主要驗證方式，逐步建立一套可追溯、可驗證且可維護的系統。

本文件為專案目前唯一正式文件，後續文件將依需求逐步拆分，避免過度設計與重複維護。

---

## 2. 專案目標

v0.1 目標完成下列三項系統能力（Capability）：

| ID | Capability |
|----|------------|
| CAP-001 | 建立可重複使用之地圖 |
| CAP-002 | 導航至任意指定 Pose |
| CAP-003 | 導航至路網站點 |

完成上述三項能力後，v0.1 即完成開發。

---

## 3. Use Cases

目前 Baseline 僅包含以下三個 Use Case。

| ID | 名稱 | 對應 Capability |
|----|------|-----------------|
| UC-001 | 建圖任務 | CAP-001 |
| UC-002 | 自由空間移動任務 | CAP-002 |
| UC-003 | 路網站點移動任務 | CAP-003 |

除上述內容外，其餘功能皆列入 Backlog，不納入 v0.1。

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
Implementation
    ↓
Hardware Verification
    ↓
Freeze
```

完成 Freeze 後，方可開始下一項功能。

---

## 6. Repository

```text
mobile_base/
├── Dockerfile
├── compose.yaml
├── docs/
│   └── README.md
└── src/
```

Repository 結構依需求自然成長，不預先建立未使用之目錄或檔案。

---

## 7. 目前開發里程碑

| Milestone | 狀態 |
|-----------|------|
| Repository 建立 | ✅ |
| 文件建立 | 進行中 |
| CAP-001 | 未開始 |
| CAP-002 | 未開始 |
| CAP-003 | 未開始 |

---

## 8. 文件管理

本文件採 Living Document 方式維護。

當文件內容逐漸增加且形成明確職責時，再拆分為獨立 Markdown 文件。

正式文件僅保留目前有效且已確認之內容，不保留討論過程或已淘汰方案。

所有需求、設計、實作與驗證皆應具有完整追溯關係。