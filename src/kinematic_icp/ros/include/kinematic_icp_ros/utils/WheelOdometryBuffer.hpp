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

#pragma once

#include <cmath>
#include <deque>
#include <mutex>
#include <optional>

#include <geometry_msgs/msg/quaternion.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/time.hpp>
#include <sophus/se3.hpp>

namespace kinematic_icp_ros::utils {

struct WheelPoseSample {
    rclcpp::Time stamp;
    double x{0.0};
    double y{0.0};
    double yaw{0.0};  // radians in [-pi, pi]

    Sophus::SE3d toSE3() const {
        Eigen::Quaterniond q(Eigen::AngleAxisd(yaw, Eigen::Vector3d::UnitZ()));
        return Sophus::SE3d(q, Eigen::Vector3d(x, y, 0.0));
    }
};

class WheelOdometryBuffer {
public:
    explicit WheelOdometryBuffer(double max_buffer_duration_sec = 5.0);

    /// Add an incoming wheel Odometry message
    void AddOdometry(const nav_msgs::msg::Odometry::ConstSharedPtr &msg);
    void AddSample(const WheelPoseSample &sample);

    /// Interpolate pose at a given target timestamp
    std::optional<WheelPoseSample> InterpolatePose(
        const rclcpp::Time &target_time,
        double time_tolerance_sec = 0.05) const;

    /// Compute delta transform T_begin^{-1} * T_end between two timestamps
    std::optional<Sophus::SE3d> ComputeDeltaTransform(
        const rclcpp::Time &begin_time,
        const rclcpp::Time &end_time,
        double time_tolerance_sec = 0.05) const;

    /// Retrieve the latest pose in buffer
    std::optional<Sophus::SE3d> GetLatestPose() const;

    /// Retrieve pose at exact/interpolated timestamp as Sophus::SE3d
    std::optional<Sophus::SE3d> GetPoseAt(
        const rclcpp::Time &target_time,
        double time_tolerance_sec = 0.05) const;

    /// Clear buffer
    void Clear();

    /// Get current buffer size
    size_t Size() const;

    /// Check if buffer is empty
    bool Empty() const;

    /// Diagnostics
    size_t TotalSamplesReceived() const { return total_samples_received_; }
    size_t DroppedFramesHistory() const { return dropped_frames_history_; }
    size_t DroppedFramesFuture() const { return dropped_frames_future_; }

    static double NormalizeAngle(double angle) {
        while (angle > M_PI) angle -= 2.0 * M_PI;
        while (angle < -M_PI) angle += 2.0 * M_PI;
        return angle;
    }

    static double ExtractYawFromQuaternion(const geometry_msgs::msg::Quaternion &q) {
        double siny_cosp = 2.0 * (q.w * q.z + q.x * q.y);
        double cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z);
        return NormalizeAngle(std::atan2(siny_cosp, cosy_cosp));
    }

private:
    double max_buffer_duration_sec_{5.0};
    mutable std::mutex mutex_;
    std::deque<WheelPoseSample> buffer_;

    mutable size_t total_samples_received_{0};
    mutable size_t dropped_frames_history_{0};
    mutable size_t dropped_frames_future_{0};
};

}  // namespace kinematic_icp_ros::utils
