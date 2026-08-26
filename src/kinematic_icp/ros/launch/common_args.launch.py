from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "lidar_topic",
                default_value="/scan_front",
                description="Sensor topic for input pointcloud/laser scan",
            ),
            DeclareLaunchArgument(
                "use_2d_lidar",
                default_value="true",
                description="Whether input sensor is a 2D laser scan",
                choices=["true", "false"],
            ),
            DeclareLaunchArgument(
                "lidar_odometry_topic",
                default_value="lidar_odometry",
                description="Output topic for estimated LiDAR odometry",
            ),
            DeclareLaunchArgument(
                "lidar_odom_frame",
                default_value="odom",
                description="Odometry parent frame ID",
            ),
            DeclareLaunchArgument(
                "wheel_odom_frame",
                default_value="odom",
                description="Wheel odometry frame ID",
            ),
            DeclareLaunchArgument(
                "base_frame",
                default_value="base_footprint",
                description="Robot base frame ID",
            ),
            DeclareLaunchArgument(
                "publish_odom_tf",
                default_value="false",
                description="Whether to publish odom TF",
                choices=["true", "false"],
            ),
            DeclareLaunchArgument(
                "invert_odom_tf",
                default_value="false",
                description="Whether to invert published odom TF",
                choices=["true", "false"],
            ),
            DeclareLaunchArgument(
                "wheel_odom_topic",
                default_value="/diff_drive_controller/odom",
                description="Wheel odometry input topic",
            ),
            DeclareLaunchArgument(
                "visualize",
                default_value="false",
                description="Whether to start RViz visualization",
                choices=["true", "false"],
            ),
        ]
    )
