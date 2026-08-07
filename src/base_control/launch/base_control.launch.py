"""SUB-001 Base Control launch."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    default_config = PathJoinSubstitution([
        FindPackageShare('base_control'),
        'config',
        'base_control.yaml',
    ])

    config_arg = DeclareLaunchArgument(
        'config',
        default_value=default_config,
        description='base_control 參數檔路徑',
    )

    base_control_node = Node(
        package='base_control',
        executable='base_control_node',
        name='base_control_node',
        output='screen',
        emulate_tty=True,
        parameters=[LaunchConfiguration('config')],
    )

    return LaunchDescription([config_arg, base_control_node])
