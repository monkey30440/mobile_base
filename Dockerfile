FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmodbus-dev \
        ros-jazzy-navigation2 \
        ros-jazzy-nav2-bringup \
        ros-jazzy-slam-toolbox \
        ros-jazzy-robot-localization \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-dual-laser-merger \
        ros-jazzy-sick-scan-xd \
        ros-jazzy-foxglove-bridge \
        python3-serial \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/mobile_base

CMD ["bash"]