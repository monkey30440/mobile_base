from glob import glob
from setuptools import setup

setup(name='mobile_base_odometry', version='0.1.0', packages=[],
      data_files=[('share/ament_index/resource_index/packages', ['resource/mobile_base_odometry']),
                  ('share/mobile_base_odometry', ['package.xml', 'README.md']),
                  ('share/mobile_base_odometry/launch', glob('launch/*.launch.py')),
                  ('share/mobile_base_odometry/config', glob('config/*.yaml'))],
      maintainer='mobile_base maintainers', maintainer_email='maintainers@example.com',
      description='Native wheel and IMU local odometry configuration.', license='Apache-2.0',
      tests_require=['pytest'])
