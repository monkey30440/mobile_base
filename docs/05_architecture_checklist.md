# 05 Architecture Refactoring Checklist

本清單只用於追蹤 `05_architecture.md` 的討論與重構進度，不是 normative input，也不作為架構設計依據。

## Progress

- 總議題：23
- 已完成：23
- 待討論：0
- 目前進度：23 / 23

狀態定義：

- `[x]` 已完成：內容已討論、取得確認並寫入 `05_architecture.md`。
- `[ ]` 待討論：尚未取得設計結論，不得預先寫入 05。
- `討論中`：一次只能有一個議題使用此狀態。
- `延後`：已明確決定不在目前階段處理。

## A. System Decomposition and Responsibility Allocation

- [x] 1. Drive Hardware Interface
  - 完成條件：定義 Drive Hardware lifecycle、feedback、fault 與唯一 hardware ownership。
- [x] 2. Motion Control
  - 完成條件：定義 motion-command ownership、command arbitration、wheel odometry 與 safe-stop responsibility。
- [x] 3. State Estimation
  - 完成條件：定義 system planar odometry、validity 與 `odom → base_footprint` ownership。
- [x] 4. LiDAR Perception
  - 完成條件：定義各 LiDAR source ownership、validity，以及非必要不融合、merge algorithm 未定的限制。
- [x] 5. IMU Perception
  - 完成條件：定義 IMU measurement、validity、calibration state 與 frame semantics。
- [x] 6. Mapping
  - 完成條件：定義 Mapping Mode、teleoperation input、Occupancy Grid output 與 map result boundary。
- [x] 7. Navigation Resource Management
  - 完成條件：定義 Map Package、Route Graph、Station Catalog 的 atomic selection、readiness 與 failure boundary。
- [x] 8. Navigation Target Resolution
  - 完成條件：將 Station ID 與 Absolute Goal Pose 正規化為 Canonical Goal Pose，並排除 Relative Pose v0.1 scope。
- [x] 9. Map Localization
  - 完成條件：定義 initial pose provision、current map pose、localization validity、`map → odom` ownership 與 localization-loss responsibility chain。
- [x] 10. Navigation overall responsibility boundary
  - 完成條件：定義 Navigation 的輸入、輸出、唯一 execution ownership，以及與 Target Resolution、Localization、Resource Management、Motion Control 的邊界。
- [x] 11. First Mile movement strategy
  - 完成條件：定義 current pose 到 usable route entry 的選擇、成功與失敗語意。
- [x] 12. On Route movement strategy
  - 完成條件：定義 Route Graph 上的 route selection、execution、reselection 與 blocked semantics。
- [x] 13. Last Mile movement strategy
  - 完成條件：定義 route exit 到 Canonical Goal Pose 的銜接、完成與失敗語意。
- [x] 14. Free-space Fallback
  - 完成條件：保留已核准的 fallback eligibility，禁止把 resource/configuration failure 當成 fallback，並明確定義 v0.1 不執行 fallback movement。

## B. Operational Flows and Cross-subsystem Contracts

- [x] 15. Teleoperation and autonomous command authority
  - 完成條件：確認 mapping teleoperation 與 autonomous navigation 的 command authority、互斥與撤銷規則。
- [x] 16. Operating modes and subsystem lifecycle
  - 完成條件：定義 Mapping Mode、Navigation Mode 的啟用條件（包含需要時提供 initial pose 並等待 localization valid）、互斥資源與 mode transition responsibility。
- [x] 17. Mapping operational flow
  - 完成條件：從啟動、teleoperation、感測與估測，到 Map Package 產出的跨 subsystem 流程閉合。
- [x] 18. Navigation operational flow
  - 完成條件：從 terminal target、resource validation、localization、三階段移動，到 navigation result 的流程閉合。
- [x] 19. Failure and safe-stop flow
  - 完成條件：定義 target、resource、localization、planning、control、hardware failure 的 owner、傳遞與停止責任。
- [x] 20. System-wide architectural contracts
  - 完成條件：集中確認 command、TF、resource identity、validity、status/result 與 safety contracts 無矛盾或重複 owner。

## C. Final Architecture Audit

- [x] 21. Requirements allocation completeness
  - 完成條件：逐項確認 `01_use_cases.md`、`02_capabilities.md`、`03_requirements.md` 的 normative intent 均在 05 有明確 allocation 或 contract。
- [x] 22. Internal-design leakage audit
  - 完成條件：只用 `06_subsystem.md` 辨識目前設計意圖與過度深入內容，移除 05 中單一 subsystem 的 internal design，不引用 06 作為設計依據。
- [x] 23. Final consistency review
  - 完成條件：確認 decomposition、responsibility allocation、cross-subsystem relationships、operational flows 與 system-wide contracts 完整且一致。

## Deferred Decisions

- LaserScan merge algorithm：未定；只有證據顯示 consumer 必須使用融合輸入時才討論。
- Free-space Fallback implementation：v0.1 不實作；保留 eligibility 與 architecture extension boundary。
- Relative navigation target：不屬於 v0.1；若要納入，須先建立上游 requirement。
- Dynamic resource switching、resource versioning、checksum、rollback、remote deployment 與 resource database：不屬於 v0.1。
- Automatic localization、fixed startup pose 與 last-pose persistence：不屬於 v0.1；v0.1 在需要時由使用者人工提供 approximate initial pose。
- Physical E-stop：已知 AMR 配備且實體停止功能正常；不據此宣稱 STO、software feedback integration 或 safety certification 已完成驗證。
