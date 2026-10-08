# LiDAR／launch SIGINT 停止驗證 — 2026-10-08

[#51](https://github.com/monkey30440/mobile_base/issues/51) 完成已重現的兩個停止根因修正。
Runtime commit `772002c`；review baseline 為 Operator 指定的 `748393c`。
研究與 upstream gap 見 [research](../research/lidar-middleware-shutdown-20261008.md)。
本輪只啟動實體 LiDAR，不啟動 Control、不 Servo ON。

## 根因與最小修正

1. **CONFIRMED：launch event consumer 遺失。** 不使用 LiDAR／DDS 的兩個 Python child
   自然重現第59輪 timeout；`KeyboardInterrupt` 發生在 asyncio `call_soon`，
   Shutdown 已入 queue，但 consumer 不再處理。排程邊界 regression 原版 timeout，
   修正版 clean exit。只在 LaunchService.run 暫時抑制同步 default SIGINT handler，
   保留原生 async signal manager；finally 還原，既有 custom handler 不變。
2. **CONFIRMED：SICK 初始化遭中止時 null receiver。** launch-only 修正的原始壓力測試
   426 cases 後仍 SIGSEGV。自然 GDB 第49輪與 deterministic initialization seam
   都定位 `MsgPackThreads::runThreadCb` 的 `udp_receiver->Fifo()`；seam 明確 x25=0。
   shutdown flag 可跳過 receiver 建立，後續卻繼續使用它。最小 null guard 在 UDP init
   之後、IMU/converter 配置之前退出既有 loop，保留正常資料與 cleanup 路徑。

兩項都先保存 RED，再加入 regression／修正。沒有用延長 timeout、kill fallback、
替換 RMW 或額外 shutdown supervisor 作為正常停止方案。

## Artifact／binary provenance

驗證及正式 `mobile_base` image：
`sha256:88e57e07e392898716a2241be80e328e84c84ff627412fc2e9a313ed5aeeb076`。

- SICK 3.9.0，commit `a562c5d098de21f6284359f4dfea97e93bd2b4d5`。
- launch 原始 source SHA256 `7d587a8269131ae9b2e950460a52c87e95fd4bce083faa1fcc1f76bf8468a756`；
  patched source `e4ab2ca650a9625374543530621d73079474c851bd944faf8bf4166f4ba91206`。
- Fast DDS 2.14.6／rclcpp 28.1.16／rmw_fastrtps_cpp 8.4.4 保持原 binary。
  隔離環境只升 Fast DDS 2.14.7，再升 rclcpp 28.1.22 都仍能重現失敗，沒有部署升級。
- Docker build 對固定 source／patch 做檢查並保存 provenance；正式 image 不包含 GDB。
  AArch64 native seam 使用隔離測試容器的 GDB，未新增 runtime debugging dependency。

## Software-only 驗證

| 驗證 | 結果 |
| --- | --- |
| default/custom SIGINT handler 與 receiver init regression | 3 passed，1.80 秒 |
| 原始 passive 雙 driver parent-only SIGINT probe | 200 輪 × 3 = 600 cases，全部 passed |
| 完整 `pytest src docker/test` | 最後一輪 99 passed，204.29 秒，0 skipped |
| 原生 M1 protocol C++ tests | 4 passed |
| 正式容器重建後 launch regressions＋原始三次雙 driver probe | 5 passed，2.20 秒 |

壓力測試未改原有 ports、domains、等待條件或10秒正常退出上限；沒有 prototype
PYTHONPATH／instrumentation。實體硬體與 software-only evidence 分開。

完整 Python 測試首輪為98 passed／1 failed：無效 `map.pgm` 已被 native map server
拒絕，但 change_state response 發送 timeout，client 12秒未收到回覆。
該項在三個獨立 pytest processes 通過，未改 runtime／測試；之後完整99項通過。
首輪與單獨重跑證據均保留。**UNRESOLVED：該 service response timeout 的根因**，
不將重跑成功當因果證明，也不把本次停止修正宣稱解決所有 DDS 問題。
#50 已有同類原生 service timeout 記錄；本次未擴張到 Nav2 service hardening。

## 實體雙 LiDAR

在同一候選 artifact、host Ethernet `192.168.0.51`，使用公開入口：

```bash
ros2 launch mobile_base_perception dual_picoscan.launch.py
```

前左 `.52`／右後 `.53`，三次啟動，每輪至少20筆 startup 後再觀察30秒；
只 SIGINT launch parent，驗證兩個 native children clean exit，再重新 launch。

| 輪次 | FL Hz | BR Hz | 正常停止秒數 |
| --- | ---: | ---: | ---: |
| 1 | 24.9996 | 24.9996 | 0.2676 |
| 2 | 25.0293 | 24.9960 | 0.2674 |
| 3 | 25.0253 | 24.9920 | 0.2167 |

三輪均維持 `base_lidar_link_FL_1`／`base_lidar_link_BR_1`；
沒有空 scan、重複／倒退 timestamp、process crash 或 shutdown timeout。
最大接收間隔0.04515秒。這是 node 停止／重啟，不是 LiDAR 電源循環、量產耐久或所有
SICK scanner families 的驗證；既有模型／TF／安裝方向不變。

## Standards

平行 review：0 actionable findings。固定來源、native ownership、handler 還原與
最小 receiver guard 符合已確認責任；沒有新增 project-owned runtime supervisor。

## Spec

平行 review：0 actionable findings。修正符合 #51；上述 pressure、完整回歸、
實體收訊／停止／重啟與部署後驗證已完成。

Totals：Standards 0；Spec 0；兩軸均無阻擋 finding。

## Evidence 與收尾

[證據 archive](artifacts/lidar-launch-shutdown-20261008.tar.gz)，SHA256：
`dd996a55e1078db72681f1901b45cdde77a64ac5ba2f0bb4dc7fc739b6620e90`。
包含自然 RED、GDB、首次失敗、600 cases logs、完整回歸、硬體 JSON／logs、
provenance、review 與可重跑的測試腳本；access credential log lines 已遮蔽。

已將候選 image 套用正式 Compose、重建 `mobile_base`，移除三個本輪測試容器。
全部 LiDAR nodes 已正常停止，未啟動馬達。#51 不代表所有 upstream lifecycle races
已排除；已確認的兩個根因與本輪驗收完成，可回到 #41 原計畫。
