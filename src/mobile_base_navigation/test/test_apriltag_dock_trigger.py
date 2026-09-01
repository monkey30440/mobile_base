# Copyright 2026 mobile_base developer
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
import subprocess
import time

from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion
from nav2_msgs.action import DockRobot
import pytest
import rclpy
from rclpy.action import ActionServer, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Header
from std_srvs.srv import Trigger


class MockDockRobotActionServer(Node):

    def __init__(self, node_name='mock_dock_robot_server'):
        super().__init__(node_name)
        self.cb_group = ReentrantCallbackGroup()
        self._action_server = ActionServer(
            self,
            DockRobot,
            '/dock_robot',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            callback_group=self.cb_group,
        )
        self.received_goals = []
        self.should_succeed = True
        self.error_code = 0
        self.error_msg = ''
        self.execution_delay_sec = 0.0

    def goal_callback(self, goal_request):
        self.received_goals.append(goal_request)
        return GoalResponse.ACCEPT

    def execute_callback(self, goal_handle):
        if self.execution_delay_sec > 0.0:
            time.sleep(self.execution_delay_sec)
        result = DockRobot.Result()
        if self.should_succeed:
            goal_handle.succeed()
            result.success = True
            result.error_code = 0
            result.error_msg = ''
        else:
            goal_handle.abort()
            result.success = False
            result.error_code = self.error_code
            result.error_msg = self.error_msg
        return result


def find_executable():
    install_exe = os.path.join(
        os.path.dirname(__file__),
        '../../../install/mobile_base_navigation/lib/'
        'mobile_base_navigation/apriltag_dock_trigger',
    )
    build_exe = os.path.join(
        os.path.dirname(__file__),
        '../../../build/mobile_base_navigation/apriltag_dock_trigger',
    )
    paths = [install_exe, build_exe]
    for p in paths:
        if os.path.exists(p):
            return p
    return 'apriltag_dock_trigger'


@pytest.fixture(scope='module')
def rclpy_init():
    rclpy.init()
    yield
    rclpy.shutdown()


def test_trigger_no_cached_pose(rclpy_init):
    exe = find_executable()
    proc = subprocess.Popen([exe])
    node = Node('test_client_no_pose')
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)

    try:
        time.sleep(1.0)
        client = node.create_client(Trigger, '/apriltag_dock')
        assert client.wait_for_service(timeout_sec=3.0)

        future = client.call_async(Trigger.Request())
        start_time = time.time()
        while not future.done() and time.time() - start_time < 3.0:
            executor.spin_once(timeout_sec=0.1)

        assert future.done()
        res = future.result()
        assert res.success is False
        assert 'No detected dock pose received yet' in res.message
    finally:
        proc.terminate()
        proc.wait(timeout=3)
        node.destroy_node()


def test_trigger_goal_forwarding_and_success(rclpy_init):
    exe = find_executable()
    proc = subprocess.Popen([exe])
    mock_server = MockDockRobotActionServer('mock_server_success')
    test_node = Node('test_client_success')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(mock_server)
    executor.add_node(test_node)

    try:
        time.sleep(1.0)
        pose_pub = test_node.create_publisher(
            PoseStamped, '/detected_dock_pose', 10
        )
        client = test_node.create_client(Trigger, '/apriltag_dock')
        assert client.wait_for_service(timeout_sec=3.0)

        # Publish specific pose
        pose_msg = PoseStamped(
            header=Header(frame_id='base_link'),
            pose=Pose(
                position=Point(x=1.23, y=0.45, z=0.0),
                orientation=Quaternion(x=0.0, y=0.0, z=0.707, w=0.707),
            ),
        )
        pose_msg.header.stamp.sec = 123
        pose_msg.header.stamp.nanosec = 456

        for _ in range(5):
            pose_pub.publish(pose_msg)
            executor.spin_once(timeout_sec=0.05)
            time.sleep(0.05)

        # Call service
        mock_server.should_succeed = True
        future = client.call_async(Trigger.Request())

        start_time = time.time()
        while not future.done() and time.time() - start_time < 5.0:
            executor.spin_once(timeout_sec=0.1)

        assert future.done(), 'Service call timed out'
        res = future.result()
        assert res.success is True
        assert 'Docking succeeded' in res.message

        # Assert received goal in mock server
        assert len(mock_server.received_goals) == 1
        goal = mock_server.received_goals[0]
        assert goal.use_dock_id is False
        assert goal.dock_id == ''
        assert goal.dock_type == 'apriltag_dock'
        assert goal.navigate_to_staging_pose is False
        assert goal.dock_pose.header.frame_id == 'base_link'
        assert goal.dock_pose.header.stamp.sec == 123
        assert goal.dock_pose.header.stamp.nanosec == 456
        assert abs(goal.dock_pose.pose.position.x - 1.23) < 1e-4
        assert abs(goal.dock_pose.pose.position.y - 0.45) < 1e-4
        assert abs(goal.dock_pose.pose.orientation.z - 0.707) < 1e-4
        assert abs(goal.dock_pose.pose.orientation.w - 0.707) < 1e-4

    finally:
        proc.terminate()
        proc.wait(timeout=3)
        mock_server.destroy_node()
        test_node.destroy_node()


