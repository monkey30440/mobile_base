FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack

# base image 未預裝下列項目：
#   ros2_control / ros2_controllers  SUB-001 hardware_interface、SUB-004 diff_drive_controller
#   xacro / joint_state_publisher_gui SUB-012 Robot Description
#   libmodbus-dev                     SUB-001 Modbus RTU 實作
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3-pip \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-xacro \
        ros-jazzy-joint-state-publisher-gui \
        libmodbus-dev \
    && rm -rf /var/lib/apt/lists/*

# Stage 1 診斷腳本使用；C++ hardware interface 不依賴
RUN pip3 install --no-cache-dir --break-system-packages \
    pyserial

WORKDIR /workspace
