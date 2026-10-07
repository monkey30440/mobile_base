"""Compose two native drivers; network facts must be supplied by the Operator."""
from pathlib import Path
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_devices(context):
    config_path = LaunchConfiguration('lidar_config').perform(context)
    config = {}
    if config_path:
        path = Path(config_path).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError('LiDAR configuration file missing: ' + str(path))
        with path.open(encoding='utf8') as stream:
            config = yaml.safe_load(stream)
        allowed = {'fl_hostname', 'br_hostname', 'udp_receiver_ip', 'fl_udp_port',
                   'br_udp_port', 'fl_check_udp_port', 'br_check_udp_port', 'ros_qos',
                   'listen_only_mode', 'set_echo_filter', 'echo_filter', 'tick_to_timestamp_mode'}
        if not isinstance(config, dict) or set(config) - allowed:
            raise RuntimeError('LiDAR configuration must be a mapping of supported launch arguments')
    defaults = {'listen_only_mode': 'False', 'set_echo_filter': 'True',
                'echo_filter': '2', 'tick_to_timestamp_mode': '1'}

    def value(name):
        selected = LaunchConfiguration(name).perform(context)
        if not selected:
            selected = config.get(name, defaults.get(name))
        if selected is None or str(selected) == '':
            raise RuntimeError('LiDAR target fact required: ' + name)
        return str(selected)

    for name in ('fl_hostname', 'br_hostname', 'udp_receiver_ip', 'fl_udp_port',
                 'br_udp_port', 'fl_check_udp_port', 'br_check_udp_port', 'ros_qos'):
        value(name)
    ports = [int(value(name)) for name in ('fl_udp_port', 'br_udp_port', 'fl_check_udp_port', 'br_check_udp_port')]
    if len(set(ports)) != len(ports) or any(port < 1 or port > 65535 for port in ports):
        raise RuntimeError('LiDAR receive/check UDP ports must be distinct and in 1..65535')
    if value('fl_hostname') == value('br_hostname'):
        raise RuntimeError('FL and BR require distinct sensor IP addresses')
    def boolean(name):
        text = value(name).lower()
        if text not in ('true', 'false', '1', '0'):
            raise RuntimeError(name + ' must be true/false or 1/0')
        return '1' if text in ('true', '1') else '0'

    native = str(Path(get_package_share_directory('sick_scan_xd')) / 'launch' / 'sick_picoscan.launch')
    nodes = []
    for source, frame in (('fl', 'base_lidar_link_FL'), ('br', 'base_lidar_link_BR')):
        namespace = 'lidar/' + source
        overrides = {
            'hostname': value(source + '_hostname'),
            'udp_receiver_ip': value('udp_receiver_ip'),
            'udp_port': int(value(source + '_udp_port')),
            'check_udp_receiver_port': int(value(source + '_check_udp_port')),
            'publish_frame_id': frame,
            'publish_laserscan_fullframe_topic': '/' + namespace + '/scan',
            'publish_laserscan_segment_topic': '/' + namespace + '/scan_segment',
            'tf_publish_rate': 0.0,
            'custom_pointclouds': '',
            'host_FREchoFilter': int(value('echo_filter')),
            'ros_qos': int(value('ros_qos')),
            'tick_to_timestamp_mode': int(value('tick_to_timestamp_mode')),
        }
        nodes.append(Node(
            package='sick_scan_xd', executable='sick_generic_caller',
            namespace=namespace, name='picoscan_' + source,
            exec_name='picoscan_' + source, output='screen',
            # Native XML configuration owns parameter loading. Its ROS2 bool
            # string conversion uses stoi, so CLI booleans must be 1/0.
            arguments=[native] + [key + ':=' + str(item) for key, item in {
                **overrides, 'listen_only_mode': boolean('listen_only_mode'),
                'host_set_FREchoFilter': boolean('set_echo_filter'),
                'imu_enable': '0',
            }.items()],
        ))
    return nodes


def generate_launch_description():
    facts = {
        'fl_hostname': 'Confirmed front-left picoScan sensor IP',
        'br_hostname': 'Confirmed back-right picoScan sensor IP',
        'udp_receiver_ip': 'Target host IPv4 address reachable from both sensors',
        'fl_udp_port': 'Front-left scan UDP destination port',
        'br_udp_port': 'Back-right scan UDP destination port',
        'fl_check_udp_port': 'Front-left receiver-IP check UDP port',
        'br_check_udp_port': 'Back-right receiver-IP check UDP port',
        'ros_qos': 'Native sick_scan_xd QoS selector; choose and record against target consumers',
    }
    return LaunchDescription([
        DeclareLaunchArgument('lidar_config',
                              default_value=str(Path(get_package_share_directory('mobile_base_perception')) / 'config/lidar.yaml'),
                              description='Defaults to package config/lidar.yaml; CLI overrides take precedence'),
        *[DeclareLaunchArgument(name, default_value='', description=description) for name, description in facts.items()],
        DeclareLaunchArgument('listen_only_mode', default_value='',
                              description='Native passive UDP mode; skips SOPAS initialization'),
        DeclareLaunchArgument('set_echo_filter', default_value='',
                              description='Set native sensor echo filter on startup (transient SOPAS write)'),
        DeclareLaunchArgument('echo_filter', default_value='',
                              description='Native selector: default LAST (2) gives one stable scan frame per sensor; 0 FIRST, 1 ALL. Set on each startup'),
        DeclareLaunchArgument('tick_to_timestamp_mode', default_value='',
                              description='Native timestamp mode: 0 PLL, 1 first host time plus sensor elapsed ticks'),
        OpaqueFunction(function=start_devices),
    ])
