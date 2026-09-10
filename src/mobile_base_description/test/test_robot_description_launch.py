#!/usr/bin/env python3
# Copyright 2026 Jim Chen
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

import os
import time
import unittest

from ament_index_python.packages import get_package_share_directory
import launch
import launch_testing
import launch_testing.actions
import pytest
import rclpy
import std_msgs.msg
import tf2_msgs.msg


@pytest.mark.launch_test
def generate_test_description():
    pkg_share = get_package_share_directory('mobile_base_description')
    launch_file = os.path.join(pkg_share, 'launch', 'robot_description.launch.py')

    robot_description_launch = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(launch_file),
        launch_arguments={
            'use_mock_hardware': 'true',
            'response_timeout_ms': '50',
        }.items(),
    )

    return (
        launch.LaunchDescription([
            robot_description_launch,
            launch_testing.actions.ReadyToTest(),
        ]),
        {'robot_description_launch': robot_description_launch},
    )


class TestRobotDescriptionPublication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def setUp(self):
        self.node = rclpy.create_node('test_robot_description_listener')
        self.sub_desc = None
        self.sub_tf_static = None

    def tearDown(self):
        self.node.destroy_node()

    def test_robot_description_and_tf_static(self):
        """Test that robot_description string and tf_static transforms are published."""
        received_description = []
        received_tf_static = []

        def desc_cb(msg):
            received_description.append(msg.data)

        def tf_static_cb(msg):
            for transform in msg.transforms:
                received_tf_static.append((
                    transform.header.frame_id,
                    transform.child_frame_id,
                ))

        self.sub_desc = self.node.create_subscription(
            std_msgs.msg.String,
            '/robot_description',
            desc_cb,
            rclpy.qos.QoSProfile(
                depth=1,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            ),
        )

        self.sub_tf_static = self.node.create_subscription(
            tf2_msgs.msg.TFMessage,
            '/tf_static',
            tf_static_cb,
            rclpy.qos.QoSProfile(
                depth=10,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            ),
        )

        # Spin node for up to 5 seconds waiting for publications
        required_frames = {
            'base_link',
            'base_lidar_link_FL',
            'base_lidar_link_FL_1',
            'base_lidar_link_BR',
            'base_lidar_link_BR_1',
            'base_imu_link',
        }
        start_time = time.time()
        while time.time() - start_time < 5.0:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            received_child_frames = {child for _, child in received_tf_static}
            if received_description and required_frames.issubset(received_child_frames):
                break

        # Verify /robot_description content
        self.assertTrue(len(received_description) > 0, 'No /robot_description received')
        self.assertIn('mobile_base', received_description[0])
        self.assertIn('base_footprint', received_description[0])
        self.assertIn('driving_wheel_joint_L', received_description[0])

        # Verify /tf_static transforms
        child_frames = [child for _, child in received_tf_static]
        self.assertIn('base_link', child_frames, 'Missing base_link in /tf_static')
        self.assertIn(
            'base_lidar_link_FL', child_frames, 'Missing base_lidar_link_FL in /tf_static'
        )
        self.assertIn(
            'base_lidar_link_FL_1', child_frames, 'Missing base_lidar_link_FL_1 in /tf_static'
        )
        self.assertIn(
            'base_lidar_link_BR', child_frames, 'Missing base_lidar_link_BR in /tf_static'
        )
        self.assertIn(
            'base_lidar_link_BR_1', child_frames, 'Missing base_lidar_link_BR_1 in /tf_static'
        )
        self.assertIn('base_imu_link', child_frames, 'Missing base_imu_link in /tf_static')
