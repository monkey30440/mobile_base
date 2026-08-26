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

"""Compose the canonical real-hardware Navigation Mode launches."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import (
    AnyLaunchDescriptionSource,
    PythonLaunchDescriptionSource,
)
from launch.substitutions import LaunchConfiguration


def _python_launch(package_name, launch_file, launch_arguments=None):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory(package_name),
                'launch',
                launch_file,
            )
        ),
        launch_arguments=launch_arguments.items() if launch_arguments else None,
    )


def generate_launch_description():
    """Generate the canonical Kinematic-ICP Navigation Mode description."""
    loc_pkg_share = get_package_share_directory('mobile_base_localization')
    nav_pkg_share = get_package_share_directory('mobile_base_navigation')

    default_loc_params = os.path.join(
        loc_pkg_share, 'config', 'amcl_params.yaml'
    )
    default_nav_params = os.path.join(
        nav_pkg_share, 'config', 'nav2_params.yaml'
    )
    default_bt_xml = os.path.join(
        nav_pkg_share, 'behavior_trees', 'route_assisted_nav.xml'
    )

    # Declare Launch Arguments
    map_arg = DeclareLaunchArgument(
        'map',
        default_value='',
        description='Full path to map yaml file to load for AMCL localization',
    )
    route_graph_arg = DeclareLaunchArgument(
        'route_graph',
        default_value='',
        description='Full path to the GeoJSON route graph file',
    )
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true',
    )
    autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the localization and navigation lifecycle stacks',
    )
    loc_params_arg = DeclareLaunchArgument(
        'localization_params_file',
        default_value=default_loc_params,
        description='Full path to the AMCL/localization parameter YAML file',
    )
    nav_params_arg = DeclareLaunchArgument(
        'nav2_params_file',
        default_value=default_nav_params,
        description='Full path to the Nav2 parameter YAML file',
    )
    bt_xml_arg = DeclareLaunchArgument(
        'bt_xml',
        default_value=default_bt_xml,
        description='Full path to the behavior tree XML file',
    )
    use_foxglove_arg = DeclareLaunchArgument(
        'use_foxglove',
        default_value='false',
        description='Start Foxglove Bridge for optional visualization',
    )
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level for localization and navigation stacks',
    )

    # Base control hardware arguments
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for M1 motor drivers',
    )
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='230400',
        description='Baud rate for M1 serial communication',
    )
    response_timeout_ms_arg = DeclareLaunchArgument(
        'response_timeout_ms',
        default_value='50',
        description='Response timeout in milliseconds',
    )
    use_mock_hardware_arg = DeclareLaunchArgument(
        'use_mock_hardware',
        default_value='false',
        description='Use mock hardware plugin instead of real M1 hardware',
    )

    lidar_odom_frame_arg = DeclareLaunchArgument(
        'lidar_odom_frame', default_value='odom',
        description='Odometry parent frame ID for Kinematic-ICP',
    )
    publish_odom_tf_arg = DeclareLaunchArgument(
        'publish_odom_tf', default_value='false',
        description='Whether Kinematic-ICP should publish odom TF',
    )
    invert_odom_tf_arg = DeclareLaunchArgument(
        'invert_odom_tf', default_value='false',
        description='Whether Kinematic-ICP should invert published odom TF',
    )
    lidar_topic_arg = DeclareLaunchArgument(
        'lidar_topic', default_value='/scan_front',
        description='Sensor topic for Kinematic-ICP',
    )
    wheel_odom_topic_arg = DeclareLaunchArgument(
        'wheel_odom_topic', default_value='/diff_drive_controller/odom',
        description='Wheel odometry input topic for Kinematic-ICP',
    )

    # Subsystem launches
    base_control = _python_launch(
        'mobile_base_control',
        'base_control.launch.py',
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'use_mock_hardware': LaunchConfiguration('use_mock_hardware'),
            'serial_port': LaunchConfiguration('serial_port'),
            'baud_rate': LaunchConfiguration('baud_rate'),
            'response_timeout_ms': LaunchConfiguration('response_timeout_ms'),
        },
    )
    tdk_imu = _python_launch(
        'mobile_base_perception',
        'tdk_imu.launch.py',
        launch_arguments={
            'params_file': os.path.join(
                get_package_share_directory('mobile_base_perception'),
                'config',
                'tdk_imu.yaml',
            )
        },
    )
    sick_dual_lidar = _python_launch(
        'mobile_base_perception', 'sick_dual_lidar.launch.py'
    )
    dual_laser_merger = _python_launch(
        'mobile_base_perception', 'dual_laser_merger.launch.py'
    )
    kinematic_icp = _python_launch(
        'kinematic_icp', 'kinematic_icp.launch.py',
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': os.path.join(
                get_package_share_directory('kinematic_icp'),
                'config', 'kinematic_icp_ros.yaml',
            ),
            'lidar_odom_frame': LaunchConfiguration('lidar_odom_frame'),
            'publish_odom_tf': LaunchConfiguration('publish_odom_tf'),
            'invert_odom_tf': LaunchConfiguration('invert_odom_tf'),
            'lidar_topic': LaunchConfiguration('lidar_topic'),
            'wheel_odom_topic': LaunchConfiguration('wheel_odom_topic'),
        },
    )
    ekf = _python_launch(
        'mobile_base_state_estimation', 'ekf.launch.py'
    )
    localization = _python_launch(
        'mobile_base_localization',
        'localization.launch.py',
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('localization_params_file'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
            'log_level': LaunchConfiguration('log_level'),
        },
    )
    navigation = _python_launch(
        'mobile_base_navigation',
        'navigation.launch.py',
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
            'params_file': LaunchConfiguration('nav2_params_file'),
            'bt_xml': LaunchConfiguration('bt_xml'),
            'route_graph': LaunchConfiguration('route_graph'),
            'log_level': LaunchConfiguration('log_level'),
        },
    )

    foxglove = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('foxglove_bridge'),
                'launch',
                'foxglove_bridge_launch.xml',
            )
        ),
        condition=IfCondition(LaunchConfiguration('use_foxglove')),
    )

    return LaunchDescription([
        # Arguments
        map_arg,
        route_graph_arg,
        use_sim_time_arg,
        autostart_arg,
        loc_params_arg,
        nav_params_arg,
        bt_xml_arg,
        use_foxglove_arg,
        log_level_arg,
        serial_port_arg,
        baud_rate_arg,
        response_timeout_ms_arg,
        use_mock_hardware_arg,
        lidar_odom_frame_arg,
        publish_odom_tf_arg,
        invert_odom_tf_arg,
        lidar_topic_arg,
        wheel_odom_topic_arg,
        # Subsystems
        base_control,
        tdk_imu,
        sick_dual_lidar,
        dual_laser_merger,
        kinematic_icp,
        ekf,
        localization,
        navigation,
        foxglove,
    ])
