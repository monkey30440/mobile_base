// MIT License
//
// Copyright (c) 2024 Tiziano Guadagnino, Benedikt Mersch, Ignacio Vizzo, Cyrill Stachniss.
// Copyright (c) 2026 Antigravity Team.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#include "kinematic_icp_ros/server/LidarOdometryServer.hpp"

#include <Eigen/Core>
#include <algorithm>
#include <chrono>
#include <memory>
#include <mutex>
#include <sophus/se3.hpp>
#include <utility>

#include "kinematic_icp/pipeline/KinematicICP.hpp"
#include "kinematic_icp_ros/utils/RosUtils.hpp"

// ROS 2 headers
#include <rcl/time.h>
#include <tf2_ros/buffer_interface.h>
#include <tf2_ros/transform_broadcaster.h>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <nav_msgs/msg/path.hpp>
#include <rclcpp/qos.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <visualization_msgs/msg/marker.hpp>

namespace {
using milliseconds = std::chrono::milliseconds;
using seconds = std::chrono::duration<long double>;
using std::chrono::duration_cast;
}  // namespace

namespace kinematic_icp_ros {

using namespace utils;

LidarOdometryServer::LidarOdometryServer(rclcpp::Node::SharedPtr node) : node_(node) {
    lidar_odom_frame_ =
        node->declare_parameter<std::string>("lidar_odom_frame", lidar_odom_frame_);
    base_frame_ = node->declare_parameter<std::string>("base_frame", base_frame_);
    wheel_odom_topic_ =
        node->declare_parameter<std::string>("wheel_odom_topic", wheel_odom_topic_);
    time_tolerance_sec_ =
        node->declare_parameter<double>("time_tolerance_sec", time_tolerance_sec_);
    publish_odom_tf_ = node->declare_parameter<bool>("publish_odom_tf", false);
    invert_odom_tf_ = node->declare_parameter<bool>("invert_odom_tf", false);
    tf_timeout_ =
        duration_cast<milliseconds>(seconds(node->declare_parameter<double>("tf_timeout", 0.0)));

    kinematic_icp::pipeline::Config config;
    // Preprocessing
    config.max_range = node->declare_parameter<double>("max_range", config.max_range);
    config.min_range = node->declare_parameter<double>("min_range", config.min_range);
    // Mapping parameters
    config.voxel_size = node->declare_parameter<double>("voxel_size", config.voxel_size);
    config.max_points_per_voxel =
        node->declare_parameter<int>("max_points_per_voxel", config.max_points_per_voxel);
    // Correspondence threshold parameters
    config.use_adaptive_threshold =
        node->declare_parameter<bool>("use_adaptive_threshold", config.use_adaptive_threshold);
    config.fixed_threshold =
        node->declare_parameter<double>("fixed_threshold", config.fixed_threshold);
    // Registration Parameters
    config.max_num_iterations =
        node->declare_parameter<int>("max_num_iterations", config.max_num_iterations);
    config.convergence_criterion =
        node->declare_parameter<double>("convergence_criterion", config.convergence_criterion);
    config.max_num_threads =
        node->declare_parameter<int>("max_num_threads", config.max_num_threads);
    config.use_adaptive_odometry_regularization = node->declare_parameter<bool>(
        "use_adaptive_odometry_regularization", config.use_adaptive_odometry_regularization);
    config.fixed_regularization =
        node->declare_parameter<double>("fixed_regularization", config.fixed_regularization);
    // Motion compensation
    config.deskew = node->declare_parameter<bool>("deskew", config.deskew);
    if (config.max_range < config.min_range) {
        RCLCPP_WARN(node_->get_logger(),
                    "[WARNING] max_range is smaller than min_range, setting min_range to 0.0");
        config.min_range = 0.0;
    }

    // Construct the main KISS-ICP odometry pipeline
    kinematic_icp_ = std::make_unique<kinematic_icp::pipeline::KinematicICP>(config);

    // Initialize publishers
    rclcpp::QoS qos((rclcpp::SystemDefaultsQoS().keep_last(1).durability_volatile()));
    odom_publisher_ = node_->create_publisher<nav_msgs::msg::Odometry>("lidar_odometry", qos);
    frame_publisher_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("frame", qos);
    kpoints_publisher_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("keypoints", qos);
    map_publisher_ = node_->create_publisher<sensor_msgs::msg::PointCloud2>("local_map", qos);
    voxel_grid_pub_ = node_->create_publisher<visualization_msgs::msg::Marker>("voxel_grid", qos);

    // Subscribe to wheel odometry topic directly (replacing dynamic TF lookup)
    wheel_odom_sub_ = node_->create_subscription<nav_msgs::msg::Odometry>(
        wheel_odom_topic_, rclcpp::SystemDefaultsQoS(),
        [this](const nav_msgs::msg::Odometry::ConstSharedPtr msg) {
            wheel_odometry_buffer_.AddOdometry(msg);
        });

    // Reset pose service using latest valid wheel odometry sample from buffer
    set_pose_srv_ = node_->create_service<std_srvs::srv::Trigger>(
        "set_pose", [this](const std::shared_ptr<std_srvs::srv::Trigger::Request> /*request*/,
                           std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
            const auto pose_opt = wheel_odometry_buffer_.GetLatestPose();
            if (!pose_opt.has_value()) {
                response->success = false;
                response->message = "No valid wheel odometry available in buffer.";
                RCLCPP_WARN(node_->get_logger(), "set_pose failed: %s", response->message.c_str());
                return;
            }
            RCLCPP_INFO_STREAM(node_->get_logger(), "Resetting Kinematic-ICP pose:\n"
                                                        << pose_opt->matrix() << "\n");
            kinematic_icp_->SetPose(*pose_opt);
            response->success = true;
            response->message = "Kinematic-ICP pose reset successfully.";
        });

    // Initialize TF buffer and listener for static sensor extrinsic lookup
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(node_);
    tf2_buffer_ = std::make_unique<tf2_ros::Buffer>(node_->get_clock());
    tf2_listener_ = std::make_unique<tf2_ros::TransformListener>(*tf2_buffer_);

    // Initialize odometry and optional TF message
    if (invert_odom_tf_) {
        tf_msg_.header.frame_id = base_frame_;
        tf_msg_.child_frame_id = lidar_odom_frame_;
    } else {
        tf_msg_.header.frame_id = lidar_odom_frame_;
        tf_msg_.child_frame_id = base_frame_;
    }

    // Fixed covariance initialization
    const auto position_covariance = node->declare_parameter<double>("position_covariance", 0.1);
    const auto orientation_covariance =
        node->declare_parameter<double>("orientation_covariance", 0.1);
    odom_msg_.header.frame_id = lidar_odom_frame_;
    odom_msg_.child_frame_id = base_frame_;
    odom_msg_.pose.covariance.fill(0.0);
    odom_msg_.pose.covariance[0] = position_covariance;
    odom_msg_.pose.covariance[7] = position_covariance;
    odom_msg_.pose.covariance[35] = orientation_covariance;
    odom_msg_.twist.covariance.fill(0.0);
    odom_msg_.twist.covariance[0] = position_covariance;
    odom_msg_.twist.covariance[7] = position_covariance;
    odom_msg_.twist.covariance[35] = orientation_covariance;
}

void LidarOdometryServer::InitializePoseAndExtrinsic(
    const sensor_msgs::msg::PointCloud2::ConstSharedPtr &msg) {
    if (!tf2_buffer_->_frameExists(base_frame_) ||
        !tf2_buffer_->_frameExists(msg->header.frame_id)) {
        return;
    }

    // Query wheel odometry pose at the initialization scan timestamp
    auto init_pose_opt =
        wheel_odometry_buffer_.GetPoseAt(msg->header.stamp, time_tolerance_sec_);
    if (!init_pose_opt.has_value()) {
        init_pose_opt = wheel_odometry_buffer_.GetLatestPose();
    }

    if (!init_pose_opt.has_value()) {
        RCLCPP_INFO_THROTTLE(
            node_->get_logger(), *node_->get_clock(), 2000,
            "Waiting for wheel odometry on '%s' to initialize Kinematic-ICP pose...",
            wheel_odom_topic_.c_str());
        return;
    }

    try {
        sensor_to_base_footprint_ = tf2::transformToSophus(
            tf2_buffer_->lookupTransform(base_frame_, msg->header.frame_id, tf2::TimePointZero));
    } catch (tf2::TransformException &ex) {
        RCLCPP_ERROR(node_->get_logger(), "Static extrinsic lookup failed: %s", ex.what());
        return;
    }

    kinematic_icp_->SetPose(*init_pose_opt);
    timestamps_handler_.last_processed_stamp_ = msg->header.stamp;
    initialize_odom_node = true;
    RCLCPP_INFO(node_->get_logger(), "Kinematic-ICP initialized successfully with wheel prior.");
}

void LidarOdometryServer::RegisterFrame(const sensor_msgs::msg::PointCloud2::ConstSharedPtr &msg) {
    if (!initialize_odom_node) {
        InitializePoseAndExtrinsic(msg);
        if (!initialize_odom_node) {
            return;
        }
    }

    // Buffer the last state for velocity computation
    const auto last_pose = kinematic_icp_->pose();
    const auto &[begin_odom_query, end_odom_query, timestamps] =
        timestamps_handler_.ProcessTimestamps(msg);

    // Get the interpolated motion prior from wheel odometry buffer
    const auto delta_opt = wheel_odometry_buffer_.ComputeDeltaTransform(
        begin_odom_query, end_odom_query, time_tolerance_sec_);

    if (!delta_opt.has_value()) {
        RCLCPP_WARN_THROTTLE(
            node_->get_logger(), *node_->get_clock(), 1000,
            "Wheel odometry prior unavailable for interval [%.4f, %.4f]. Deferring scan.",
            timestamps_handler_.toTime(begin_odom_query),
            timestamps_handler_.toTime(end_odom_query));
        return;
    }

    const auto &delta = *delta_opt;

    // Run Kinematic ICP registration
    if (delta.log().norm() > 1e-3) {
        const auto &extrinsic = sensor_to_base_footprint_;
        const auto points = PointCloud2ToEigen(msg, {});
        const auto &[frame, kpoints] =
            kinematic_icp_->RegisterFrame(points, timestamps, extrinsic, delta);
        PublishClouds(frame, kpoints);
    }

    // Compute velocities using elapsed interval between consecutive LiDAR frames
    const double elapsed_time =
        timestamps_handler_.toTime(end_odom_query) - timestamps_handler_.toTime(begin_odom_query);
    Sophus::SE3d::Tangent velocity = Sophus::SE3d::Tangent::Zero();
    if (elapsed_time > 1e-6) {
        const Sophus::SE3d::Tangent delta_twist =
            (last_pose.inverse() * kinematic_icp_->pose()).log();
        velocity = delta_twist / elapsed_time;
    }

    // Publish odometry message
    PublishOdometryMsg(kinematic_icp_->pose(), velocity);
}

void LidarOdometryServer::PublishOdometryMsg(const Sophus::SE3d &pose,
                                             const Sophus::SE3d::Tangent &velocity) {
    // Broadcast over TF if explicitly enabled (default false)
    if (publish_odom_tf_) {
        tf_msg_.transform = [&]() {
            if (invert_odom_tf_) return tf2::sophusToTransform(pose.inverse());
            return tf2::sophusToTransform(pose);
        }();
        tf_msg_.header.stamp = timestamps_handler_.last_processed_stamp_;
        tf_broadcaster_->sendTransform(tf_msg_);
    }

    // Publish Odometry message
    odom_msg_.pose.pose = tf2::sophusToPose(pose);
    odom_msg_.twist.twist.linear.x = velocity[0];
    odom_msg_.twist.twist.angular.z = velocity[5];
    odom_msg_.header.stamp = timestamps_handler_.last_processed_stamp_;
    odom_publisher_->publish(odom_msg_);
}

void LidarOdometryServer::PublishClouds(const std::vector<Eigen::Vector3d> frame,
                                        const std::vector<Eigen::Vector3d> keypoints) {
    std_msgs::msg::Header lidar_header;
    lidar_header.frame_id = base_frame_;
    lidar_header.stamp = timestamps_handler_.last_processed_stamp_;

    std_msgs::msg::Header map_header;
    map_header.frame_id = lidar_odom_frame_;
    map_header.stamp = timestamps_handler_.last_processed_stamp_;

    if (frame_publisher_->get_subscription_count() > 0) {
        frame_publisher_->publish(std::move(EigenToPointCloud2(frame, lidar_header)));
    }
    if (kpoints_publisher_->get_subscription_count() > 0) {
        kpoints_publisher_->publish(std::move(EigenToPointCloud2(keypoints, lidar_header)));
    }
    if (map_publisher_->get_subscription_count() > 0) {
        map_publisher_->publish(
            std::move(EigenToPointCloud2(kinematic_icp_->LocalMap(), map_header)));
    }
}

}  // namespace kinematic_icp_ros
