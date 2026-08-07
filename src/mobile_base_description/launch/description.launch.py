"""SUB-012 Robot Description — robot_state_publisher。

僅發布車體 TF 與 robot_description，不含控制器。
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    xacro_file = PathJoinSubstitution([
        FindPackageShare('mobile_base_description'),
        'urdf',
        'mobile_base.urdf.xacro',
    ])

    args = [
        DeclareLaunchArgument(
            'use_ros2_control', default_value='true',
            description='是否於 URDF 中宣告 ros2_control 硬體介面'),
        DeclareLaunchArgument(
            'serial_port', default_value='/dev/ttyUSB0',
            description='SUB-001 Base Control 序列埠'),
        DeclareLaunchArgument(
            'use_joint_state_publisher_gui', default_value='false',
            description='以 GUI 手動驅動關節，僅供幾何檢視'),
    ]

    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' use_ros2_control:=', LaunchConfiguration('use_ros2_control'),
            ' serial_port:=', LaunchConfiguration('serial_port'),
        ]),
        value_type=str,
    )

    nodes = [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}],
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            condition=IfCondition(
                LaunchConfiguration('use_joint_state_publisher_gui')),
        ),
    ]

    return LaunchDescription(args + nodes)
