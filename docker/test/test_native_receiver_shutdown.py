"""Native initialization/shutdown regression; debugger is a test dependency."""
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess

from ament_index_python.packages import get_package_prefix, get_package_share_directory
import pytest


@pytest.mark.skipif(
    platform.machine() != 'aarch64' or shutil.which('gdb') is None,
    reason='Requires AArch64 GDB for the observed native ABI scheduling seam',
)
def test_stop_before_receiver_initialization_exits_without_null_fifo_access():
    fixture = Path(__file__).with_name('stop_during_receiver_init.gdb.py')
    prefix = Path(get_package_prefix('sick_scan_xd'))
    share = Path(get_package_share_directory('sick_scan_xd'))
    command = [
        'gdb', '--batch', '--return-child-result',
        '-ex', 'handle SIGINT nostop noprint pass',
        '-ex', f'source {fixture}', '-ex', 'run',
        '-ex', 'thread apply all bt', '--args',
        str(prefix / 'lib/sick_scan_xd/sick_generic_caller'),
        str(share / 'launch/sick_picoscan.launch'),
        'hostname:=127.0.0.2', 'udp_receiver_ip:=127.0.0.1',
        'udp_port:=32115', 'check_udp_receiver_port:=32117',
        'tf_publish_rate:=0.0', 'listen_only_mode:=1', 'imu_enable:=0',
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env={**os.environ, 'ROS_DOMAIN_ID': '94'}, start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        raise AssertionError('Native shutdown did not finish:\n' + output)
    assert 'INJECT STOP BEFORE UDP RECEIVER INITIALIZATION' in output, output
    assert process.returncode == 0, output
    assert 'received signal SIGSEGV' not in output, output
    assert 'sick_scansegment_xd::runThreadCb() finished' in output, output
