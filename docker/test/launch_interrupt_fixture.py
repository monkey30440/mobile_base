"""Inject SIGINT where an observed interruption lost the event consumer wakeup."""
import asyncio
import signal
import sys

from launch import LaunchDescription, LaunchService
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessStart

armed = False
injected = False
custom_signal_received = False


def custom_handler(signum, frame):
    global custom_signal_received
    custom_signal_received = True


if 'custom' in sys.argv:
    signal.signal(signal.SIGINT, custom_handler)


def arm(event, context):
    global armed
    armed = True


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
original_call_soon = loop.call_soon


def schedule(callback, *args, context=None):
    global injected
    task = getattr(callback, '__self__', None)
    if (
        getattr(callback, '__name__', '') == 'task_wakeup'
        and armed and not injected and isinstance(task, asyncio.Task)
        and task.get_coro().__name__ == '_process_one_event'
    ):
        injected = True
        print('INJECT SIGINT AT EVENT TASK WAKEUP', flush=True)
        signal.raise_signal(signal.SIGINT)
    return original_call_soon(callback, *args, context=context)


loop.call_soon = schedule
service = LaunchService(noninteractive=True)
child = (
    'import signal,time; '
    'signal.signal(signal.SIGINT,lambda *_: exit(0)); '
    'print("READY",flush=True); time.sleep(30)'
)
service.include_launch_description(LaunchDescription([
    RegisterEventHandler(OnProcessStart(on_start=arm)),
    ExecuteProcess(cmd=[sys.executable, '-u', '-c', child], output='screen'),
]))
previous_handler = signal.getsignal(signal.SIGINT)
code = service.run()
assert signal.getsignal(signal.SIGINT) is previous_handler
assert injected
if 'custom' in sys.argv:
    assert custom_signal_received
loop.close()
raise SystemExit(code)
