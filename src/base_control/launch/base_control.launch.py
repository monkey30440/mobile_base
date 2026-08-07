"""SUB-001 Base Control + SUB-004 Differential Drive Controller。

啟動 robot_state_publisher、controller_manager，
並依序啟用 joint_state_broadcaster 與 diff_drive_controller。
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
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
    controllers_file = PathJoinSubstitution([
        FindPackageShare('base_control'),
        'config',
        'controllers.yaml',
    ])

    args = [
        DeclareLaunchArgument(
            'serial_port', default_value='/dev/ttyUSB0',
            description='DEXMART M1 驅動器序列埠'),
        DeclareLaunchArgument(
            'controllers_file', default_value=controllers_file,
            description='controller_manager 參數檔'),
    ]

    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' use_ros2_control:=true',
            ' serial_port:=', LaunchConfiguration('serial_port'),
        ]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}],
    )

    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        output='screen',
        parameters=[
            {'robot_description': robot_description},
            LaunchConfiguration('controllers_file'),
        ],
    )

    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )

    diff_drive_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller'],
        output='screen',
    )

    # 廣播器啟用後才啟用控制器，避免競爭
    ordered = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[diff_drive_controller],
        )
    )

    return LaunchDescription(
        args + [robot_state_publisher, controller_manager, joint_state_broadcaster, ordered]
    )
