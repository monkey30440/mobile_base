"""Native local EKF only; model TF belongs to the caller's single RSP."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    config = Path(LaunchConfiguration('filter_config').perform(context)).expanduser().resolve()
    if not config.is_file():
        raise RuntimeError(f'Local estimation filter_config file required: {config}')
    return [Node(package='robot_localization', executable='ekf_node',
                 name='ekf_filter_node', parameters=[str(config)], output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('filter_config', description='Explicit native EKF YAML; no deployment defaults'),
        OpaqueFunction(function=setup),
    ])
