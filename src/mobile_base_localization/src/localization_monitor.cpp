// Copyright 2026 Antigravity Team.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "mobile_base_localization/localization_monitor.hpp"

#include <algorithm>
#include <cmath>

#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

namespace mobile_base_localization
{

void ScanMapQualityEvaluatorConfig::validate() const
{
  if (match_dist_m <= 0.0) {
    throw std::invalid_argument("match_dist_m must be > 0");
  }
  if (occupied_threshold < 0 || occupied_threshold > 100) {
    throw std::invalid_argument("occupied_threshold must be in [0, 100]");
  }
  if (min_valid_beams <= 0) {
    throw std::invalid_argument("min_valid_beams must be > 0");
  }
  if (beam_stride < 1) {
    throw std::invalid_argument("beam_stride must be >= 1");
  }
}

ScanMapQualityEvaluator::ScanMapQualityEvaluator(
  const ScanMapQualityEvaluatorConfig & config)
{
  set_config(config);
}

void ScanMapQualityEvaluator::set_config(const ScanMapQualityEvaluatorConfig & config)
{
  config.validate();
  config_ = config;
}

bool ScanMapQualityEvaluator::set_map(const nav_msgs::msg::OccupancyGrid & map_msg)
{
  const auto & q = map_msg.info.origin.orientation;

  // Compute roll, pitch, yaw from quaternion
  double siny_cosp = 2.0 * (q.w * q.z + q.x * q.y);
  double cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z);
  double yaw = std::atan2(siny_cosp, cosy_cosp);

  double sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z);
  double cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y);
  double roll = std::atan2(sinr_cosp, cosr_cosp);

  double sinp = 2.0 * (q.w * q.y - q.z * q.x);
  double pitch = (std::abs(sinp) >= 1.0) ? std::copysign(M_PI / 2.0, sinp) : std::asin(sinp);

  constexpr double kAngleTolerance = 1e-3;
  if (std::abs(roll) > kAngleTolerance ||
    std::abs(pitch) > kAngleTolerance ||
    std::abs(yaw) > kAngleTolerance)
  {
    has_map_ = false;
    return false;
  }

  int width = static_cast<int>(map_msg.info.width);
  int height = static_cast<int>(map_msg.info.height);
  if (width <= 0 || height <= 0 || map_msg.info.resolution <= 0.0) {
    has_map_ = false;
    return false;
  }

  // Convert OccupancyGrid into binary image.
  // Occupied cells (>= occupied_threshold) are set to 0.
  // Free and unknown cells (< occupied_threshold) are set to 255.
  // Unknown cells are thus NOT treated as matching occupied walls.
  cv::Mat binary_img(height, width, CV_8UC1);
  for (int r = 0; r < height; ++r) {
    auto * row_ptr = binary_img.ptr<uint8_t>(r);
    for (int c = 0; c < width; ++c) {
      int8_t val = map_msg.data[r * width + c];
      if (val >= config_.occupied_threshold) {
        row_ptr[c] = 0;
      } else {
        row_ptr[c] = 255;
      }
    }
  }

  // Build distance-to-nearest-occupied-cell field
  cv::distanceTransform(binary_img, dist_field_, cv::DIST_L2, cv::DIST_MASK_PRECISE);

  map_info_ = map_msg.info;
  has_map_ = true;
  return true;
}

bool ScanMapQualityEvaluator::has_map() const
{
  return has_map_;
}

std::optional<float> ScanMapQualityEvaluator::evaluate(
  const sensor_msgs::msg::LaserScan & scan_msg,
  const geometry_msgs::msg::TransformStamped & tf_map_to_scan) const
{
  tf2::Transform tf;
  tf2::fromMsg(tf_map_to_scan.transform, tf);
  return evaluate(scan_msg, tf);
}

