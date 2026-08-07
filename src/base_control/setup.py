from glob import glob

from setuptools import find_packages, setup

package_name = 'base_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jim Chen',
    maintainer_email='SteveTsai@fih-foxconn.com',
    description='SUB-001 Base Control: differential drive base control over RS-485 Multi-drive 2.0.',
    license='Proprietary',
    entry_points={
        'console_scripts': [
            'base_control_node = base_control.node:main',
        ],
    },
)
