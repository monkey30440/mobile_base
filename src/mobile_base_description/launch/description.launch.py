"""Start the sole native model TF owner from the supplied URDF mounting poses."""
from pathlib import Path
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    model = Path(get_package_share_directory('mobile_base_description')) / 'urdf/mobile_base.urdf.xacro'
    description = xacro.process_file(str(model)).toxml()
    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description}], output='screen'),
    ])
