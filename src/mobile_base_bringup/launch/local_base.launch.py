"""Local base verification: measured wheels, USB IMU and native model/EKF owners."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def setup(context):
    launch = Path(get_package_share_directory('mobile_base_bringup')) / 'launch'
    values = {}
    for name in ('hardware_config', 'imu_config', 'filter_config', 'model_file'):
        value = Path(LaunchConfiguration(name).perform(context)).expanduser().resolve()
        if not value.is_file():
            raise RuntimeError(f'Local base {name} file required: {value}')
        values[name] = str(value)
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(launch / file)),
                launch_arguments={name: values[name] for name in names}.items())
            for file, names in [('control.launch.py', ('hardware_config','model_file')),
                                ('imu.launch.py', ('imu_config',)),
                                ('local_estimation.launch.py', ('filter_config',))]]


def generate_launch_description():
    model = str(Path(get_package_share_directory('mobile_base_description')) / 'urdf/mobile_base.urdf.xacro')
    return LaunchDescription([
        *[DeclareLaunchArgument(name) for name in ('hardware_config','imu_config','filter_config')],
        DeclareLaunchArgument('model_file', default_value=model),
        OpaqueFunction(function=setup),
    ])
