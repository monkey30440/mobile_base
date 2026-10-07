"""Operator IMU verification entry; all device facts supplied explicitly."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    path = Path(LaunchConfiguration('imu_config').perform(context)).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f'IMU imu_config file required: {path}')
    return [Node(package='mobile_base_perception', executable='usb_imu', name='usb_imu',
                 parameters=[str(path)], output='screen')]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('imu_config'), OpaqueFunction(function=setup)])
