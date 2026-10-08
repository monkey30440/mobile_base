# 基礎環境：指定 Isaac ROS image 與確切內容。
FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack@sha256:e5a7ecfaea177c602a43937c932672dd354ed8bf3acc11e29ca7c5ebc6a891d6 AS ros_base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 使用 HTTPS 存取 Jetson repository，再安裝開發與 V1 原生套件。
RUN sed -i 's|http://repo.download.nvidia.com/|https://repo.download.nvidia.com/|g' \
    /etc/apt/sources.list.d/nvidia-jetson-apt-source.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    iputils-ping \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pytest \
    python3-vcstool \
    python3-serial \
    libmodbus-dev \
    ros-jazzy-fastcdr \
    ros-jazzy-fastrtps \
    ros-jazzy-rmw-fastrtps-cpp \
    ros-jazzy-rmw-fastrtps-shared-cpp \
    ros-jazzy-foxglove-bridge \
    ros-jazzy-diagnostic-updater \
    ros-jazzy-diagnostic-aggregator \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    ros-jazzy-xacro \
    ros-jazzy-sick-scan-xd \
    ros-jazzy-ament-cmake-gtest \
    ros-jazzy-launch-testing-ament-cmake \
    ros-jazzy-robot-localization \
    ros-jazzy-slam-toolbox \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-route \
    ros-jazzy-teleop-twist-keyboard \
    ros-jazzy-rviz2 \
    ros-jazzy-rqt-console \
    ros-jazzy-rqt-robot-monitor \
    && dpkg-query -W > /opt/mobile-base-packages.tsv \
    && rm -rf /var/lib/apt/lists/*

# 下載與修正建置分開快取；final image 只保留安裝產物。
FROM ros_base AS sick_builder
RUN git clone --depth 1 --branch 3.9.0 https://github.com/SICKAG/sick_scan_xd.git /tmp/sick-source \
    && test "$(git -C /tmp/sick-source rev-parse HEAD)" = a562c5d098de21f6284359f4dfea97e93bd2b4d5

# 原生 ROS 2 deferred signal handling，加上明確釋放診斷 node。
COPY docker/patches/sick-scan-xd-shutdown.patch /tmp/sick-scan-xd.patch
COPY docker/patches/sick-scan-xd-range-bounds.patch /tmp/sick-scan-xd-range-bounds.patch
RUN git -C /tmp/sick-source apply --check /tmp/sick-scan-xd.patch \
    && git -C /tmp/sick-source apply /tmp/sick-scan-xd.patch \
    && git -C /tmp/sick-source apply --check /tmp/sick-scan-xd-range-bounds.patch \
    && git -C /tmp/sick-source apply /tmp/sick-scan-xd-range-bounds.patch \
    && source /opt/ros/jazzy/setup.bash \
    && colcon --log-base /tmp/sick-log build --base-paths /tmp/sick-source \
        --build-base /tmp/sick-build --install-base /opt/mobile_base/sick_scan_xd \
        --executor sequential --cmake-args -DROS_VERSION=2 -DBUILD_DEBUG_TARGET=OFF \
    && printf '%s\n' 'upstream=3.9.0' \
        'commit=a562c5d098de21f6284359f4dfea97e93bd2b4d5' \
        > /opt/mobile_base/sick_scan_xd/source-version.txt \
    && sha256sum /tmp/sick-scan-xd.patch >> /opt/mobile_base/sick_scan_xd/source-version.txt \
    && sha256sum /tmp/sick-scan-xd-range-bounds.patch >> /opt/mobile_base/sick_scan_xd/source-version.txt \
    && rm -rf /tmp/sick-source /tmp/sick-build /tmp/sick-log /tmp/sick-scan-xd.patch /tmp/sick-scan-xd-range-bounds.patch

# 倒裝非對稱 scan：固定原生版本，只修正 metadata angle bounds。
FROM ros_base AS slam_builder
RUN git clone --filter=blob:none --depth 1 --branch 2.8.5 --sparse \
        https://github.com/SteveMacenski/slam_toolbox.git /tmp/slam-source \
    && test "$(git -C /tmp/slam-source rev-parse HEAD)" = ec8f7635dea317b531c419f798f87d90a336f32e \
    && git -C /tmp/slam-source sparse-checkout set \
        CMake config include launch lib rviz_plugin solvers src srv test

COPY docker/patches/slam-toolbox-inverted-bounds.patch /tmp/slam-toolbox.patch
RUN git -C /tmp/slam-source apply --check /tmp/slam-toolbox.patch \
    && git -C /tmp/slam-source apply /tmp/slam-toolbox.patch \
    && source /opt/ros/jazzy/setup.bash \
    && MAKEFLAGS=-j4 colcon --log-base /tmp/slam-log build --base-paths /tmp/slam-source \
        --build-base /tmp/slam-build --install-base /opt/mobile_base/slam_toolbox \
        --executor sequential --cmake-args -DBUILD_TESTING=OFF \
    && printf '%s\n' 'upstream=2.8.5' \
        'commit=ec8f7635dea317b531c419f798f87d90a336f32e' \
        > /opt/mobile_base/slam_toolbox/source-version.txt \
    && sha256sum /tmp/slam-toolbox.patch >> /opt/mobile_base/slam_toolbox/source-version.txt \
    && rm -rf /tmp/slam-source /tmp/slam-build /tmp/slam-log /tmp/slam-toolbox.patch

# apt 版保留作為依賴／基線；overlays 提供正式 executable。
FROM ros_base
COPY --from=sick_builder /opt/mobile_base/sick_scan_xd /opt/mobile_base/sick_scan_xd
COPY --from=slam_builder /opt/mobile_base/slam_toolbox /opt/mobile_base/slam_toolbox

# 配合 host UID/GID，準備非 root 使用者的可寫家目錄。
ARG LOCAL_UID=1000
ARG LOCAL_GID=1000
RUN mkdir -p /home/mobile_base /workspace \
    && chown "${LOCAL_UID}:${LOCAL_GID}" /home/mobile_base

ENV HOME=/home/mobile_base

# 共用 ROS 環境：互動 Bash 與 bash -c 都載入 Jazzy／workspace overlay。
RUN cat <<'EOF' > /etc/mobile-base-ros.bash
source /opt/ros/jazzy/setup.bash
source /opt/mobile_base/sick_scan_xd/local_setup.bash
source /opt/mobile_base/slam_toolbox/local_setup.bash
if [[ -f /workspace/install/setup.bash ]]; then
    source /workspace/install/setup.bash
fi
EOF

RUN echo 'source /etc/mobile-base-ros.bash' >> /etc/bash.bashrc
ENV BASH_ENV=/etc/mobile-base-ros.bash

# 開發容器保持運行，透過 docker compose exec 進入操作。
WORKDIR /workspace
USER ${LOCAL_UID}:${LOCAL_GID}
CMD ["sleep", "infinity"]
