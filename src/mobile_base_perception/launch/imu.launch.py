"""Start the USB IMU adapter with an explicitly selected ROS parameter file."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_imu(context):
    path = Path(LaunchConfiguration('imu_config').perform(context)).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError('IMU configuration file missing: ' + str(path))
    return [Node(package='mobile_base_perception', executable='usb_imu',
                 name='usb_imu', parameters=[str(path)], output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('imu_config', description='Explicit USB IMU ROS parameter YAML'),
        OpaqueFunction(function=start_imu),
    ])
