# mobile_base Documentation

## Purpose

本文件集是 `mobile_base` 文件的入口，涵蓋 Use Cases、Capabilities、Requirements、目前 production Systems／implementation documentation，以及獨立的 Operator Guides。

## V-Model Documentation

閱讀順序：01 Use Cases → 02 Capabilities → 03 Requirements → 04 Systems

- [01 Use Cases](./01_USE_CASES.md) — 使用者意圖與工作流程。
- [02 Capabilities](./02_CAPABILITIES.md) — 系統對外提供的能力。
- [03 Requirements](./03_REQUIREMENTS.md) — 規範性系統需求與追溯關係。
- [04 Systems](./04_SYSTEMS.md) — 目前 production systems 與實作架構。

## Operator Guides

- [Release](../operator/RELEASE.md) — Release image、deployment、startup 與 shutdown 操作。
- [Mapping](../operator/MAPPING.md) — Mapping 操作。
- [Navigation](../operator/NAVIGATION.md) — Navigation 操作。

## Document Responsibilities

- [01 Use Cases](./01_USE_CASES.md)：定義 user intent、actors、preconditions、triggers、main flows、completion 與 observable failure boundaries。
- [02 Capabilities](./02_CAPABILITIES.md)：定義 externally visible system capabilities、inputs、outputs 與 boundaries。
- [03 Requirements](./03_REQUIREMENTS.md)：定義 normative system requirements、constraints、acceptance semantics、UC/CAP traceability 與 Requirement → Implementation Area allocation。
- [04 Systems](./04_SYSTEMS.md)：記錄 current production implementation、Implementation Area responsibilities、interfaces、data and command flows、TF ownership 與 expected normal behavior。
- Operator Guides：提供 Release、Mapping 與 Navigation 的 operational procedures。

## Source of Truth

- **Requirements Authority**：[03 Requirements](./03_REQUIREMENTS.md)。
- **Implementation Authority**：production source、launch files、configuration、URDF/Xacro 與 Behavior Tree files。
- **Operational Procedures**：[Release](../operator/RELEASE.md)、[Mapping](../operator/MAPPING.md) 與 [Navigation](../operator/NAVIGATION.md)。

若描述性文件與 production implementation evidence 衝突，以 implementation evidence 為準，並修正相關文件。
