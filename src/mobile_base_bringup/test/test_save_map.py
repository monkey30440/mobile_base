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

"""Behavior test for timestamped map persistence and read-back reuse."""

import os
from pathlib import Path
import subprocess


def test_save_map_uses_timestamped_repository_directory_and_authoritative_contract(tmp_path):
    """Catch wrong output naming, changed saver arguments, or skipped read-back."""
    package_dir = Path(__file__).resolve().parent.parent
    script = package_dir / 'scripts' / 'save_map.sh'

    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    ros2_log = tmp_path / 'ros2.log'
    fake_ros2 = fake_bin / 'ros2'
    fake_ros2.write_text(
        '#!/usr/bin/env bash\n'
        'printf "%s\\n" "$*" >> "$FAKE_ROS2_LOG"\n'
        'if [[ "$1 $2 $3" == "run nav2_map_server map_saver_cli" ]]; then\n'
        '  while [[ $# -gt 0 ]]; do\n'
        '    if [[ "$1" == "-f" ]]; then\n'
        '      touch "$2.yaml" "$2.pgm"\n'
        '      break\n'
        '    fi\n'
        '    shift\n'
        '  done\n'
        'fi\n',
        encoding='utf-8',
    )
    fake_ros2.chmod(0o755)
    fake_date = fake_bin / 'date'
    fake_date.write_text(
        '#!/usr/bin/env bash\n'
        'printf "20260820_143012\\n"\n',
        encoding='utf-8',
    )
    fake_date.chmod(0o755)

    env = os.environ.copy()
    env.update({
        'PATH': f'{fake_bin}:{env["PATH"]}',
        'FAKE_ROS2_LOG': str(ros2_log),
        'MOBILE_BASE_REPOSITORY_ROOT': str(tmp_path / 'repository'),
    })
    result = subprocess.run(
        ['bash', str(script)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    output_dir = tmp_path / 'repository' / 'maps' / '20260820_143012'
    assert (output_dir / 'map.yaml').is_file()
    assert (output_dir / 'map.pgm').is_file()
    assert str(output_dir) in result.stdout

    calls = ros2_log.read_text(encoding='utf-8').splitlines()
    assert calls == [
        f'run nav2_map_server map_saver_cli -t /map -f {output_dir}/map '
        '--fmt pgm --mode trinary --occ 0.65 --free 0.25 --ros-args '
        '-p map_subscribe_transient_local:=true -p save_map_timeout:=10.0',
        f'run mobile_base_mapping validate_map_readback {output_dir}/map.yaml',
    ]
