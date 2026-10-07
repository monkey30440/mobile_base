"""Start the sole native model TF owner with explicitly selected optical yaw."""
import math
from pathlib import Path
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_model(context):
    mapping={name:LaunchConfiguration(name).perform(context) for name in ('fl_scan_yaw','br_scan_yaw')}
    if any(not math.isfinite(float(v)) for v in mapping.values()):
        raise RuntimeError('scan yaw must be finite radians from an explicit mounting profile')
    model=Path(get_package_share_directory('mobile_base_description'))/'urdf/mobile_base.urdf.xacro'
    description=xacro.process_file(str(model),mappings=mapping).toxml()
    return [Node(package='robot_state_publisher',executable='robot_state_publisher',
                 parameters=[{'robot_description':description}],output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('fl_scan_yaw',description='Explicit FL optical yaw relative to CAD mount, radians'),
        DeclareLaunchArgument('br_scan_yaw',description='Explicit BR optical yaw relative to CAD mount, radians'),
        OpaqueFunction(function=start_model),
    ])
