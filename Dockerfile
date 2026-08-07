FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack

# ros2_control：SUB-001 hardware_interface 插件與 SUB-004 diff_drive_controller
# base image 未預裝，須另行安裝
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3-pip \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
    && rm -rf /var/lib/apt/lists/*

# Stage 1 診斷腳本使用；C++ hardware interface 不依賴
RUN pip3 install --no-cache-dir --break-system-packages \
    pyserial

WORKDIR /workspace
