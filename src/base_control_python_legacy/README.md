# base_control（Python 原型，已停用）

Stage 1／Stage 2 之 Python 實作，2026-08-07 於實機（架高）驗證通過。

依 Mature Solution First 改採 ros2_control 後，本實作由 C++
`hardware_interface` 插件取代（見 `src/base_control`）。

保留為協議行為之對照基準；`COLCON_IGNORE` 使 colcon 略過本目錄。
Stage C 完成並通過實機驗證後刪除。

已驗證之協議事實見
`docs/implementation/SUB-001-base-control-plan.md` § 已驗證之通訊協議。
