from setuptools import setup

setup(
    name='mobile_base_imu', version='0.1.0', packages=['mobile_base_imu'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/mobile_base_imu']),
                ('share/mobile_base_imu', ['package.xml', 'README.md'])],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='mobile_base maintainers', maintainer_email='maintainers@example.com',
    description='Minimal USB HandBoard IMU bridge adapter for V1.',
    license='Apache-2.0', tests_require=['pytest'],
    entry_points={'console_scripts': ['usb_imu = mobile_base_imu.node:main']},
)
