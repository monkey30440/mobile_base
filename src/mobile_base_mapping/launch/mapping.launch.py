"""Use the upstream asynchronous SLAM lifecycle launch; no custom SLAM node."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def start_mapping(context):
    config = Path(LaunchConfiguration('mapping_config').perform(context)).expanduser().resolve()
    if not config.is_file():
        raise RuntimeError('Mapping configuration file missing: ' + str(config))
    native = Path(get_package_share_directory('slam_toolbox')) / 'launch/online_async_launch.py'
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(native)),
                                    launch_arguments={'slam_params_file': str(config),
                                                      'use_sim_time': 'false',
                                                      'autostart': 'true',
                                                      'use_lifecycle_manager': 'false'}.items())]


def generate_launch_description():
    profile = Path(get_package_share_directory('mobile_base_mapping')) / 'config/slam.yaml'
    return LaunchDescription([
        DeclareLaunchArgument('mapping_config', default_value=str(profile),
                              description='Defaults to package config/slam.yaml'),
        OpaqueFunction(function=start_mapping),
    ])
