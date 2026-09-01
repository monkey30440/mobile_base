# Copyright 2026 FIH
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

"""Contract tests for the AMR-side Fluent Bit logs pipeline."""

import importlib.util
from pathlib import Path
import runpy

from launch import LaunchDescription
from launch.actions import ExecuteProcess
import setuptools


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PACKAGE_ROOT / 'config' / 'fluent-bit.conf'
LAUNCH_PATH = PACKAGE_ROOT / 'launch' / 'fluent_bit.launch.py'


def _config_text():
    return CONFIG_PATH.read_text(encoding='utf-8')


def _load_launch_module():
    spec = importlib.util.spec_from_file_location(
        'mobile_base_observability_fluent_bit_launch', LAUNCH_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_installs_fluent_bit_config_to_package_share(monkeypatch):
    """Dropping the config data_files entry must fail this packaging test."""
    captured = {}
    monkeypatch.setattr(setuptools, 'setup', lambda **kwargs: captured.update(kwargs))

    monkeypatch.chdir(PACKAGE_ROOT)
    runpy.run_path(str(PACKAGE_ROOT / 'setup.py'), run_name='__main__')

    config_entries = [
        files
        for destination, files in captured['data_files']
        if destination == 'share/mobile_base_observability/config'
    ]
    assert config_entries == [['config/fluent-bit.conf']]


def test_fluent_bit_config_is_volatile_bounded_and_tails_launch_logs():
    """Removing any required loss-bounded Tail setting must fail this test."""
    config = _config_text()

    assert 'Path              /root/.ros/log/*/launch.log' in config
    assert 'Read_from_Head    false' in config
    assert 'storage.type      memrb' in config
    assert 'Mem_Buf_Limit     32M' in config
    assert 'DB ' not in config
    assert 'storage.path' not in config
    assert 'filesystem' not in config


def test_fluent_bit_config_uses_only_environment_for_opensearch_identity():
    """Hardcoding deployment identity or credentials must fail this test."""
    config = _config_text()
    required_references = {
        '${MOBILE_BASE_OPENSEARCH_HOST}',
        '${MOBILE_BASE_OPENSEARCH_PORT}',
        '${MOBILE_BASE_OPENSEARCH_TLS}',
        '${MOBILE_BASE_OPENSEARCH_USERNAME}',
        '${MOBILE_BASE_OPENSEARCH_PASSWORD}',
        '${MOBILE_BASE_ROBOT_ID}',
    }

    assert required_references.issubset(set(config.split()))
    assert 'Record            source ros_launch_log' in config
    assert 'amr01' not in config


def test_fluent_bit_launch_starts_only_an_independent_process(monkeypatch):
    """Adding ROS nodes or lifecycle integration must fail this test."""
    module = _load_launch_module()
    monkeypatch.setattr(
        module,
        'get_package_share_directory',
        lambda package: f'/opt/ros/share/{package}',
    )
    description = module.generate_launch_description()

    assert isinstance(description, LaunchDescription)
    assert len(description.entities) == 1
    process = description.entities[0]
    assert isinstance(process, ExecuteProcess)
    assert process.cmd[0][0].text == '/opt/fluent-bit/bin/fluent-bit'
    assert process.cmd[1][0].text == '-c'
