"""Load the Operator-selected SI calibration; never guess missing offsets."""
from datetime import datetime
import math
from pathlib import Path

import yaml


def load_calibration(filename):
    if not filename:
        raise ValueError('calibration_file not configured; raw only')
    path = Path(filename).expanduser().resolve()
    with path.open(encoding='utf8') as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError('calibration must be a YAML mapping')
    for key, value in (('frame_id', 'base_imu_link'), ('units', 'rad/s'), ('source_topic', '/imu/data_raw')):
        if data.get(key) != value:
            raise ValueError('calibration ' + key + ' mismatch')
    for key in ('angular_velocity_bias', 'angular_velocity_variances'):
        values = data.get(key)
        if (not isinstance(values, list) or len(values) != 3
                or not all(type(v) in (int, float) and math.isfinite(v) for v in values)):
            raise ValueError('calibration requires three finite SI values: ' + key)
    if any(v <= 0 for v in data['angular_velocity_variances']):
        raise ValueError('calibration variances must be positive; no invented zero uncertainty')
    if type(data.get('sample_count')) is not int or data['sample_count'] < 2:
        raise ValueError('calibration sample_count must be at least two')
    for key in ('duration_seconds', 'first_sample_stamp', 'last_sample_stamp'):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('invalid calibration capture metadata: ' + key)
    if data['duration_seconds'] <= 0 or data['last_sample_stamp'] <= data['first_sample_stamp']:
        raise ValueError('invalid calibration capture interval')
    when = data.get('calibrated_at_utc')
    if not isinstance(when, str) or datetime.fromisoformat(when).tzinfo is None:
        raise ValueError('calibration timestamp must include timezone')
    return data
