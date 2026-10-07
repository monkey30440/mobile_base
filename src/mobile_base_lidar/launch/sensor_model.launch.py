"""Compose real single-echo scans with the authoritative base model; no motion."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    lidar=Path(get_package_share_directory('mobile_base_lidar'))/'launch'
    model=Path(get_package_share_directory('mobile_base_description'))/'launch'
    names=('fl_hostname','br_hostname','udp_receiver_ip','fl_udp_port','br_udp_port',
           'fl_check_udp_port','br_check_udp_port','ros_qos')
    arguments={name:LaunchConfiguration(name) for name in names}
    return LaunchDescription([
        *[DeclareLaunchArgument(name) for name in names],
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(model/'description.launch.py'))),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(lidar/'dual_picoscan.launch.py')),
            launch_arguments={**{name:arguments[name] for name in names},
                              'set_echo_filter':'True','echo_filter':'2','listen_only_mode':'False'}.items()),
    ])