std::optional<float> ScanMapQualityEvaluator::evaluate(
  const sensor_msgs::msg::LaserScan & scan_msg,
  const tf2::Transform & tf_map_to_scan) const
{
  if (!has_map_) {
    return std::nullopt;
  }

  int stride = config_.beam_stride;
  int inlier_count = 0;
  int valid_endpoint_count = 0;

  int num_ranges = static_cast<int>(scan_msg.ranges.size());
  double origin_x = map_info_.origin.position.x;
  double origin_y = map_info_.origin.position.y;
  double resolution = map_info_.resolution;
  int map_w = static_cast<int>(map_info_.width);
  int map_h = static_cast<int>(map_info_.height);

  for (int i = 0; i < num_ranges; i += stride) {
    float r = scan_msg.ranges[i];
    // 1. Ignore invalid ranges: non-finite, below range_min, above range_max
    if (!std::isfinite(r) || r < scan_msg.range_min || r > scan_msg.range_max) {
      continue;
    }

    double angle = scan_msg.angle_min + i * scan_msg.angle_increment;
    double x_scan = r * std::cos(angle);
    double y_scan = r * std::sin(angle);

    tf2::Vector3 pt_scan(x_scan, y_scan, 0.0);
    tf2::Vector3 pt_map = tf_map_to_scan * pt_scan;

    double cell_x = (pt_map.x() - origin_x) / resolution;
    double cell_y = (pt_map.y() - origin_y) / resolution;

    int col = static_cast<int>(std::floor(cell_x));
    int row = static_cast<int>(std::floor(cell_y));

    // Only endpoints inside the map may participate in the denominator
    if (col < 0 || col >= map_w || row < 0 || row >= map_h) {
      continue;
    }

    valid_endpoint_count++;

    float dist_cells = dist_field_.at<float>(row, col);
    float dist_m = dist_cells * static_cast<float>(resolution);
    if (dist_m <= static_cast<float>(config_.match_dist_m)) {
      inlier_count++;
    }
  }

  if (valid_endpoint_count < config_.min_valid_beams) {
    return std::nullopt;
  }

  float quality = static_cast<float>(inlier_count) / static_cast<float>(valid_endpoint_count);
  return quality;
}

void LocalizationLostDetectorConfig::validate() const
{
  if (lost_ratio < 0.0 || lost_ratio > 1.0) {
    throw std::invalid_argument("lost_ratio must be in [0.0, 1.0]");
  }
  if (recover_ratio < 0.0 || recover_ratio > 1.0) {
    throw std::invalid_argument("recover_ratio must be in [0.0, 1.0]");
  }
  if (lost_ratio >= recover_ratio) {
    throw std::invalid_argument("lost_ratio must be < recover_ratio");
  }
  if (lost_hold_s < 0.0) {
    throw std::invalid_argument("lost_hold_s must be >= 0");
  }
  if (recover_hold_s < 0.0) {
    throw std::invalid_argument("recover_hold_s must be >= 0");
  }
}

LocalizationLostDetector::LocalizationLostDetector(
  const LocalizationLostDetectorConfig & config)
{
  set_config(config);
}

void LocalizationLostDetector::set_config(const LocalizationLostDetectorConfig & config)
{
  config.validate();
  config_ = config;
}

LocalizationHealthState LocalizationLostDetector::update(float quality, double current_time)
{
  if (last_measurement_time_.has_value() && current_time < *last_measurement_time_) {
    // Time went backwards (e.g. sim time reset)
    low_quality_start_time_.reset();
    high_quality_start_time_.reset();
  }
  last_measurement_time_ = current_time;

  if (current_state_ == LocalizationHealthState::UNKNOWN) {
    if (quality >= config_.recover_ratio) {
      current_state_ = LocalizationHealthState::OK;
      low_quality_start_time_.reset();
      high_quality_start_time_.reset();
    } else if (quality < config_.lost_ratio) {
      if (!low_quality_start_time_.has_value()) {
        low_quality_start_time_ = current_time;
      } else if ((current_time - *low_quality_start_time_) >= config_.lost_hold_s) {
        current_state_ = LocalizationHealthState::LOST;
        low_quality_start_time_.reset();
      }
    } else {
      low_quality_start_time_.reset();
      high_quality_start_time_.reset();
    }
  } else if (current_state_ == LocalizationHealthState::OK) {
    if (quality < config_.lost_ratio) {
      if (!low_quality_start_time_.has_value()) {
        low_quality_start_time_ = current_time;
      } else if ((current_time - *low_quality_start_time_) >= config_.lost_hold_s) {
        current_state_ = LocalizationHealthState::LOST;
        low_quality_start_time_.reset();
      }
    } else {
      low_quality_start_time_.reset();
    }
  } else if (current_state_ == LocalizationHealthState::LOST) {
    if (quality >= config_.recover_ratio) {
      if (!high_quality_start_time_.has_value()) {
        high_quality_start_time_ = current_time;
      } else if ((current_time - *high_quality_start_time_) >= config_.recover_hold_s) {
        current_state_ = LocalizationHealthState::OK;
        high_quality_start_time_.reset();
      }
    } else {
      high_quality_start_time_.reset();
    }
  }

  return current_state_;
}

void LocalizationLostDetector::reset()
{
  current_state_ = LocalizationHealthState::UNKNOWN;
  low_quality_start_time_.reset();
  high_quality_start_time_.reset();
  last_measurement_time_.reset();
}