def test_trigger_failure_aborted_mapping(rclpy_init):
    exe = find_executable()
    proc = subprocess.Popen([exe])
    mock_server = MockDockRobotActionServer('mock_server_aborted')
    mock_server.should_succeed = False
    mock_server.error_code = 904  # FAILED_TO_DETECT_DOCK
    mock_server.error_msg = 'Camera lost visual tag'

    test_node = Node('test_client_aborted')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(mock_server)
    executor.add_node(test_node)

    try:
        time.sleep(1.0)
        pose_pub = test_node.create_publisher(
            PoseStamped, '/detected_dock_pose', 10
        )
        client = test_node.create_client(Trigger, '/apriltag_dock')
        assert client.wait_for_service(timeout_sec=3.0)

        pose_msg = PoseStamped(
            header=Header(frame_id='base_link'),
            pose=Pose(position=Point(x=0.5, y=0.0, z=0.0)),
        )
        for _ in range(5):
            pose_pub.publish(pose_msg)
            executor.spin_once(timeout_sec=0.05)
            time.sleep(0.05)

        future = client.call_async(Trigger.Request())
        start_time = time.time()
        while not future.done() and time.time() - start_time < 5.0:
            executor.spin_once(timeout_sec=0.1)

        assert future.done()
        res = future.result()
        assert res.success is False
        assert 'Docking aborted' in res.message
        assert '904' in res.message
        assert 'Camera lost visual tag' in res.message

    finally:
        proc.terminate()
        proc.wait(timeout=3)
        mock_server.destroy_node()
        test_node.destroy_node()


def test_trigger_server_unavailable(rclpy_init):
    exe = find_executable()
    proc = subprocess.Popen([exe])
    test_node = Node('test_client_unavailable')
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(test_node)

    try:
        time.sleep(1.0)
        pose_pub = test_node.create_publisher(
            PoseStamped, '/detected_dock_pose', 10
        )
        client = test_node.create_client(Trigger, '/apriltag_dock')
        assert client.wait_for_service(timeout_sec=3.0)

        pose_msg = PoseStamped(
            header=Header(frame_id='base_link'),
            pose=Pose(position=Point(x=0.5, y=0.0, z=0.0)),
        )
        for _ in range(5):
            pose_pub.publish(pose_msg)
            executor.spin_once(timeout_sec=0.05)
            time.sleep(0.05)

        # No mock action server running
        future = client.call_async(Trigger.Request())
        start_time = time.time()
        while not future.done() and time.time() - start_time < 5.0:
            executor.spin_once(timeout_sec=0.1)

        assert future.done()
        res = future.result()
        assert res.success is False
        assert (
            'DockRobot action server unavailable' in res.message
            or 'Timeout waiting for DockRobot goal response' in res.message
        )

    finally:
        proc.terminate()
        proc.wait(timeout=3)
        test_node.destroy_node()


def test_concurrency_no_deadlock(rclpy_init):
    """Verify synchronous service waiting does not deadlock the executor."""
    exe = find_executable()
    proc = subprocess.Popen([exe])
    mock_server = MockDockRobotActionServer('mock_server_concurrency')
    mock_server.should_succeed = True
    mock_server.execution_delay_sec = 0.3

    test_node = Node('test_client_concurrency')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(mock_server)
    executor.add_node(test_node)

    try:
        time.sleep(1.0)
        pose_pub = test_node.create_publisher(
            PoseStamped, '/detected_dock_pose', 10
        )
        client = test_node.create_client(Trigger, '/apriltag_dock')
        assert client.wait_for_service(timeout_sec=3.0)

        pose_msg = PoseStamped(
            header=Header(frame_id='base_link'),
            pose=Pose(position=Point(x=0.5, y=0.0, z=0.0)),
        )
        for _ in range(5):
            pose_pub.publish(pose_msg)
            executor.spin_once(timeout_sec=0.05)
            time.sleep(0.05)

        # Service call must complete cleanly without deadlocking
        future = client.call_async(Trigger.Request())

        start_time = time.time()
        while not future.done() and time.time() - start_time < 5.0:
            executor.spin_once(timeout_sec=0.1)

        assert future.done(), 'Executor deadlocked during synchronous action waiting!'
        res = future.result()
        assert res.success is True
        assert 'Docking succeeded' in res.message

    finally:
        proc.terminate()
        proc.wait(timeout=3)
        mock_server.destroy_node()
        test_node.destroy_node()
