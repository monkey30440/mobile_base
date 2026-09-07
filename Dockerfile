# =========================
# 1. Shared runtime base
# =========================
FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack AS base

ENV DEBIAN_FRONTEND=noninteractive

RUN curl -fsSL https://packages.fluentbit.io/fluentbit.key \
        | gpg --dearmor -o /usr/share/keyrings/fluentbit-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/fluentbit-keyring.gpg] https://packages.fluentbit.io/ubuntu/noble noble main" \
        > /etc/apt/sources.list.d/fluent-bit.list

RUN echo 'Acquire::http::Pipeline-Depth "0";' > /etc/apt/apt.conf.d/99fix \
    && echo 'Acquire::Retries "3";' >> /etc/apt/apt.conf.d/99fix \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libmodbus-dev \
        ros-jazzy-fastcdr \
        ros-jazzy-fastrtps \
        ros-jazzy-rmw-fastrtps-cpp \
        ros-jazzy-rmw-fastrtps-shared-cpp \
        ros-jazzy-rosidl-typesupport-fastrtps-cpp \
        ros-jazzy-rosidl-typesupport-fastrtps-c \
        ros-jazzy-rosidl-dynamic-typesupport-fastrtps \
        ros-jazzy-navigation2 \
        ros-jazzy-nav2-bringup \
        ros-jazzy-slam-toolbox \
        ros-jazzy-robot-localization \
        ros-jazzy-ros2-control \
        ros-jazzy-ros2-controllers \
        ros-jazzy-sick-scan-xd \
        ros-jazzy-foxglove-bridge \
        ros-jazzy-teleop-twist-keyboard \
        fluent-bit=4.2.8 \
        python3-serial \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/mobile_base

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

CMD ["bash"]


# =========================
# 2. Development environment
# =========================
FROM base AS dev

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ros-jazzy-rviz2 \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN echo '[ -f /workspaces/mobile_base/install/setup.bash ] && source /workspaces/mobile_base/install/setup.bash' >> ~/.bashrc

CMD ["bash"]


# =========================
# 3. Release builder
# =========================
FROM base AS builder

WORKDIR /ws

COPY src /ws/src

RUN bash -c "source /opt/ros/jazzy/setup.bash && \
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release"


# =========================
# 4. Release runtime
# =========================
FROM base AS release

WORKDIR /workspaces/mobile_base

COPY --from=builder /ws/install /workspaces/mobile_base/install

RUN echo "source /workspaces/mobile_base/install/setup.bash" >> ~/.bashrc

CMD ["bash"]
