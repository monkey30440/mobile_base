# 基礎環境：指定 Isaac ROS image 與確切內容。
FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack@sha256:e5a7ecfaea177c602a43937c932672dd354ed8bf3acc11e29ca7c5ebc6a891d6

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

# 配合 host UID/GID，準備非 root 使用者的可寫家目錄。
ARG LOCAL_UID=1000
ARG LOCAL_GID=1000
RUN mkdir -p /home/mobile_base /workspace \
    && chown "${LOCAL_UID}:${LOCAL_GID}" /home/mobile_base

ENV HOME=/home/mobile_base

# 共用 ROS 環境：互動 Bash 與 bash -c 都載入 Jazzy／workspace overlay。
RUN cat <<'EOF' > /etc/mobile-base-ros.bash
source /opt/ros/jazzy/setup.bash
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
