from glob import glob
from setuptools import setup

setup(name='mobile_base_mapping', version='0.1.0', packages=[],
      data_files=[('share/ament_index/resource_index/packages', ['resource/mobile_base_mapping']),
                  ('share/mobile_base_mapping', ['package.xml', 'README.md']),
                  ('share/mobile_base_mapping/launch', glob('launch/*.launch.py')),
                  ('share/mobile_base_mapping/config', glob('config/*.yaml'))],
      maintainer='mobile_base maintainers', maintainer_email='maintainers@example.com',
      description='Native slam_toolbox mapping configuration.', license='Apache-2.0',
      tests_require=['pytest'])
