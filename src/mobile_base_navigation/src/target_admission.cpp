// Copyright 2026 mobile_base developer
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

#include "mobile_base_navigation/target_admission.hpp"

#include <yaml-cpp/yaml.h>

#include <cctype>
#include <fstream>
#include <sstream>

#include "rclcpp/time.hpp"

namespace mobile_base_navigation
{

TargetAdmission::TargetAdmission(const std::string & catalog_path)
{
  load_station_catalog(catalog_path);
}

bool TargetAdmission::load_station_catalog(
  const std::string & catalog_path,
  std::string * error_msg)
{
  std::ifstream ifs(catalog_path);
  if (!ifs.is_open()) {
    clear_stations();
    std::string err = "Failed to open station catalog file: " + catalog_path;
    if (error_msg) {
      *error_msg = err;
    }
    catalog_loaded_ = false;
    return false;
  }

  std::stringstream ss;
  ss << ifs.rdbuf();
  return load_station_catalog_from_string(ss.str(), error_msg);
}

bool TargetAdmission::load_station_catalog_from_string(
  const std::string & yaml_content,
  std::string * error_msg)
{
  clear_stations();

  const auto reject_catalog = [this, error_msg](const std::string & error) {
      clear_stations();
      if (error_msg) {
        *error_msg = error;
      }
      return false;
    };

  try {
    YAML::Node root = YAML::Load(yaml_content);
    if (!root || !root.IsMap()) {
      return reject_catalog("Station catalog root must be a YAML map.");
    }

    for (const auto & field : root) {
      const auto key = field.first.as<std::string>();
      if (key != "frame_id" && key != "stations") {
        return reject_catalog("Unknown root field in station catalog: " + key);
      }
    }

    if (!root["frame_id"] || !root["frame_id"].IsScalar()) {
      return reject_catalog("Station catalog requires scalar 'frame_id'.");
    }
    const auto frame_id = root["frame_id"].as<std::string>();
    if (frame_id != "map") {
      return reject_catalog("Station catalog frame_id must be exactly 'map'.");
    }

    if (!root["stations"] || !root["stations"].IsSequence()) {
      return reject_catalog("Station catalog must contain a 'stations' sequence.");
    }
    if (root["stations"].size() == 0u) {
      return reject_catalog("Station catalog 'stations' sequence must not be empty.");
    }

    std::unordered_map<std::string, StationEntry> parsed_stations;
    for (const auto & item : root["stations"]) {
      if (!item.IsMap()) {
        return reject_catalog("Station entry must be a map.");
      }

      for (const auto & field : item) {
        const auto key = field.first.as<std::string>();
        if (key != "id" && key != "x" && key != "y" && key != "yaw_rad") {
          return reject_catalog("Unknown station field: " + key);
        }
      }

      if (!item["id"] || !item["x"] || !item["y"] || !item["yaw_rad"]) {
        return reject_catalog("Station entry missing required fields (id, x, y, yaw_rad).");
      }

      StationEntry entry;
      entry.name = item["id"].as<std::string>();
      if (entry.name.empty()) {
        return reject_catalog("Station ID cannot be empty.");
      }
      if (
        std::isspace(static_cast<unsigned char>(entry.name.front())) ||
        std::isspace(static_cast<unsigned char>(entry.name.back())))
      {
        return reject_catalog("Station ID cannot contain leading or trailing whitespace.");
      }

      entry.x = item["x"].as<double>();
      entry.y = item["y"].as<double>();
      entry.yaw = item["yaw_rad"].as<double>();

      if (!std::isfinite(entry.x) || !std::isfinite(entry.y) || !std::isfinite(entry.yaw)) {
        return reject_catalog(
          "Station '" + entry.name + "' contains non-finite x, y, or yaw_rad.");
      }

      if (parsed_stations.find(entry.name) != parsed_stations.end()) {
        return reject_catalog("Duplicate Station ID: " + entry.name);
      }

      parsed_stations.emplace(entry.name, entry);
    }

    stations_ = std::move(parsed_stations);
    catalog_loaded_ = true;
    return true;
  } catch (const std::exception & e) {
    return reject_catalog(std::string("YAML parsing error: ") + e.what());
  }
}

AdmissionResult TargetAdmission::admit_target(const TargetInput & input) const
{
  if (std::holds_alternative<std::monostate>(input)) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_EMPTY_TARGET,
      "Target input is empty (monostate).");
  }

  if (std::holds_alternative<GoalPoseTarget>(input)) {
    const auto & gp = std::get<GoalPoseTarget>(input);
    return admit_goal_pose(gp.x, gp.y, gp.yaw_deg, gp.frame_id);
  }

  if (std::holds_alternative<StationTarget>(input)) {
    const auto & st = std::get<StationTarget>(input);
    return admit_station(st.station_id);
  }

  return AdmissionResult::reject(
    AdmissionStatus::REJECTED_UNKNOWN_TARGET_TYPE,
    "Unknown target variant type.");
}

