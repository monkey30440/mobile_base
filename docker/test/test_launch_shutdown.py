"""Regression at the real launch/asyncio signal scheduling boundary."""
import os
from pathlib import Path
import signal
import subprocess

import pytest


@pytest.mark.parametrize('handler', ['default', 'custom'])
def test_sigint_during_event_task_wakeup_does_not_lose_shutdown(handler):
    fixture = Path(__file__).with_name('launch_interrupt_fixture.py')
    process = subprocess.Popen(
        ['python3', str(fixture), handler], stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=4)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        raise AssertionError('Shutdown event was not consumed:\n' + output)
    assert process.returncode == 0, output
    assert 'INJECT SIGINT AT EVENT TASK WAKEUP' in output
    assert 'sending signal' in output
    assert 'process has finished cleanly' in output
