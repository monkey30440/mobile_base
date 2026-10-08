# V1 開發容器

範圍為 #47 的 development/build/test；不啟動機器人功能。V1 target 仍為 AGX Orin。採用使用者指定的 NVIDIA Isaac ROS image，Dockerfile 以觀測 digest 固定 base；後續 apt 套件解析不保證跨時間完全相同，實際清單保存在 `/opt/mobile-base-packages.tsv`。

## Host 前提與操作

需要 Linux ARM64、Docker daemon 與 Compose plugin。帳號須有經管理者授權的 daemon 存取權；Docker group 等同高度 host 權限。不要 chmod socket。本機普通帳號目前 permission denied，以下命令在有權限的 shell 執行；需 sudo 時保留下面 export 的環境設定。若使用 sudo，可用 `sudo --preserve-env=LOCAL_UID,LOCAL_GID docker compose ...`（須符合管理者 sudo policy），或把這兩個數值寫入 git-ignored `.env`。此 ticket 沒有修改 host 帳號、groups 或 daemon。

```bash
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
docker compose config --quiet
docker compose build mobile_base
docker compose up -d mobile_base
docker compose exec mobile_base bash
# 也可直接執行非互動 shell：
docker compose exec -T mobile_base bash -c 'ros2 pkg list'
docker compose down
```

預設 UID/GID=1000；不同帳號須在 build 與 up 時一致設定，變更後重新 build。工作目錄 `/workspace` bind mount repository，build/install/log、maps 與其他 workspace 產物留在 host。HOME 為容器內 `/home/mobile_base`，此目錄不是持久資料存放處。容器以對應 UID/GID 執行，不重設 host 目錄 ownership。

互動 bash 與 `bash -c` 都接入 Jazzy 與存在時的 workspace overlay。沒有自訂 entrypoint；直接執行 ROS 命令（例如 `docker compose exec mobile_base ros2 ...`）不經 bash sourcing，請使用上面的 `bash -c`。新 build 完成後開新 shell，或手動 source install/setup.bash。沒有 production package 時 colcon 成功不代表測試通過。

```bash
# workspace 有 package 後：
docker compose exec -T mobile_base bash -c 'colcon list && colcon build --symlink-install'
docker compose exec -T mobile_base bash -c 'colcon test && colcon test-result --verbose'
```

`reference/` 只供閱讀；其中 IMU 有 COLCON_IGNORE。新增 package 前再次確認 `colcon list`，不得誤編譯 reference。Docker build context 只包含 Dockerfile，不傳送 reference、credentials 或 workspace outputs。

## ROS smoke check

先確認 ROS CLI 與原生套件可使用：

```bash
docker compose exec -T mobile_base bash -c 'ros2 pkg prefix robot_state_publisher'
docker compose exec -T mobile_base bash -c 'ros2 pkg executables nav2_route'
```

先前 talker/listener 驗證使用 demo_nodes_cpp；目前精簡 image 不安裝該套件，需要重做 pub/sub smoke test 時，在臨時驗證 image 安裝。

測試後執行 `docker compose down`，確認不殘留此開發容器。

## 網路與 USB

Linux host networking 讓 ROS discovery 與 Ethernet LiDAR 共用 host 網路。沒有 port mapping。可設定 ROS_DOMAIN_ID（0 預設）；ROS_AUTOMATIC_DISCOVERY_RANGE 預設 SUBNET。軟體 pub/sub 成功不驗證 LiDAR IP、NIC、防火牆、multicast 跨機或硬體封包；留 #37。

USB 預設不掛入。取得實際穩定 `/dev/serial/by-id/...` 路徑、以 `stat -Lc '%g' <path>` 確認 group 後，在不提交的 `compose.local.yaml` 加入：

```yaml
services:
  mobile_base:
    devices:
      - /dev/serial/by-id/ACTUAL_MOTOR_ID:/dev/mobile_base_motor
      - /dev/serial/by-id/ACTUAL_IMU_ID:/dev/mobile_base_imu
    group_add:
      - "ACTUAL_DEVICE_GROUP_GID"
```

