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

import pytest


LAUNCH_FILE = Path(__file__).parents[1] / 'launch' / 'base_control.launch.py'
PARAMS_FILE = Path(__file__).parents[1] / 'config' / 'base_control_params.yaml'


def load_launch_module():
    spec = importlib.util.spec_from_file_location('base_control_launch', LAUNCH_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_loads_firmware_motor_steps_per_rev_from_control_config():
    module = load_launch_module()

    assert module.load_motor_steps_per_rev(PARAMS_FILE) == '65535.0'


def test_rejects_non_positive_motor_steps_per_rev(tmp_path):
    params_file = tmp_path / 'invalid_params.yaml'
    params_file.write_text(
        'mobile_base_hardware:\n'
        '  ros__parameters:\n'
        '    motor_steps_per_rev: 0\n'
    )
    module = load_launch_module()

    with pytest.raises(RuntimeError, match='motor_steps_per_rev must be positive'):
        module.load_motor_steps_per_rev(params_file)
