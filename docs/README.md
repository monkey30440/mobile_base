# mobile_base Documentation

## 1. 目的 (Purpose)

本文件集說明 `mobile_base` 自主移動機器人（AMR）之現行系統定義與設計原理，回答讀者：「現在這台 AMR 是什麼，以及為什麼這樣設計」。

文件內容涵蓋系統用途、對外能力、規範性需求、系統層級與子系統架構、核心設計決策依據，以及目前已驗證之運作狀態與已知限制。

---

## 2. 閱讀順序 (Reading Order)

本文件集依循 V-Model 系統工程由外而內、由抽象至具體的脈絡編排，建議依下列順序閱讀：

1. [`01_USE_CASES.md`](./01_USE_CASES.md) — 說明使用者視角的操作使用案例與工作流程。
2. [`02_CAPABILITIES.md`](./02_CAPABILITIES.md) — 說明系統對外提供的核心功能與能力定義。
3. [`03_REQUIREMENTS.md`](./03_REQUIREMENTS.md) — 說明系統必須滿足的規範性功能需求、安全需求與驗收邊界。
4. [`04_SYSTEMS.md`](./04_SYSTEMS.md) — 說明全系統與子系統架構、資料流、TF 契約、設計決策依據以及實機驗證狀態。

---

## 3. 文件職責 (Document Responsibilities)

- **`README.md`**：文件集單一入口與導航索引。
- **[`01_USE_CASES.md`](./01_USE_CASES.md)**：回答這台 AMR 用於什麼情境（建圖與自主導航工作流）。
- **[`02_CAPABILITIES.md`](./02_CAPABILITIES.md)**：回答這台 AMR 具備哪些對外能力（地圖建立與指定目標導航）。
- **[`03_REQUIREMENTS.md`](./03_REQUIREMENTS.md)**：回答系統必須滿足哪些可觀察規範與約束（SYS-001 ~ SYS-034）。
- **[`04_SYSTEMS.md`](./04_SYSTEMS.md)**：回答現行 AMR 是什麼、各子系統如何協同運作、為何採取當前架構設計，以及目前實機已驗證結論與已知限制。

---

## 4. 單一真相來源原則 (Source of Truth)

為維持系統規格一致性與避免重複維護，各領域定義之權威來源如下：

- **需求權威 (Requirements Authority)**：[`docs/03_REQUIREMENTS.md`](./03_REQUIREMENTS.md) 為系統規範性需求之單一權威來源。
- **架構與驗證權威 (Architecture & Verification Authority)**：[`docs/04_SYSTEMS.md`](./04_SYSTEMS.md) 為系統架構、子系統責任、動態 TF 擁有權契約、設計決策依據與實機驗證狀態之單一權威來源。
- **實機操作指南 (Operational Procedures)**：[`src/mobile_base_bringup/MAPPING.md`](../src/mobile_base_bringup/MAPPING.md) 與 [`src/mobile_base_bringup/NAVIGATION.md`](../src/mobile_base_bringup/NAVIGATION.md) 為建圖與導航之實機操作流程權威。
- **實作權威 (Implementation Authority)**：生產程式碼（`src/`）、Launch 檔、參數配置 YAML、URDF/Xacro 與 Behavior Tree 檔為執行期實作之最終權威。

> **衝突判定規則**：若描述性文件與生產實作或實機驗證證據發生衝突，應以實作與實機驗證證據為準，並及時修正文件。
