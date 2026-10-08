# #38：mobile_base_odometry 套件搬移

Operator 同意先新增 Odometry 套件，再做架高／落地驗證。
基準 `1597507`；review 使用已指定 `f447874`，涵蓋此前已 review 的起始配置交付及本輪搬移。
平台 AGX Thor、Jazzy，映像 `566d8ff74d6b`、Fast DDS。

## 改動與 ownership

`local_estimation.launch.py`、`config/ekf.yaml`、公開 ROS 測試由 Bringup 搬至
`mobile_base_odometry`。對舊 commit 執行逐 byte 比對，launch／YAML 完全相同。
公開測試只更換套件定位與 launch target，原行為 assertions 保留。
Bringup 移除舊入口、配置安裝與只屬於該測試／runtime 的依賴；不保留重複配置。

Odometry 只提供 native robot_localization 配置；Control／Perception／Description
各自保留輪端、IMU、單一 RSP ownership。沒有新增融合、TF engine、命令 publisher
或完整產品 Bringup。保留 explicit filter_config、topic／frame、commissioning uncertainty
及 `3600 秒／0.50／0.50`。新套件 README 為繁中。

## 軟體／安装驗證

新入口測試先 RED（Package not found），建置套件後兩項 GREEN。
新入口 `--show-args` 顯示必填 filter_config；舊 Bringup 入口 file not found，確認沒有重複入口。
搬移後首次 Bringup build 因舊 symlink cache 指向已移走檔案失敗；只清除該套件
build/install 產物再建置，成功。這是 migration cache，不修改程式繞過建置。

完整 suite 採 `--executor sequential`：79 tests，0 errors、0 failures、0 skipped。
所有五個套件通過，沒有跨套件合成 topic 污染。

## 使用新入口的靜止實機資料鏈

Description、Control、IMU 分別啟動，EKF 使用新套件 installed YAML。
11 筆零速度初始化，未送非零速度，publisher 隨後移除。
15 秒 wheel300／IMU2586／filtered300；有限值、quaternion、frame、模型輪／感測器 TF
通過。Controller odom TF disabled；停 EKF 後 odom edge 停止，RSP 模型 TF 留存。
最後 native M1 inactive，獨立 FC03 讀回兩輪 inhibited／alarm0／目前與目標 RPM0。

原生 controller_manager pal_statistics 停止時仍有已知 invalid-context ERROR，
程序 finished cleanly、停用及獨立讀回通過，不宣稱日誌沒有 ERROR。

本紀錄只支持 package ownership 搬移與靜止資料鏈；新入口的有人觀察架高／落地
動態驗收尚未進行，不關閉 #38，不宣稱 covariance／bias／定位精度已標定。

## Review／原始 evidence

Standards 0 findings；Spec 0 findings。
[新套件靜止 raw events／TF／logs、實際配置、最後讀回、建置與完整測試](artifacts/odometry-package-20261008.tar.gz)

SHA256：`f8b256f30f0814f1b7f67522ae96dbb632adcbfc35b80d1abafa7b7a405114df`。
