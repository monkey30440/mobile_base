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

"""Integration test simulating Upper Body interaction with native Nav2 docking_server."""

import os
import shutil
import subprocess
import tempfile
import threading
import time

from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import PoseStamped, TransformStamped, TwistStamped
from lifecycle_msgs.msg import State, Transition
from lifecycle_msgs.srv import ChangeState, GetState
from nav2_msgs.action import DockRobot
import pytest
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
import tf2_ros
import yaml


def _find_docking_server_executable():
    """Find the installed opennav_docking binary."""
    try:
        pkg_prefix = get_package_prefix('opennav_docking')
        candidate = os.path.join(pkg_prefix, 'lib', 'opennav_docking', 'opennav_docking')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    except Exception:
        pass

    which_path = shutil.which('opennav_docking')
    if which_path and os.access(which_path, os.X_OK):
        return which_path

    raise RuntimeError('opennav_docking executable not found in ROS 2 environment')


def _create_minimal_docking_config(tmp_dir: str) -> str:
    """Create a minimal, safe parameter configuration for docking_server."""
    config = {
        'docking_server': {
            'ros__parameters': {
                'use_sim_time': False,
                'controller_frequency': 20.0,
                'initial_perception_timeout': 5.0,
                'dock_approach_timeout': 30.0,
                'max_retries': 0,
                'base_frame': 'base_link',
                'fixed_frame': 'odom',
                'dock_backwards': False,
                'enable_stamped_cmd_vel': True,
                'dock_plugins': ['apriltag_dock'],
                'apriltag_dock': {
                    'plugin': 'opennav_docking::SimpleNonChargingDock',
                    'docking_threshold': 0.05,
                    'use_external_detection_pose': True,
                    'use_stall_detection': False,
                    'external_detection_timeout': 2.0,
                    'external_detection_translation_x': -0.7,
                    'external_detection_translation_y': 0.0,
                    'external_detection_rotation_roll': 0.0,
                    'external_detection_rotation_pitch': 0.0,
                    'external_detection_rotation_yaw': 0.0,
                    'filter_coef': 0.1,
                },
                'controller': {
                    'k_phi': 3.0,
                    'k_delta': 2.0,
                    'v_linear_min': 0.05,
                    'v_linear_max': 0.15,
                    'v_angular_max': 0.5,
                    'slowdown_radius': 0.25,
                    'use_collision_detection': False,
                },
            }
        }
    }
    cfg_path = os.path.join(tmp_dir, 'docking_test_params.yaml')
    with open(cfg_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
    return cfg_path


def test_native_apriltag_docking_integration():
    """Verify Upper Body contract with real Nav2 docking_server: Accepted -> Feedback -> Canceled."""
    tmp_dir = tempfile.mkdtemp(prefix='docking_test_')
    proc = None
    node = None
    executor = None
    executor_thread = None
    goal_handle = None
    timer = None

    try:
        # 1. Prepare minimal params & start real docking_server
        exe = _find_docking_server_executable()
        param_file = _create_minimal_docking_config(tmp_dir)

        # Strictly remap cmd_vel away from production /diff_drive_controller/cmd_vel
        cmd = [
            exe,
            '--ros-args',
            '--params-file',
            param_file,
            '-r',
            '/cmd_vel:=/test/docking_cmd_vel',
            '-r',
            'cmd_vel:=/test/docking_cmd_vel',
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 2. Initialize rclpy & Fake Upper node
        rclpy.init()
        node = rclpy.create_node('test_fake_upper_body')
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(node)

        executor_thread = threading.Thread(target=executor.spin, daemon=True)
        executor_thread.start()

        # 3. Lifecycle Transition: UNCONFIGURED -> INACTIVE -> ACTIVE
        change_state_client = node.create_client(
            ChangeState, '/docking_server/change_state'
        )
        assert change_state_client.wait_for_service(timeout_sec=5.0), (
            '/docking_server/change_state service not available'
        )

        # Transition to CONFIGURE
        req_configure = ChangeState.Request()
        req_configure.transition.id = Transition.TRANSITION_CONFIGURE
        future = change_state_client.call_async(req_configure)
        _wait_future_or_fail(future, timeout_sec=5.0, msg='Lifecycle CONFIGURE timed out')
        assert future.result().success, 'Lifecycle CONFIGURE transition failed'

        # Transition to ACTIVATE
        req_activate = ChangeState.Request()
        req_activate.transition.id = Transition.TRANSITION_ACTIVATE
        future = change_state_client.call_async(req_activate)
        _wait_future_or_fail(future, timeout_sec=5.0, msg='Lifecycle ACTIVATE timed out')
        assert future.result().success, 'Lifecycle ACTIVATE transition failed'

        # Verify State is ACTIVE
        get_state_client = node.create_client(GetState, '/docking_server/get_state')
        assert get_state_client.wait_for_service(timeout_sec=3.0)
        future = get_state_client.call_async(GetState.Request())
        _wait_future_or_fail(future, timeout_sec=3.0, msg='Lifecycle GetState timed out')
        assert future.result().current_state.id == State.PRIMARY_STATE_ACTIVE, (
            f'Expected ACTIVE state ({State.PRIMARY_STATE_ACTIVE}), '
            f'got {future.result().current_state.id}'
        )

        # 4. Publish Fake TF: odom -> base_footprint -> base_link (production topology)
        tf_broadcaster = tf2_ros.StaticTransformBroadcaster(node)
        now_msg = node.get_clock().now().to_msg()

        tf_odom_footprint = TransformStamped()
        tf_odom_footprint.header.stamp = now_msg
        tf_odom_footprint.header.frame_id = 'odom'
        tf_odom_footprint.child_frame_id = 'base_footprint'
        tf_odom_footprint.transform.translation.x = 0.0
        tf_odom_footprint.transform.translation.y = 0.0
        tf_odom_footprint.transform.translation.z = 0.0
        tf_odom_footprint.transform.rotation.x = 0.0
        tf_odom_footprint.transform.rotation.y = 0.0
        tf_odom_footprint.transform.rotation.z = 0.0
        tf_odom_footprint.transform.rotation.w = 1.0

        tf_footprint_base_link = TransformStamped()
        tf_footprint_base_link.header.stamp = now_msg
        tf_footprint_base_link.header.frame_id = 'base_footprint'
        tf_footprint_base_link.child_frame_id = 'base_link'
        tf_footprint_base_link.transform.translation.x = 0.0
        tf_footprint_base_link.transform.translation.y = 0.0
        tf_footprint_base_link.transform.translation.z = 0.2560
        tf_footprint_base_link.transform.rotation.x = 0.0
        tf_footprint_base_link.transform.rotation.y = 0.0
        tf_footprint_base_link.transform.rotation.z = 0.0
        tf_footprint_base_link.transform.rotation.w = 1.0

        tf_broadcaster.sendTransform([tf_odom_footprint, tf_footprint_base_link])

        # 5. Fake Upper continuously publishes fresh /detected_dock_pose at 10 Hz
        pose_pub = node.create_publisher(PoseStamped, '/detected_dock_pose', 10)

        def publish_dock_pose():
            msg = PoseStamped()
            msg.header.frame_id = 'base_link'
            msg.header.stamp = node.get_clock().now().to_msg()
            msg.pose.position.x = 1.5
            msg.pose.position.y = 0.0
            msg.pose.position.z = 0.0
            msg.pose.orientation.x = 0.0
            msg.pose.orientation.y = 0.0
            msg.pose.orientation.z = 0.0
            msg.pose.orientation.w = 1.0
            pose_pub.publish(msg)

        timer = node.create_timer(0.1, publish_dock_pose)

        # Capture remapped test cmd_vel
        captured_cmd_vels = []
        node.create_subscription(
            TwistStamped,
            '/test/docking_cmd_vel',
            lambda msg: captured_cmd_vels.append(msg),
            10,
        )

        # Allow brief grace period for TF and initial pose publication
        time.sleep(0.3)

        # 6. Create DockRobot Action Client & wait for server
        action_client = ActionClient(node, DockRobot, '/dock_robot')
        assert action_client.wait_for_server(timeout_sec=5.0), (
            '/dock_robot action server not available'
        )

        # 7. Construct and send Direct DockRobot Goal
        goal_msg = DockRobot.Goal()
        goal_msg.use_dock_id = False
        goal_msg.dock_id = ''
        goal_msg.dock_type = 'apriltag_dock'
        goal_msg.navigate_to_staging_pose = False
        goal_msg.max_staging_time = 0.0
        goal_msg.dock_pose.header.frame_id = 'base_link'
        goal_msg.dock_pose.header.stamp = node.get_clock().now().to_msg()
        goal_msg.dock_pose.pose.position.x = 1.5
        goal_msg.dock_pose.pose.position.y = 0.0
        goal_msg.dock_pose.pose.position.z = 0.0
        goal_msg.dock_pose.pose.orientation.w = 1.0

        received_feedbacks = []
        feedback_event = threading.Event()

        def feedback_cb(feedback_msg):
            received_feedbacks.append(feedback_msg.feedback)
            feedback_event.set()

        send_goal_future = action_client.send_goal_async(
            goal_msg, feedback_callback=feedback_cb
        )
        _wait_future_or_fail(
            send_goal_future, timeout_sec=5.0, msg='Send goal timed out'
        )
        goal_handle = send_goal_future.result()
        assert goal_handle.accepted, 'DockRobot goal was rejected by docking_server'

        # 8. Wait for at least one native feedback
        feedback_received = feedback_event.wait(timeout=5.0)
        assert feedback_received, 'No native DockRobot feedback received within timeout'
        assert len(received_feedbacks) >= 1, 'Expected at least 1 feedback'

        # 9. Immediately send Action Cancel
        cancel_future = goal_handle.cancel_goal_async()
        _wait_future_or_fail(
            cancel_future, timeout_sec=5.0, msg='Cancel goal request timed out'
        )
        cancel_res = cancel_future.result()
        assert cancel_res.return_code == 0 or len(cancel_res.goals_canceling) > 0, (
            f'Cancel request not accepted by server (code={cancel_res.return_code})'
        )

        # 10. Wait for terminal result and assert STATUS_CANCELED
        result_future = goal_handle.get_result_async()
        _wait_future_or_fail(
            result_future, timeout_sec=5.0, msg='Wait for canceled result timed out'
        )
        wrapped_result = result_future.result()
        assert wrapped_result.status == GoalStatus.STATUS_CANCELED, (
            f'Expected terminal status STATUS_CANCELED ({GoalStatus.STATUS_CANCELED}), '
            f'got {wrapped_result.status}'
        )

    finally:
        # Graceful cleanup
        if timer is not None:
            timer.cancel()
        if executor is not None:
            executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        if executor_thread is not None and executor_thread.is_alive():
            executor_thread.join(timeout=2.0)

        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)

        shutil.rmtree(tmp_dir, ignore_errors=True)


def _wait_future_or_fail(future, timeout_sec: float, msg: str):
    """Poll future until complete or raise AssertionError upon timeout."""
    start = time.time()
    while not future.done() and (time.time() - start) < timeout_sec:
        time.sleep(0.02)
    assert future.done(), f'{msg} (exceeded {timeout_sec}s)'
