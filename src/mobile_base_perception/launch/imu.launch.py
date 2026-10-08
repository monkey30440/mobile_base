"""Start the USB IMU adapter with the package profile or an explicit override."""
from pathlib import Path
import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def start_imu(context):
    path = Path(LaunchConfiguration('imu_config').perform(context)).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError('IMU configuration file missing: ' + str(path))
    with path.open(encoding='utf8') as stream:
        parameters = yaml.safe_load(stream)['usb_imu']['ros__parameters']
    calibration = parameters.get('calibration_file', '')
    if calibration:
        calibration = str((path.parent / Path(calibration).expanduser()).resolve())
    return [Node(package='mobile_base_perception', executable='usb_imu',
                 name='usb_imu', parameters=[str(path), {'calibration_file': calibration}], output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'imu_config',
            default_value=str(Path(get_package_share_directory('mobile_base_perception'))
                              / 'config' / 'imu.yaml'),
            description='USB IMU ROS parameter YAML (defaults to package config/imu.yaml)'),
        OpaqueFunction(function=start_imu),
    ])
