FROM nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack@sha256:e5a7ecfaea177c602a43937c932672dd354ed8bf3acc11e29ca7c5ebc6a891d6

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# The inherited Jetson HTTP endpoint returns 401 on this network; HTTPS works.
RUN sed -i 's|http://repo.download.nvidia.com/|https://repo.download.nvidia.com/|g' \
    /etc/apt/sources.list.d/nvidia-jetson-apt-source.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential git python3-colcon-common-extensions python3-rosdep \
    python3-pytest python3-vcstool \
    ros-jazzy-demo-nodes-cpp ros-jazzy-diagnostic-updater \
    ros-jazzy-diagnostic-aggregator ros-jazzy-robot-state-publisher \
    ros-jazzy-robot-localization ros-jazzy-slam-toolbox \
    ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-route \
    ros-jazzy-teleop-twist-keyboard ros-jazzy-rviz2 \
    ros-jazzy-rqt-console ros-jazzy-rqt-robot-monitor \
    && dpkg-query -W > /opt/mobile-base-packages.tsv \
    && rm -rf /var/lib/apt/lists/*

ARG LOCAL_UID=1000
ARG LOCAL_GID=1000
RUN mkdir -p /home/mobile_base /workspace \
    && chown "${LOCAL_UID}:${LOCAL_GID}" /home/mobile_base /workspace
ENV HOME=/home/mobile_base ROS_DISTRO=jazzy
COPY docker/ros-environment.sh /etc/mobile-base/ros-environment.sh
COPY docker/entrypoint.sh /usr/local/bin/mobile-base-entrypoint
RUN chmod +x /usr/local/bin/mobile-base-entrypoint \
    && echo 'source /etc/mobile-base/ros-environment.sh' >> /etc/bash.bashrc
ENV BASH_ENV=/etc/mobile-base/ros-environment.sh
WORKDIR /workspace
USER ${LOCAL_UID}:${LOCAL_GID}
ENTRYPOINT ["/usr/local/bin/mobile-base-entrypoint"]
CMD ["sleep", "infinity"]
