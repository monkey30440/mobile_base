"""Mapping product composition; native components retain runtime ownership."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def share(package, relative):
    return str(Path(get_package_share_directory(package)) / relative)


def include(package, launch_file, arguments):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(share(package, 'launch/' + launch_file)),
        launch_arguments={name: LaunchConfiguration(name) for name in arguments}.items())


def generate_launch_description():
    profiles = {
        'model_file': ('mobile_base_description', 'urdf/mobile_base.urdf'),
        'hardware_config': ('mobile_base_control', 'config/m1.yaml'),
        'lidar_config': ('mobile_base_perception', 'config/lidar.yaml'),
        'imu_config': ('mobile_base_perception', 'config/imu.yaml'),
        'filter_config': ('mobile_base_odometry', 'config/ekf.yaml'),
        'mapping_config': ('mobile_base_mapping', 'config/slam.yaml'),
    }
    return LaunchDescription([
        *[DeclareLaunchArgument(name, default_value=share(package, relative),
                                description='Selected ' + name + '; defaults to installed package profile')
          for name, (package, relative) in profiles.items()],
        # Description and Control must consume the same selected hardware profile.
        include('mobile_base_description', 'description.launch.py', ['model_file', 'hardware_config']),
        include('mobile_base_perception', 'dual_picoscan.launch.py', ['lidar_config']),
        include('mobile_base_perception', 'imu.launch.py', ['imu_config']),
        include('mobile_base_control', 'm1.launch.py', ['hardware_config']),
        include('mobile_base_odometry', 'odometry.launch.py', ['filter_config']),
        include('mobile_base_mapping', 'mapping.launch.py', ['mapping_config']),
    ])
