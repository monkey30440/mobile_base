"""Operator control verification entry; native control launch owns the sole RSP."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    model = str(Path(get_package_share_directory('mobile_base_description')) / 'urdf/mobile_base.urdf.xacro')
    control = str(Path(get_package_share_directory('mobile_base_control')) / 'launch/m1.launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('hardware_config', default_value=''),
        DeclareLaunchArgument('model_file', default_value=model),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(control), launch_arguments={
            'hardware_config': LaunchConfiguration('hardware_config'),
            'model_file': LaunchConfiguration('model_file'),
        }.items()),
    ])