以 `docker compose -f compose.yaml -f compose.local.yaml up -d mobile_base` 使用，同組裝方式 down。依實際裝置填入，未接 USB 時不要套用；Compose 對缺失 device 應報錯。driver 使用容器內對應路徑。熱插拔後可能需要重新建立容器。不要使用 privileged 或掛入全部 `/dev`。通訊與重新接線驗證留 #35／#36。

## 可選 GUI

Headless 模式不需要 DISPLAY、Xauthority、GPU 或 NVIDIA runtime。RViz/rqt 已安裝。GUI 需要 host 可用 X11/XWayland DISPLAY 與經授權、容器 UID 可讀的 Xauthority cookie 檔案；使用者先確認實際來源（例如 `xauth info`），不要用 blanket `xhost +`。

在同一 local override 加入下列設定，將 cookie 路徑換成實際檔案：

```yaml
services:
  mobile_base:
    environment:
      DISPLAY: ${DISPLAY:?Host DISPLAY required}
      XAUTHORITY: /tmp/mobile-base.xauthority
      QT_X11_NO_MITSHM: "1"
      LIBGL_ALWAYS_SOFTWARE: "1"
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:ro
      - /absolute/path/to/authorized-cookie:/tmp/mobile-base.xauthority:ro
```

啟動後執行 `docker compose -f compose.yaml -f compose.local.yaml exec mobile_base bash -c rviz2`（rqt_console 同理）。預設先用 software OpenGL；本輪未驗證可見 GUI。若 target 實測需要 NVIDIA graphics，先核對 host BSP、driver 與 Container Toolkit 相容性，再於 local override 選 `runtime: nvidia` 並設定 `NVIDIA_VISIBLE_DEVICES: all`、`NVIDIA_DRIVER_CAPABILITIES: graphics,display,utility`。這是待驗證入口，不宣稱選定 image 已與 Orin／Thor GPU 相容。不要為 headless 開發強制 GPU。

## 驗證紀錄

見 [ticket #47](https://github.com/monkey30440/mobile_base/issues/47) 的 resolution 與 [環境驗證紀錄](container-validation.md)。未完成的 Orin BSP／GPU／GUI／USB／LiDAR 驗證留在後續 target/裝置 tickets，不代表 robot Bringup ready。

## Mapping 原生倒裝修正（#39）

原生 `slam_toolbox 2.8.5` 對倒裝且非對稱 scan 只反轉 ranges，未反轉
angle bounds。本平台實測會造成約 23.742° 的 scan/map 旋轉偏差；
Operator 採用固定官方 source 的最小 metadata 修正。
Docker 的 slam_builder 使用官方 commit
`ec8f7635dea317b531c419f798f87d90a336f32e` 與
`docker/patches/slam-toolbox-inverted-bounds.patch`，安裝至
`/opt/mobile_base/slam_toolbox`；正式 executable 由此 overlay 提供，
apt 套件保留作依賴／基線。版本及 patch hash 在該目录的 source-version.txt。
source sparse checkout 略過不參與編譯的 images，保留實際建置／安裝輸入。

這不修改 scan topics／frames、真實 URDF、FOV、SLAM／TF ownership，
也不新增 scan relay、融合或存圖 wrapper。軟體及真實地圖品質分開驗收；
將來 upstream 修正後，需重做適用驗證再移除此 overlay。
研究與驗證見 [Mapping research](../research/mapping-native-20261008.md) 及
[Mapping validation](../validation/mapping-package-20261008.md)。

## LaserScan 距離範圍 metadata 修正（#39）

同一固定 SICK 3.9.0 source overlay 加入
`docker/patches/sick-scan-xd-range-bounds.patch`。上游的 segment publisher
使用當幀最近／最遠量測填入 range_min/max；SLAM 快取首幀 bounds 後，
可能排除後續仍在感測器能力內的有效點。
修正版提供 `laserscan_range_min/max`，0/0 預設保留上游行為；平台
lidar.yaml 根據兩台已讀回 OrdNum=1134608 的 Core-1，明定 0.05／25 m。
只修正 metadata，不修改 ranges、角度、frame、時間戳或點雲。
這兩個參數屬於本專案的最小 source 補足，**不是 apt 原生版既有參數**。
版本與兩份 SICK patch hash 都寫入 source-version.txt；因此必須重新
build image 並 recreate container，僅重建 workspace 不會更新 driver。
