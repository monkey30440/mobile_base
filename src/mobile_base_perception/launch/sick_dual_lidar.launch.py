# Copyright 2026 Antigravity Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Launch composition for dual SICK picoScan150 2D LiDAR acquisition in S2 Perception."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for dual SICK picoScan150 LiDAR acquisition."""
    sick_scan_pkg = get_package_share_directory('sick_scan_xd')

    # Declare launch arguments
    front_hostname_arg = DeclareLaunchArgument(
        'front_hostname',
        default_value='192.168.0.1',
        description='IP address of Front-Left SICK picoScan150 LiDAR'
    )

    rear_hostname_arg = DeclareLaunchArgument(
        'rear_hostname',
        default_value='192.168.0.2',
        description='IP address of Rear-Right SICK picoScan150 LiDAR'
    )

    udp_receiver_ip_arg = DeclareLaunchArgument(
        'udp_receiver_ip',
        default_value='192.168.0.100',
        description='Host IP address to receive LiDAR UDP scan packets'
    )

    front_frame_arg = DeclareLaunchArgument(
        'front_frame_id',
        default_value='base_lidar_link_FL',
        description='TF frame ID for Front-Left SICK LiDAR'
    )

    rear_frame_arg = DeclareLaunchArgument(
        'rear_frame_id',
        default_value='base_lidar_link_BR',
        description='TF frame ID for Rear-Right SICK LiDAR'
    )

    front_topic_arg = DeclareLaunchArgument(
        'front_topic',
        default_value='/scan_front',
        description='Authoritative output topic for Front-Left LaserScan'
    )

    rear_topic_arg = DeclareLaunchArgument(
        'rear_topic',
        default_value='/scan_rear',
        description='Authoritative output topic for Rear-Right LaserScan'
    )

    # Launch configuration substitutions
    front_hostname = LaunchConfiguration('front_hostname')
    rear_hostname = LaunchConfiguration('rear_hostname')
    udp_receiver_ip = LaunchConfiguration('udp_receiver_ip')
    front_frame_id = LaunchConfiguration('front_frame_id')
    rear_frame_id = LaunchConfiguration('rear_frame_id')
    front_topic = LaunchConfiguration('front_topic')
    rear_topic = LaunchConfiguration('rear_topic')

    # Path to upstream SICK picoScan template launch file
    picoscan_launch_file = PathJoinSubstitution([
        sick_scan_pkg, 'launch', 'sick_picoscan.launch'
    ])

    # Front-Left SICK picoScan150 node instance
    front_lidar_node = Node(
        package='sick_scan_xd',
        executable='sick_generic_caller',
        name='front_lidar_node',
        output='screen',
        arguments=[
            picoscan_launch_file,
            ['hostname:=', front_hostname],
            ['udp_receiver_ip:=', udp_receiver_ip],
            ['udp_port:=', '2115'],
            ['imu_udp_port:=', '7503'],
            'imu_enable:=False',
            'start_sopas_service:=False',
            ['check_udp_receiver_ip:=', '0'],
            ['nodename:=', 'front_lidar_node'],
            ['publish_frame_id:=', front_frame_id],
            ['publish_laserscan_fullframe_topic:=', front_topic],
            'publish_laserscan_segment_topic:=',
            'custom_pointclouds:=',
            ['tf_publish_rate:=', '0.0'],
            ['sw_pll_only_publish:=', '1'],
            ['verbose_level:=', '0'],
            ['imu_enable:=', 'False'],
        ],
        remappings=[
            ('scan_fullframe', front_topic),
            ('/scan_fullframe', front_topic),
        ],
    )

    # Rear-Right SICK picoScan150 node instance
    rear_lidar_node = Node(
        package='sick_scan_xd',
        executable='sick_generic_caller',
        name='rear_lidar_node',
        output='screen',
        arguments=[
            picoscan_launch_file,
            ['hostname:=', rear_hostname],
            ['udp_receiver_ip:=', udp_receiver_ip],
            ['udp_port:=', '2116'],
            ['imu_udp_port:=', '7504'],
            'imu_enable:=False',
            'start_sopas_service:=False',
            ['check_udp_receiver_ip:=', '0'],
            ['nodename:=', 'rear_lidar_node'],
            ['publish_frame_id:=', rear_frame_id],
            ['publish_laserscan_fullframe_topic:=', rear_topic],
            'publish_laserscan_segment_topic:=',
            'custom_pointclouds:=',
            ['tf_publish_rate:=', '0.0'],
            ['sw_pll_only_publish:=', '1'],
            ['verbose_level:=', '0'],
            ['imu_enable:=', 'False'],
        ],
        remappings=[
            ('scan_fullframe', rear_topic),
            ('/scan_fullframe', rear_topic),
        ],
    )

    return LaunchDescription([
        front_hostname_arg,
        rear_hostname_arg,
        udp_receiver_ip_arg,
        front_frame_arg,
        rear_frame_arg,
        front_topic_arg,
        rear_topic_arg,
        front_lidar_node,
        rear_lidar_node,
    ])
