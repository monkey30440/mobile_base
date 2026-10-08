from glob import glob
from setuptools import setup

setup(
    name='mobile_base_perception', version='0.1.0', packages=['mobile_base_perception'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/mobile_base_perception']),
                ('share/mobile_base_perception', ['package.xml', 'README.md']),
                ('share/mobile_base_perception/launch', glob('launch/*.launch.py')),
                ('share/mobile_base_perception/config', glob('config/*.yaml'))],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='mobile_base maintainers', maintainer_email='maintainers@example.com',
    description='V1 USB IMU adapter and native dual picoScan composition.',
    license='Apache-2.0', tests_require=['pytest'],
    entry_points={'console_scripts': ['usb_imu = mobile_base_perception.node:main',
                                      'calibrate_imu = mobile_base_perception.calibrate:main']},
)
