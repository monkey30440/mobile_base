"""Public Mapping composition entry; these checks never open hardware."""
import subprocess


def test_operator_can_select_mapping_profiles():
    result = subprocess.run([
        'ros2', 'launch', 'mobile_base_bringup', 'mapping.launch.py', '--show-args',
    ], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    for argument in ('hardware_config', 'model_file', 'lidar_config', 'imu_config',
                     'filter_config', 'mapping_config'):
        assert argument in result.stdout
    for profile in ('m1.yaml', 'lidar.yaml', 'imu.yaml', 'ekf.yaml', 'slam.yaml'):
        assert profile in result.stdout


def test_missing_selected_hardware_profile_stops_mapping_start(tmp_path):
    missing = tmp_path / 'missing.yaml'
    result = subprocess.run([
        'ros2', 'launch', 'mobile_base_bringup', 'mapping.launch.py',
        'hardware_config:=' + str(missing),
    ], capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert str(missing) in result.stdout + result.stderr
    assert 'process started' not in result.stdout + result.stderr
