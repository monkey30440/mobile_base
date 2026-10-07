"""Complete local base verification; no Mapping/Navigation readiness claim."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    launch = Path(get_package_share_directory('mobile_base_bringup')) / 'launch'
    profiles = ('hardware_config','imu_config','filter_config')
    network = ('fl_hostname','br_hostname','udp_receiver_ip','fl_udp_port','br_udp_port',
               'fl_check_udp_port','br_check_udp_port','ros_qos')
    return LaunchDescription([
        *[DeclareLaunchArgument(name) for name in profiles+network],
        DeclareLaunchArgument('foxglove', default_value='False'),
        DeclareLaunchArgument('foxglove_port', default_value='8765'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(launch/'local_base.launch.py')),
            launch_arguments={name: LaunchConfiguration(name) for name in profiles}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(launch/'lidar.launch.py')),
            launch_arguments={name: LaunchConfiguration(name) for name in network}.items()),
        Node(package='foxglove_bridge', executable='foxglove_bridge', name='foxglove_bridge',
             parameters=[{'port': ParameterValue(LaunchConfiguration('foxglove_port'), value_type=int)}],
             condition=IfCondition(LaunchConfiguration('foxglove')), output='screen'),
    ])
