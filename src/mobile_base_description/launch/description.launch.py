"""Publish the model independently; optional control declaration opens no device."""
from pathlib import Path
import xml.etree.ElementTree as ET
import xacro
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_model(context):
    model = Path(LaunchConfiguration('model_file').perform(context)).expanduser().resolve()
    if not model.is_file():
        raise RuntimeError('Model file missing: ' + str(model))
    robot = ET.fromstring(xacro.process_file(str(model)).toxml())
    if robot.find('ros2_control') is not None:
        raise RuntimeError('model_file must contain geometry only; hardware_config supplies control declaration')
    config_path = LaunchConfiguration('hardware_config').perform(context)
    if config_path:
        path = Path(config_path).expanduser().resolve()
        with path.open(encoding='utf8') as stream:
            config = yaml.safe_load(stream)
        hardware = config.get('hardware') if isinstance(config, dict) else None
        if not isinstance(hardware, dict) or not hardware or any(value is None for value in hardware.values()):
            raise RuntimeError('Explicit non-null hardware mapping required for control model')
        joint_names = ('left_wheel_joint', 'right_wheel_joint')
        for name in joint_names:
            if robot.find(f"joint[@name='{name}']") is None:
                raise RuntimeError('model missing canonical wheel joint: ' + name)
        control = ET.SubElement(robot, 'ros2_control', name='M1', type='system')
        hw = ET.SubElement(control, 'hardware')
        ET.SubElement(hw, 'plugin').text = 'mobile_base_control/M1System'
        for key, value in hardware.items():
            ET.SubElement(hw, 'param', name=key).text = str(value).lower() if isinstance(value, bool) else str(value)
        for name in joint_names:
            joint = ET.SubElement(control, 'joint', name=name)
            ET.SubElement(joint, 'command_interface', name='velocity')
            ET.SubElement(joint, 'state_interface', name='velocity')
            ET.SubElement(joint, 'state_interface', name='position')
    return [Node(package='robot_state_publisher', executable='robot_state_publisher',
                 parameters=[{'robot_description': ET.tostring(robot, encoding='unicode')}], output='screen')]


def generate_launch_description():
    model = Path(get_package_share_directory('mobile_base_description')) / 'urdf/mobile_base.urdf.xacro'
    return LaunchDescription([
        DeclareLaunchArgument('model_file', default_value=str(model), description='Geometry-only URDF/xacro'),
        DeclareLaunchArgument('hardware_config', default_value='',
                              description='Optional explicit M1 profile for the control declaration; no device startup'),
        OpaqueFunction(function=start_model),
    ])
