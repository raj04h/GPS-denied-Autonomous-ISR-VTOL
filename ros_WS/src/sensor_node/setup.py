from setuptools import find_packages, setup

package_name = 'sensor_node'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hraj',
    maintainer_email='himanshuraj.hr9934@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
    'console_scripts': [
        'strix_imu_publisher = sensor_node.flight_controller.strix_imu_publisher:main',
        'sensor_health_monitor = sensor_node.health.sensor_health_monitor:main',
        'strix_timing = sensor_node.timing.strix_timing:main',
        'realsense_timing = sensor_node.timing.realsense_timing:main',
        'concurrent_sensor_logger = sensor_node.timing.concurrent_sensor_logger:main',
        'analyze_sensor_timing = sensor_node.timing.analyze_sensor_timing:main',
    ],
},
)
