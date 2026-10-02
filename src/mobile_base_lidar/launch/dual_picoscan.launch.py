"""Compose two native drivers; network facts must be supplied by the Operator."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_devices(context):
    value = lambda name: LaunchConfiguration(name).perform(context)
    ports = [int(value(name)) for name in ('fl_udp_port', 'br_udp_port', 'fl_check_udp_port', 'br_check_udp_port')]
    if len(set(ports)) != len(ports) or any(port < 1 or port > 65535 for port in ports):
        raise RuntimeError('LiDAR receive/check UDP ports must be distinct and in 1..65535')
    if value('fl_hostname') == value('br_hostname'):
        raise RuntimeError('FL and BR require distinct sensor IP addresses')
    native = str(Path(get_package_share_directory('sick_scan_xd')) / 'launch' / 'sick_picoscan.launch')
    nodes = []
    for source, frame in (('fl', 'base_lidar_link_FL'), ('br', 'base_lidar_link_BR')):
        namespace = 'lidar/' + source
        overrides = {
            'hostname': value(source + '_hostname'),
            'listen_only_mode': value('listen_only_mode'),
            'udp_receiver_ip': value('udp_receiver_ip'),
            'udp_port': value(source + '_udp_port'),
            'check_udp_receiver_port': value(source + '_check_udp_port'),
            'publish_frame_id': frame,
            'publish_laserscan_fullframe_topic': '/' + namespace + '/scan',
            'publish_laserscan_segment_topic': '/' + namespace + '/scan_segment',
            'imu_enable': 'False',
            'tf_publish_rate': '0',
            'custom_pointclouds': '',
            'host_set_FREchoFilter': value('set_echo_filter'),
            'host_FREchoFilter': value('echo_filter'),
            'ros_qos': value('ros_qos'),
        }
        nodes.append(Node(
            package='sick_scan_xd', executable='sick_generic_caller',
            namespace=namespace, name='picoscan_' + source,
            exec_name='picoscan_' + source, output='screen',
            arguments=[native] + [key + ':=' + item for key, item in overrides.items()],
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
        *[DeclareLaunchArgument(name, description=description) for name, description in facts.items()],
        DeclareLaunchArgument('listen_only_mode', default_value='False',
                              description='Native passive UDP mode; skips SOPAS initialization'),
        DeclareLaunchArgument('set_echo_filter', default_value='False',
                              description='Set native sensor echo filter on startup (transient SOPAS write)'),
        DeclareLaunchArgument('echo_filter', default_value='2',
                              description='Native echo selector: 0 FIRST, 1 ALL, 2 LAST; applied only when set_echo_filter=True'),
        OpaqueFunction(function=start_devices),
    ])
