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

import importlib.util
from pathlib import Path

from launch.actions import IncludeLaunchDescription


LAUNCH_FILE = Path(__file__).parents[1] / 'launch' / 'base_control.launch.py'


def load_launch_module():
    spec = importlib.util.spec_from_file_location('base_control_launch', LAUNCH_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_does_not_require_or_forward_a_ros_position_scale(monkeypatch, tmp_path):
    module = load_launch_module()
    monkeypatch.setattr(
        module, 'get_package_share_directory', lambda package: str(tmp_path / package)
    )
    description = module.generate_launch_description()
    includes = [a for a in description.entities if isinstance(a, IncludeLaunchDescription)]
    assert len(includes) == 1
    arguments = dict(includes[0].launch_arguments)
    assert 'response_timeout_ms' in arguments
    assert 'motor_steps_per_rev' not in arguments
