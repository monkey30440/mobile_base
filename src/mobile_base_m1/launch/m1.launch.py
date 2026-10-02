"""Configure native controller manager from an explicit M1 target profile."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    path = LaunchConfiguration('hardware_config').perform(context)
    model = LaunchConfiguration('model_file').perform(context)
    if not path or not model:
        raise RuntimeError('hardware_config and model_file are required; no guessed hardware defaults')
    with open(path, encoding='utf8') as stream:
        config = yaml.safe_load(stream)
    hardware = config['hardware']
    required = ('serial_port', 'baud', 'parity', 'stop_bits', 'response_timeout_seconds', 'enable_timeout_seconds',
                'firmware', 'verified_speed_mode', 'verified_multidrive2', 'pdo_mapping', 'drive_enable_setting')
    required += tuple(side + suffix for side in ('left_', 'right_') for suffix in
                      ('drive_id', 'gear_ratio', 'direction', 'feedback_rpm_per_count', 'max_motor_rpm'))
    for key in required:
        if key not in hardware or hardware[key] is None:
            raise RuntimeError('M1 target fact required: ' + key)
    controller = config['controller']
    for key in ('wheel_radius', 'wheel_separation', 'cmd_vel_timeout', 'update_rate',
                'linear_velocity_limit', 'angular_velocity_limit'):
        value = controller.get(key)
        if value is None or not math.isfinite(value) or value <= 0:
            raise RuntimeError('positive calibrated/operational controller value required: ' + key)
    robot = ET.fromstring(Path(model).read_text(encoding='utf8'))
    if robot.find('ros2_control') is not None:
        raise RuntimeError('model_file must contain geometry only; M1 owns ros2_control fragment')
    joint_names = ('left_wheel_joint', 'right_wheel_joint')
    for name in joint_names:
        if robot.find(f"joint[@name='{name}']") is None:
            raise RuntimeError('model missing canonical wheel joint: ' + name)
    control = ET.SubElement(robot, 'ros2_control', name='M1', type='system')
    hw = ET.SubElement(control, 'hardware')
    ET.SubElement(hw, 'plugin').text = 'mobile_base_m1/M1System'
    for key in required:
        value = hardware[key]
        ET.SubElement(hw, 'param', name=key).text = str(value).lower() if isinstance(value, bool) else str(value)
    for name in joint_names:
        joint = ET.SubElement(control, 'joint', name=name)
        ET.SubElement(joint, 'command_interface', name='velocity')
        ET.SubElement(joint, 'state_interface', name='velocity')
    description = ET.tostring(robot, encoding='unicode')
    parameters = {'update_rate': int(controller['update_rate']),
                  'base_controller.type': 'diff_drive_controller/DiffDriveController',
                  'joint_state_broadcaster.type': 'joint_state_broadcaster/JointStateBroadcaster'}
    budget = controller.get('native_hardware_execution_budget_us')
    if budget is not None:
        for metric, prefix in (('mean', 'mean_error'), ('stddev', 'standard_deviation')):
            warn, error = (budget.get(metric + '_' + level) for level in ('warn', 'error'))
            if any(value is None or not math.isfinite(value) or value <= 0 for value in (warn, error)) or warn >= error:
                raise RuntimeError('positive ordered native hardware execution budget required: ' + metric)
            for level, value in (('warn', warn), ('error', error)):
                parameters['diagnostics.threshold.hardware_components.execution_time.' + prefix + '.' + level] = float(value)
    drive = {'left_wheel_names': [joint_names[0]], 'right_wheel_names': [joint_names[1]],
             'wheel_radius': float(controller['wheel_radius']),
             'wheel_separation': float(controller['wheel_separation']),
             'position_feedback': False, 'open_loop': False, 'enable_odom_tf': False,
             'odom_frame_id': 'odom', 'base_frame_id': 'base_footprint',
             'cmd_vel_timeout': float(controller['cmd_vel_timeout']),
             'publish_limited_velocity': True,
             'linear.x.has_velocity_limits': True,
             'linear.x.max_velocity': float(controller['linear_velocity_limit']),
             'linear.x.min_velocity': -float(controller['linear_velocity_limit']),
             'angular.z.has_velocity_limits': True,
             'angular.z.max_velocity': float(controller['angular_velocity_limit']),
             'angular.z.min_velocity': -float(controller['angular_velocity_limit'])}
    # Native spawner loads per-controller parameters from the required target YAML.
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as stream:
        yaml.safe_dump({'base_controller': {'ros__parameters': drive}}, stream)
        drive_file = stream.name
    def cleanup(_context):
        Path(drive_file).unlink(missing_ok=True)
        return []

    return [RegisterEventHandler(OnShutdown(on_shutdown=[OpaqueFunction(function=cleanup)])),
            Node(package='robot_state_publisher', executable='robot_state_publisher',
                 parameters=[{'robot_description': description}]),
            Node(package='controller_manager', executable='ros2_control_node',
                 parameters=[parameters], output='screen'),
            Node(package='controller_manager', executable='spawner',
                 arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'], output='screen'),
            Node(package='controller_manager', executable='spawner',
                 arguments=['base_controller', '--controller-manager', '/controller_manager',
                            '--param-file', drive_file], output='screen')]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('hardware_config', default_value=''),
                              DeclareLaunchArgument('model_file', default_value=''),
                              OpaqueFunction(function=setup)])
