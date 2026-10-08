"""Offline stationary raw-rate calibration; never controls the robot."""
import argparse
from datetime import datetime, timezone
import math
from pathlib import Path
import statistics
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
import yaml


def main():
    parser = argparse.ArgumentParser(description='Operator must ensure physical stationarity; gyro values alone cannot prove it.')
    parser.add_argument('--stationary', action='store_true', required=True,
                        help='Confirm the robot is physically stationary during this entire capture')
    parser.add_argument('--output', type=Path, required=True, help='New YAML file; existing files are never overwritten')
    parser.add_argument('--duration', type=float, default=60.0)
    parser.add_argument('--min-samples', type=int, default=200)
    parser.add_argument('--wait-timeout', type=float, default=10.0)
    parser.add_argument('--max-gap', type=float, default=0.3)
    args = parser.parse_args()
    for name in ('duration', 'wait_timeout', 'max_gap'):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            parser.error(name + ' must be finite and positive')
    if args.min_samples < 2:
        parser.error('min-samples must be at least two')
    output = args.output.expanduser().resolve()
    if output.exists() or not output.parent.is_dir():
        parser.error('output must be a new file in an existing directory: ' + str(output))
    rclpy.init(args=[])
    node = rclpy.create_node('imu_stationary_calibration')
    rows, stamps = [], []
    received = []
    errors = []

    def sample(message):
        now = time.monotonic()
        values = [message.angular_velocity.x, message.angular_velocity.y, message.angular_velocity.z]
        stamp = message.header.stamp.sec + message.header.stamp.nanosec / 1e9
        if message.header.frame_id != 'base_imu_link' or not all(math.isfinite(v) for v in values):
            errors.append('invalid raw sample frame/rate')
        elif stamps and (stamp <= stamps[-1] or stamp - stamps[-1] > args.max_gap):
            errors.append('raw sample timestamp discontinuity or gap')
        elif received and now - received[-1] > args.max_gap:
            errors.append('raw sample receipt gap')
        rows.append(values)
        stamps.append(stamp)
        received.append(now)

    node.create_subscription(Imu, '/imu/data_raw', sample, qos_profile_sensor_data)
    waiting = time.monotonic()
    try:
        print('Capturing /imu/data_raw; Operator-confirmed stationarity, no automatic motion detection.', flush=True)
        while True:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if errors:
                raise ValueError(errors[0])
            if not received and now - waiting > args.wait_timeout:
                raise ValueError('no raw IMU samples before wait timeout')
            if received and now - received[-1] > args.max_gap:
                raise ValueError('raw IMU stream stopped during calibration')
            if received and now - received[0] >= args.duration:
                break
        if len(rows) < args.min_samples:
            raise ValueError('insufficient raw samples: ' + str(len(rows)))
        bias = [statistics.mean(row[axis] for row in rows) for axis in range(3)]
        variances = [statistics.variance(row[axis] for row in rows) for axis in range(3)]
        if not all(math.isfinite(v) and v > 0 for v in variances):
            raise ValueError('noise dispersion not measurable on all three axes; do not invent zero uncertainty')
        result = {'frame_id': 'base_imu_link', 'units': 'rad/s', 'source_topic': '/imu/data_raw',
                  'calibrated_at_utc': datetime.now(timezone.utc).isoformat(),
                  'sample_count': len(rows), 'duration_seconds': now - received[0],
                  'first_sample_stamp': stamps[0], 'last_sample_stamp': stamps[-1],
                  'angular_velocity_bias': bias, 'angular_velocity_variances': variances}
        with output.open('x', encoding='utf8') as stream:
            yaml.safe_dump(result, stream, sort_keys=False)
        print(yaml.safe_dump(result, sort_keys=False), flush=True)
        print('Saved ' + str(output) + '; review before use. Session noise estimate, not thermal/long-term calibration.', flush=True)
    except (ValueError, OSError) as error:
        parser.exit(1, 'Calibration failed: ' + str(error) + '\n')
    finally:
        node.destroy_node()
        rclpy.shutdown()
