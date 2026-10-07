"""Operator LiDAR verification entry; native sensor launch declares explicit facts."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    launch = Path(get_package_share_directory('mobile_base_perception')) / 'launch/dual_picoscan.launch.py'
    names = ('fl_hostname','br_hostname','udp_receiver_ip','fl_udp_port','br_udp_port',
             'fl_check_udp_port','br_check_udp_port','ros_qos')
    return LaunchDescription([
        *[DeclareLaunchArgument(name) for name in names],
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(launch)),
            launch_arguments={name: LaunchConfiguration(name) for name in names}.items()),
    ])
