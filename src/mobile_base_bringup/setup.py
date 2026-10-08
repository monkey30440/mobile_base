from setuptools import setup
from glob import glob

setup(name='mobile_base_bringup', version='0.1.0', packages=[],
      data_files=[('share/ament_index/resource_index/packages', ['resource/mobile_base_bringup']),
                  ('share/mobile_base_bringup', ['package.xml', 'README.md']),
                  ('share/mobile_base_bringup/launch', glob('launch/*.launch.py'))],
      maintainer='mobile_base maintainers', maintainer_email='maintainers@example.com',
      description='V1 native ROS launch composition.', license='Apache-2.0',
      tests_require=['pytest'])