LocalizationMonitorNode::LocalizationMonitorNode(const rclcpp::NodeOptions & options)
: Node("localization_monitor", options)
{
  double match_dist_m = this->declare_parameter<double>("match_dist_m", 0.15);
  int occupied_threshold = static_cast<int>(
    this->declare_parameter<int64_t>("occupied_threshold", 65));
  int min_valid_beams = static_cast<int>(
    this->declare_parameter<int64_t>("min_valid_beams", 30));
  int beam_stride = static_cast<int>(
    this->declare_parameter<int64_t>("beam_stride", 1));

  double lost_ratio = this->declare_parameter<double>("lost_ratio", 0.35);
  double recover_ratio = this->declare_parameter<double>("recover_ratio", 0.60);
  double lost_hold_s = this->declare_parameter<double>("lost_hold_s", 1.5);
  double recover_hold_s = this->declare_parameter<double>("recover_hold_s", 1.5);

  tf_timeout_s_ = this->declare_parameter<double>("tf_timeout_s", 0.1);
  if (tf_timeout_s_ < 0.0) {
    throw std::invalid_argument("tf_timeout_s must be >= 0");
  }

  ScanMapQualityEvaluatorConfig eval_cfg;
  eval_cfg.match_dist_m = match_dist_m;
  eval_cfg.occupied_threshold = occupied_threshold;
  eval_cfg.min_valid_beams = min_valid_beams;
  eval_cfg.beam_stride = beam_stride;
  evaluator_.set_config(eval_cfg);

  LocalizationLostDetectorConfig det_cfg;
  det_cfg.lost_ratio = lost_ratio;
  det_cfg.recover_ratio = recover_ratio;
  det_cfg.lost_hold_s = lost_hold_s;
  det_cfg.recover_hold_s = recover_hold_s;
  detector_.set_config(det_cfg);

  quality_pub_ = this->create_publisher<std_msgs::msg::Float32>("/localization/quality", 10);
  lost_pub_ = this->create_publisher<std_msgs::msg::Bool>("/localization/lost", 10);

  tf_buffer_ = std::make_shared<tf2_ros::Buffer>(this->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

  auto map_qos = rclcpp::QoS(rclcpp::KeepLast(1)).reliable().transient_local();
  map_sub_ = this->create_subscription<nav_msgs::msg::OccupancyGrid>(
    "/map", map_qos,
    std::bind(&LocalizationMonitorNode::map_callback, this, std::placeholders::_1));

  scan_sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
    "/scan_front", rclcpp::SensorDataQoS(),
    std::bind(&LocalizationMonitorNode::scan_callback, this, std::placeholders::_1));

  RCLCPP_INFO(this->get_logger(), "LocalizationMonitor initialized successfully.");
}

void LocalizationMonitorNode::map_callback(
  const nav_msgs::msg::OccupancyGrid::ConstSharedPtr msg)
{
  if (!evaluator_.set_map(*msg)) {
    RCLCPP_ERROR(
      this->get_logger(),
      "Rejected /map: orientation yaw is non-zero or map dimensions are invalid. "
      "MVP requires axis-aligned map (yaw == 0).");
  } else {
    RCLCPP_INFO(
      this->get_logger(),
      "Successfully received and processed /map (resolution: %.3f m, size: %u x %u)",
      msg->info.resolution, msg->info.width, msg->info.height);
  }
}

void LocalizationMonitorNode::scan_callback(
  const sensor_msgs::msg::LaserScan::ConstSharedPtr msg)
{
  if (!evaluator_.has_map()) {
    return;
  }

  geometry_msgs::msg::TransformStamped tf_stamped;
  try {
    tf_stamped = tf_buffer_->lookupTransform(
      "map", msg->header.frame_id, msg->header.stamp,
      rclcpp::Duration::from_seconds(tf_timeout_s_));
  } catch (const tf2::TransformException & ex) {
    RCLCPP_DEBUG_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000,
      "TF lookup map -> %s failed: %s", msg->header.frame_id.c_str(), ex.what());
    return;
  }

  auto quality = evaluator_.evaluate(*msg, tf_stamped);
  if (!quality.has_value()) {
    return;
  }

  std_msgs::msg::Float32 q_msg;
  q_msg.data = quality.value();
  quality_pub_->publish(q_msg);

  double stamp_sec = rclcpp::Time(msg->header.stamp).seconds();
  if (stamp_sec <= 0.0) {
    stamp_sec = this->now().seconds();
  }

  auto state = detector_.update(quality.value(), stamp_sec);
  if (state != LocalizationHealthState::UNKNOWN) {
    std_msgs::msg::Bool lost_msg;
    lost_msg.data = (state == LocalizationHealthState::LOST);
    lost_pub_->publish(lost_msg);
  }
}

}  // namespace mobile_base_localization
