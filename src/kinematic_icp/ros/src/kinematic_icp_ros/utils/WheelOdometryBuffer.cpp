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

#include "kinematic_icp_ros/utils/WheelOdometryBuffer.hpp"

#include <algorithm>

namespace kinematic_icp_ros::utils {

WheelOdometryBuffer::WheelOdometryBuffer(double max_buffer_duration_sec)
    : max_buffer_duration_sec_(max_buffer_duration_sec) {}

void WheelOdometryBuffer::AddOdometry(const nav_msgs::msg::Odometry::ConstSharedPtr &msg) {
    if (!msg) return;
    WheelPoseSample sample;
    sample.stamp = msg->header.stamp;
    sample.x = msg->pose.pose.position.x;
    sample.y = msg->pose.pose.position.y;
    sample.yaw = ExtractYawFromQuaternion(msg->pose.pose.orientation);
    AddSample(sample);
}

void WheelOdometryBuffer::AddSample(const WheelPoseSample &sample) {
    std::lock_guard<std::mutex> lock(mutex_);
    ++total_samples_received_;

    if (buffer_.empty() || sample.stamp >= buffer_.back().stamp) {
        buffer_.push_back(sample);
    } else {
        // Out-of-order sample: find sorted insertion position
        auto it = std::upper_bound(
            buffer_.begin(), buffer_.end(), sample.stamp,
            [](const rclcpp::Time &stamp, const WheelPoseSample &s) {
                return stamp < s.stamp;
            });
        buffer_.insert(it, sample);
    }

    // Prune old samples exceeding retention duration
    while (buffer_.size() > 2) {
        const double duration = (buffer_.back().stamp - buffer_.front().stamp).seconds();
        if (duration > max_buffer_duration_sec_) {
            buffer_.pop_front();
        } else {
            break;
        }
    }
}

std::optional<WheelPoseSample> WheelOdometryBuffer::InterpolatePose(
    const rclcpp::Time &target_time,
    double time_tolerance_sec) const {
    std::lock_guard<std::mutex> lock(mutex_);

    if (buffer_.empty()) {
        ++dropped_frames_history_;
        return std::nullopt;
    }

    const auto &oldest = buffer_.front();
    const auto &newest = buffer_.back();

    // Check if target is before oldest sample
    if (target_time < oldest.stamp) {
        const double diff = (oldest.stamp - target_time).seconds();
        if (diff <= time_tolerance_sec) {
            return oldest;
        }
        ++dropped_frames_history_;
        return std::nullopt;
    }

    // Check if target is after newest sample
    if (target_time > newest.stamp) {
        const double diff = (target_time - newest.stamp).seconds();
        if (diff <= time_tolerance_sec) {
            return newest;
        }
        ++dropped_frames_future_;
        return std::nullopt;
    }

    // If only 1 sample exists (and passed boundary tolerance checks above)
    if (buffer_.size() == 1) {
        return oldest;
    }

    // Binary search for sample with stamp >= target_time
    auto it = std::lower_bound(
        buffer_.begin(), buffer_.end(), target_time,
        [](const WheelPoseSample &s, const rclcpp::Time &stamp) {
            return s.stamp < stamp;
        });

    if (it == buffer_.begin()) {
        return *it;
    }
    if (it == buffer_.end()) {
        return buffer_.back();
    }

    const auto &s0 = *(it - 1);
    const auto &s1 = *it;

    const double dt = (s1.stamp - s0.stamp).seconds();
    if (dt <= 1e-9) {
        return s0;
    }

    const double alpha = std::clamp((target_time - s0.stamp).seconds() / dt, 0.0, 1.0);

    WheelPoseSample res;
    res.stamp = target_time;
    res.x = s0.x + alpha * (s1.x - s0.x);
    res.y = s0.y + alpha * (s1.y - s0.y);

    // Shortest-angle interpolation on yaw
    const double delta_yaw = NormalizeAngle(s1.yaw - s0.yaw);
    res.yaw = NormalizeAngle(s0.yaw + alpha * delta_yaw);

    return res;
}

std::optional<Sophus::SE3d> WheelOdometryBuffer::ComputeDeltaTransform(
    const rclcpp::Time &begin_time,
    const rclcpp::Time &end_time,
    double time_tolerance_sec) const {
    const auto p_begin = InterpolatePose(begin_time, time_tolerance_sec);
    const auto p_end = InterpolatePose(end_time, time_tolerance_sec);

    if (!p_begin.has_value() || !p_end.has_value()) {
        return std::nullopt;
    }

    const Sophus::SE3d T_begin = p_begin->toSE3();
    const Sophus::SE3d T_end = p_end->toSE3();

    // Delta transform from base at begin_time to base at end_time expressed in begin frame:
    // delta = T_begin^{-1} * T_end
    return T_begin.inverse() * T_end;
}

std::optional<Sophus::SE3d> WheelOdometryBuffer::GetLatestPose() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (buffer_.empty()) {
        return std::nullopt;
    }
    return buffer_.back().toSE3();
}

std::optional<Sophus::SE3d> WheelOdometryBuffer::GetPoseAt(
    const rclcpp::Time &target_time,
    double time_tolerance_sec) const {
    const auto p = InterpolatePose(target_time, time_tolerance_sec);
    if (!p.has_value()) {
        return std::nullopt;
    }
    return p->toSE3();
}

void WheelOdometryBuffer::Clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    buffer_.clear();
}

size_t WheelOdometryBuffer::Size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return buffer_.size();
}

bool WheelOdometryBuffer::Empty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return buffer_.empty();
}

}  // namespace kinematic_icp_ros::utils
