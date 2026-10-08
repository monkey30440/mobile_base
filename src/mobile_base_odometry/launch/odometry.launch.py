"""Native local EKF only; model TF belongs to the caller's single RSP."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

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
    profile = Path(get_package_share_directory('mobile_base_odometry')) / 'config/ekf.yaml'
    return LaunchDescription([
        DeclareLaunchArgument('filter_config', default_value=str(profile),
                              description='Native EKF YAML; defaults to package commissioning config'),
        OpaqueFunction(function=setup),
    ])