AdmissionResult TargetAdmission::admit_goal_pose(
  double x, double y, double yaw_deg,
  const std::string & frame_id) const
{
  auto norm_res = normalize_goal_pose(x, y, yaw_deg, frame_id);
  if (!norm_res.admitted) {
    return norm_res;
  }

  auto val_res = validate_canonical_pose(*norm_res.canonical_pose, frame_id);
  if (!val_res.admitted) {
    return val_res;
  }

  return AdmissionResult::success(
    *norm_res.canonical_pose,
    "Goal pose admitted successfully.");
}

AdmissionResult TargetAdmission::admit_station(const std::string & station_id) const
{
  auto res_res = resolve_station(station_id);
  if (!res_res.admitted) {
    return res_res;
  }

  auto val_res = validate_canonical_pose(*res_res.canonical_pose, "map");
  if (!val_res.admitted) {
    return val_res;
  }

  return AdmissionResult::success(
    *res_res.canonical_pose,
    "Station '" + station_id + "' admitted successfully.");
}

AdmissionResult TargetAdmission::normalize_goal_pose(
  double x, double y, double yaw_deg,
  const std::string & frame_id)
{
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(yaw_deg)) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_NON_FINITE_COORDINATES,
      "Goal pose contains non-finite coordinate values (NaN or Inf).");
  }

  if (frame_id.empty()) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_EMPTY_FRAME_ID,
      "Goal pose frame_id cannot be empty.");
  }

  const double yaw_rad = yaw_deg * (M_PI / 180.0);
  const double half_yaw = yaw_rad * 0.5;
  const double qz = std::sin(half_yaw);
  const double qw = std::cos(half_yaw);

  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = frame_id;
  pose.header.stamp = rclcpp::Time(0, 0, RCL_ROS_TIME);
  pose.pose.position.x = x;
  pose.pose.position.y = y;
  pose.pose.position.z = 0.0;
  pose.pose.orientation.x = 0.0;
  pose.pose.orientation.y = 0.0;
  pose.pose.orientation.z = qz;
  pose.pose.orientation.w = qw;

  return AdmissionResult::success(pose, "Goal pose normalized successfully.");
}

AdmissionResult TargetAdmission::resolve_station(const std::string & station_id) const
{
  if (station_id.empty()) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_EMPTY_STATION_ID,
      "Station ID cannot be empty.");
  }

  if (!catalog_loaded_ || stations_.empty()) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_CATALOG_UNAVAILABLE,
      "Station catalog is not loaded or contains no stations.");
  }

  auto it = stations_.find(station_id);
  if (it == stations_.end()) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_STATION_NOT_FOUND,
      "Station '" + station_id + "' was not found in station catalog.");
  }

  const auto & station = it->second;
  const double half_yaw = station.yaw * 0.5;
  const double qz = std::sin(half_yaw);
  const double qw = std::cos(half_yaw);

  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "map";
  pose.header.stamp = rclcpp::Time(0, 0, RCL_ROS_TIME);
  pose.pose.position.x = station.x;
  pose.pose.position.y = station.y;
  pose.pose.position.z = 0.0;
  pose.pose.orientation.x = 0.0;
  pose.pose.orientation.y = 0.0;
  pose.pose.orientation.z = qz;
  pose.pose.orientation.w = qw;

  return validate_canonical_pose(pose, "map");
}

AdmissionResult TargetAdmission::validate_canonical_pose(
  const geometry_msgs::msg::PoseStamped & pose,
  const std::string & expected_frame)
{
  const auto & p = pose.pose.position;
  const auto & q = pose.pose.orientation;

  if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_NON_FINITE_COORDINATES,
      "Canonical pose position contains non-finite coordinates (NaN or Inf).");
  }

  if (!std::isfinite(q.x) || !std::isfinite(q.y) || !std::isfinite(q.z) || !std::isfinite(q.w)) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_NON_FINITE_COORDINATES,
      "Canonical pose orientation contains non-finite coordinates (NaN or Inf).");
  }

  if (pose.header.frame_id.empty()) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_EMPTY_FRAME_ID,
      "Canonical pose frame_id cannot be empty.");
  }

  if (!expected_frame.empty() && pose.header.frame_id != expected_frame) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_INVALID_FRAME_ID,
      "Canonical pose frame_id '" + pose.header.frame_id + "' does not match expected frame '" +
      expected_frame + "'.");
  }

  const double norm_sq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
  if (norm_sq < 1e-6 || std::abs(norm_sq - 1.0) > 1e-3) {
    return AdmissionResult::reject(
      AdmissionStatus::REJECTED_INVALID_QUATERNION,
      "Canonical pose quaternion is invalid or not normalized.");
  }

  return AdmissionResult::success(pose, "Canonical pose validated successfully.");
}

size_t TargetAdmission::station_count() const
{
  return stations_.size();
}

bool TargetAdmission::has_station(const std::string & station_id) const
{
  return stations_.find(station_id) != stations_.end();
}

std::optional<StationEntry> TargetAdmission::get_station(const std::string & station_id) const
{
  auto it = stations_.find(station_id);
  if (it != stations_.end()) {
    return it->second;
  }
  return std::nullopt;
}

const std::unordered_map<std::string, StationEntry> & TargetAdmission::get_all_stations() const
{
  return stations_;
}

void TargetAdmission::clear_stations()
{
  stations_.clear();
  catalog_loaded_ = false;
  catalog_namespace_.clear();
  catalog_version_.clear();
}

}  // namespace mobile_base_navigation
