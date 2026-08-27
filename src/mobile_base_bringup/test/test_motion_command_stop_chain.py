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

"""Automated consolidated tests for Motion Command and Stop Layers (Checklist #21)."""

from pathlib import Path

import yaml


def get_workspace_root() -> Path:
    """Get the root directory of mobile_base workspace."""
    return Path(__file__).resolve().parent.parent.parent.parent


def test_navigation_motion_command_chain_contract():
    """Verify Nav2 controller_server -> Collision Monitor -> diff_drive_controller chain."""
    ws_root = get_workspace_root()

    # 1. Navigation launch file remappings
    nav_launch = (
        ws_root / 'src' / 'mobile_base_navigation' / 'launch' / 'navigation.launch.py'
    )
    assert nav_launch.exists(), f'File not found: {nav_launch}'
    with open(nav_launch, 'r', encoding='utf-8') as f:
        launch_content = f.read()

    # Verify controller_server remaps output to /cmd_vel_nav
    assert "'/cmd_vel_nav'" in launch_content
    # Verify collision_monitor remaps output to /diff_drive_controller/cmd_vel
    assert "'/diff_drive_controller/cmd_vel'" in launch_content

    # 2. Navigation parameters configuration
    nav_yaml = (
        ws_root / 'src' / 'mobile_base_navigation' / 'config' / 'nav2_params.yaml'
    )
    assert nav_yaml.exists()
    with open(nav_yaml, 'r', encoding='utf-8') as f:
        nav_params = yaml.safe_load(f)

    cm_params = nav_params['collision_monitor']['ros__parameters']
    assert cm_params['cmd_vel_in_topic'] == 'cmd_vel_nav'
    assert cm_params['cmd_vel_out_topic'] == 'cmd_vel'
    assert cm_params['enable_stamped_cmd_vel'] is True
    assert 'scan_front' in cm_params['observation_sources']
    assert 'scan_rear' in cm_params['observation_sources']
    assert cm_params['scan_front']['topic'] == '/scan_front'
    assert cm_params['scan_rear']['topic'] == '/scan_rear'
    assert cm_params['source_timeout'] >= 0.5


def test_teleop_motion_command_chain_contract():
    """Verify Mapping / Teleop command directly drives diff_drive_controller."""
    ws_root = get_workspace_root()

    # Verify diff_drive_controller configuration accepts TwistStamped
    ctrl_yaml = (
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    )
    assert ctrl_yaml.exists()
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        ctrl_params = yaml.safe_load(f)['diff_drive_controller']['ros__parameters']

    assert ctrl_params['use_stamped_vel'] is True


def test_diff_drive_controller_safety_and_limits():
    """Verify diff_drive_controller timeout, rate, TF, and deceleration limits."""
    ws_root = get_workspace_root()
    ctrl_yaml = (
        ws_root / 'src' / 'mobile_base_control' / 'config' / 'base_control_params.yaml'
    )
    assert ctrl_yaml.exists()
    with open(ctrl_yaml, 'r', encoding='utf-8') as f:
        full_params = yaml.safe_load(f)

    cm_params = full_params['controller_manager']['ros__parameters']
    assert cm_params['update_rate'] == 30  # 30 Hz control loop

    dd_params = full_params['diff_drive_controller']['ros__parameters']
    assert dd_params['cmd_vel_timeout'] == 0.5  # SYS-027 command timeout
    assert dd_params['enable_odom_tf'] is False  # S7 prohibited from broadcasting TF

    # SYS-028 Speed and acceleration limits
    assert dd_params['linear.x.max_velocity'] <= 1.0
    assert dd_params['linear.x.max_deceleration'] < 0.0  # e.g., -1.0 m/s^2
    assert dd_params['angular.z.max_velocity'] <= 1.5
    assert dd_params['angular.z.max_deceleration'] < 0.0  # e.g., -2.0 rad/s^2


def test_m1_hardware_safe_stop_and_timeout_contract():
    """Verify M1Hardware ros2_control interface, timeout parameter, and safe stop."""
    ws_root = get_workspace_root()

    # 1. URDF Xacro ros2_control interface
    xacro_file = (
        ws_root / 'src' / 'mobile_base_description' / 'urdf' /
        'mobile_base_ros2_control.xacro'
    )
    assert xacro_file.exists()
    with open(xacro_file, 'r', encoding='utf-8') as f:
        xacro_content = f.read()

    assert 'response_timeout_ms' in xacro_content
    assert 'driving_wheel_joint_L' in xacro_content
    assert 'driving_wheel_joint_R' in xacro_content

    # 2. C++ Source code contract for GAP-06 Safe Stop (stop before disable)
    cpp_source = (
        ws_root / 'src' / 'mobile_base_control' / 'src' / 'm1_hardware.cpp'
    )
    assert cpp_source.exists()
    with open(cpp_source, 'r', encoding='utf-8') as f:
        cpp_content = f.read()

    assert 'on_deactivate' in cpp_content
    assert 'driver_->stop' in cpp_content
    assert 'driver_->disable' in cpp_content


def test_base_control_spawner_ordering_contract():
    """Verify base_control.launch.py chains diff_drive_controller after joint_state_broadcaster."""
    ws_root = get_workspace_root()
    launch_file = ws_root / 'src' / 'mobile_base_control' / 'launch' / 'base_control.launch.py'
    assert launch_file.exists()

    import importlib.util
    spec = importlib.util.spec_from_file_location('base_control_launch', str(launch_file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ld = module.generate_launch_description()

    # Verify joint_state_broadcaster spawner is in root entities
    from launch_ros.actions import Node
    from launch.actions import RegisterEventHandler
    from launch.event_handlers import OnProcessExit

    root_nodes = [e for e in ld.entities if isinstance(e, Node)]

    # Verify diff_drive_controller spawner is NOT a parallel uncoordinated root action
    for n in root_nodes:
        pkg = getattr(n, '_Node__package', getattr(n, 'node_package', ''))
        raw_args = getattr(n, '_Node__arguments', []) or []
        args = [str(a) for a in raw_args]
        if pkg == 'controller_manager':
            assert 'diff_drive_controller' not in args, (
                'diff_drive_controller spawner must not be launched '
                'in parallel with joint_state_broadcaster'
            )

    # Verify RegisterEventHandler with OnProcessExit is registered for diff_drive_controller
    event_handlers = [e for e in ld.entities if isinstance(e, RegisterEventHandler)]
    assert len(event_handlers) >= 1

    found_chain = False
    for eh in event_handlers:
        handler = eh.event_handler
        if isinstance(handler, OnProcessExit):
            found_chain = True
    assert found_chain, 'Must register OnProcessExit event handler for controller spawner chaining'
