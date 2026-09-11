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

#ifndef MOBILE_BASE_LOCALIZATION__LOCALIZATION_MONITOR_HPP_
#define MOBILE_BASE_LOCALIZATION__LOCALIZATION_MONITOR_HPP_

#include <memory>
#include <optional>
#include <string>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_msgs/msg/float32.hpp"
#include "tf2/LinearMath/Transform.h"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"

namespace mobile_base_localization
{

struct ScanMapQualityEvaluatorConfig
{
  double match_dist_m{0.15};
  int occupied_threshold{65};
  int min_valid_beams{30};
  int beam_stride{1};

  void validate() const;
};

class ScanMapQualityEvaluator
{
public:
  explicit ScanMapQualityEvaluator(
    const ScanMapQualityEvaluatorConfig & config = ScanMapQualityEvaluatorConfig{});

  bool set_map(const nav_msgs::msg::OccupancyGrid & map_msg);
  bool has_map() const;

  std::optional<float> evaluate(
    const sensor_msgs::msg::LaserScan & scan_msg,
    const geometry_msgs::msg::TransformStamped & tf_map_to_scan) const;

  std::optional<float> evaluate(
    const sensor_msgs::msg::LaserScan & scan_msg,
    const tf2::Transform & tf_map_to_scan) const;

  const ScanMapQualityEvaluatorConfig & get_config() const {return config_;}
  void set_config(const ScanMapQualityEvaluatorConfig & config);

private:
  ScanMapQualityEvaluatorConfig config_;
  bool has_map_{false};
  nav_msgs::msg::MapMetaData map_info_;
  cv::Mat dist_field_;  // Distance in pixels to nearest occupied cell
};

enum class LocalizationHealthState
{
  UNKNOWN,
  OK,
  LOST
};

struct LocalizationLostDetectorConfig
{
  double lost_ratio{0.35};
  double recover_ratio{0.60};
  double lost_hold_s{1.5};
  double recover_hold_s{1.5};

  void validate() const;
};

class LocalizationLostDetector
{
public:
  explicit LocalizationLostDetector(
    const LocalizationLostDetectorConfig & config = LocalizationLostDetectorConfig{});

  LocalizationHealthState update(float quality, double current_time);
  LocalizationHealthState get_state() const {return current_state_;}
  void reset();

  const LocalizationLostDetectorConfig & get_config() const {return config_;}
  void set_config(const LocalizationLostDetectorConfig & config);

private:
  LocalizationLostDetectorConfig config_;
  LocalizationHealthState current_state_{LocalizationHealthState::UNKNOWN};
  std::optional<double> low_quality_start_time_;
  std::optional<double> high_quality_start_time_;
  std::optional<double> last_measurement_time_;
};

class LocalizationMonitorNode : public rclcpp::Node
{
public:
  explicit LocalizationMonitorNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions{});

private:
  void map_callback(const nav_msgs::msg::OccupancyGrid::ConstSharedPtr msg);
  void scan_callback(const sensor_msgs::msg::LaserScan::ConstSharedPtr msg);

  ScanMapQualityEvaluator evaluator_;
  LocalizationLostDetector detector_;

  double tf_timeout_s_{0.1};

  std::shared_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;

  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr map_sub_;
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;

  rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr quality_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr lost_pub_;
};

}  // namespace mobile_base_localization

#endif  // MOBILE_BASE_LOCALIZATION__LOCALIZATION_MONITOR_HPP_
