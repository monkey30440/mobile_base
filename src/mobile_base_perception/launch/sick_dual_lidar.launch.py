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

"""Launch composition for dual SICK 2D LiDAR acquisition in S2 Perception."""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for dual SICK LiDAR acquisition."""
    sick_scan_pkg = get_package_share_directory('sick_scan_xd')

    # Declare launch arguments
    front_hostname_arg = DeclareLaunchArgument(
        'front_hostname',
        default_value='192.168.0.1',
        description='IP address of Front-Left SICK LiDAR'
    )

    rear_hostname_arg = DeclareLaunchArgument(
        'rear_hostname',
        default_value='192.168.0.2',
        description='IP address of Rear-Right SICK LiDAR'
    )

    front_port_arg = DeclareLaunchArgument(
        'front_port',
        default_value='2112',
        description='TCP port for Front-Left SICK LiDAR'
    )

    rear_port_arg = DeclareLaunchArgument(
        'rear_port',
        default_value='2112',
        description='TCP port for Rear-Right SICK LiDAR'
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

    scanner_type_arg = DeclareLaunchArgument(
        'scanner_type',
        default_value='sick_tim_5xx',
        description='Scanner model type for sick_scan_xd launch resolution'
    )

    tf_publish_rate_arg = DeclareLaunchArgument(
        'tf_publish_rate',
        default_value='0.0',
        description='Rate of internal TF publishing in Hz (0.0 to disable; TF owned by S1)'
    )

    ros_qos_arg = DeclareLaunchArgument(
        'ros_qos',
        default_value='4',
        description='ROS 2 QoS profile (4: rclcpp::SensorDataQoS)'
    )

    # Launch configuration substitutions
    front_hostname = LaunchConfiguration('front_hostname')
    rear_hostname = LaunchConfiguration('rear_hostname')
    front_port = LaunchConfiguration('front_port')
    rear_port = LaunchConfiguration('rear_port')
    front_frame_id = LaunchConfiguration('front_frame_id')
    rear_frame_id = LaunchConfiguration('rear_frame_id')
    front_topic = LaunchConfiguration('front_topic')
    rear_topic = LaunchConfiguration('rear_topic')
    scanner_type = LaunchConfiguration('scanner_type')
    tf_publish_rate = LaunchConfiguration('tf_publish_rate')
    ros_qos = LaunchConfiguration('ros_qos')

    # Path to underlying SICK template launch file
    sick_launch_file = PathJoinSubstitution([
        sick_scan_pkg, 'launch',
        [scanner_type, '.launch']
    ])

    # Front-Left SICK LiDAR node instance
    front_lidar_node = Node(
        package='sick_scan_xd',
        executable='sick_generic_caller',
        name='front_lidar_node',
        output='screen',
        arguments=[
            sick_launch_file,
            ['hostname:=', front_hostname],
            ['port:=', front_port],
            ['nodename:=', 'front_lidar_node'],
            ['frame_id:=', front_frame_id],
            ['laserscan_topic:=', front_topic],
            ['cloud_topic:=', '/cloud_front'],
            ['tf_publish_rate:=', tf_publish_rate],
            ['ros_qos:=', ros_qos],
            ['sw_pll_only_publish:=', 'true'],
        ],
        remappings=[
            ('scan', front_topic),
            ('/scan', front_topic),
        ],
    )

    # Rear-Right SICK LiDAR node instance
    rear_lidar_node = Node(
        package='sick_scan_xd',
        executable='sick_generic_caller',
        name='rear_lidar_node',
        output='screen',
        arguments=[
            sick_launch_file,
            ['hostname:=', rear_hostname],
            ['port:=', rear_port],
            ['nodename:=', 'rear_lidar_node'],
            ['frame_id:=', rear_frame_id],
            ['laserscan_topic:=', rear_topic],
            ['cloud_topic:=', '/cloud_rear'],
            ['tf_publish_rate:=', tf_publish_rate],
            ['ros_qos:=', ros_qos],
            ['sw_pll_only_publish:=', 'true'],
        ],
        remappings=[
            ('scan', rear_topic),
            ('/scan', rear_topic),
        ],
    )

    return LaunchDescription([
        front_hostname_arg,
        rear_hostname_arg,
        front_port_arg,
        rear_port_arg,
        front_frame_arg,
        rear_frame_arg,
        front_topic_arg,
        rear_topic_arg,
        scanner_type_arg,
        tf_publish_rate_arg,
        ros_qos_arg,
        front_lidar_node,
        rear_lidar_node,
    ])
