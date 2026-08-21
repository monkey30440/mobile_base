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

#ifndef MOBILE_BASE_NAVIGATION__TARGET_ADMISSION_HPP_
#define MOBILE_BASE_NAVIGATION__TARGET_ADMISSION_HPP_

#include <cmath>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <utility>
#include <variant>

#include "geometry_msgs/msg/pose_stamped.hpp"

namespace mobile_base_navigation
{

/**
 * @brief Admission status code distinguishing success from deterministic rejection reasons.
 */
enum class AdmissionStatus
{
  SUCCESS = 0,
  REJECTED_EMPTY_TARGET,
  REJECTED_EMPTY_STATION_ID,
  REJECTED_STATION_NOT_FOUND,
  REJECTED_CATALOG_UNAVAILABLE,
  REJECTED_CATALOG_MALFORMED,
  REJECTED_NON_FINITE_COORDINATES,
  REJECTED_EMPTY_FRAME_ID,
  REJECTED_INVALID_FRAME_ID,
  REJECTED_INVALID_QUATERNION,
  REJECTED_UNKNOWN_TARGET_TYPE
};

/**
 * @brief Helper string conversion for AdmissionStatus.
 */
inline const char * to_string(AdmissionStatus status)
{
  switch (status) {
    case AdmissionStatus::SUCCESS:
      return "SUCCESS";
    case AdmissionStatus::REJECTED_EMPTY_TARGET:
      return "REJECTED_EMPTY_TARGET";
    case AdmissionStatus::REJECTED_EMPTY_STATION_ID:
      return "REJECTED_EMPTY_STATION_ID";
    case AdmissionStatus::REJECTED_STATION_NOT_FOUND:
      return "REJECTED_STATION_NOT_FOUND";
    case AdmissionStatus::REJECTED_CATALOG_UNAVAILABLE:
      return "REJECTED_CATALOG_UNAVAILABLE";
    case AdmissionStatus::REJECTED_CATALOG_MALFORMED:
      return "REJECTED_CATALOG_MALFORMED";
    case AdmissionStatus::REJECTED_NON_FINITE_COORDINATES:
      return "REJECTED_NON_FINITE_COORDINATES";
    case AdmissionStatus::REJECTED_EMPTY_FRAME_ID:
      return "REJECTED_EMPTY_FRAME_ID";
    case AdmissionStatus::REJECTED_INVALID_FRAME_ID:
      return "REJECTED_INVALID_FRAME_ID";
    case AdmissionStatus::REJECTED_INVALID_QUATERNION:
      return "REJECTED_INVALID_QUATERNION";
    case AdmissionStatus::REJECTED_UNKNOWN_TARGET_TYPE:
      return "REJECTED_UNKNOWN_TARGET_TYPE";
    default:
      return "UNKNOWN_STATUS";
  }
}

/**
 * @brief Result object returned by all admission and validation operations.
 *
 * Guarantees that canonical_pose is only present if admitted is true.
 */
struct AdmissionResult
{
  bool admitted{false};
  AdmissionStatus status{AdmissionStatus::REJECTED_EMPTY_TARGET};
  std::string message;
  std::optional<geometry_msgs::msg::PoseStamped> canonical_pose;

  static AdmissionResult success(
    const geometry_msgs::msg::PoseStamped & pose,
    const std::string & msg = "Target admitted successfully")
  {
    AdmissionResult res;
    res.admitted = true;
    res.status = AdmissionStatus::SUCCESS;
    res.message = msg;
    res.canonical_pose = pose;
    return res;
  }

  static AdmissionResult reject(
    AdmissionStatus status,
    const std::string & msg)
  {
    AdmissionResult res;
    res.admitted = false;
    res.status = status;
    res.message = msg;
    res.canonical_pose = std::nullopt;
    return res;
  }
};

/**
 * @brief Input payload for Goal Pose targets (SYS-008, SYS-009).
 */
struct GoalPoseTarget
{
  double x{0.0};
  double y{0.0};
  double yaw_deg{0.0};
  std::string frame_id{"map"};
};

/**
 * @brief Input payload for Station targets (SYS-008, SYS-032).
 */
struct StationTarget
{
  std::string station_id;
};

/**
 * @brief Unified target input variant (SYS-008 GAP-01).
 */
using TargetInput = std::variant<std::monostate, GoalPoseTarget, StationTarget>;

/**
 * @brief Station definition parsed from authoritative station catalog (06 §4.1).
 */
struct StationEntry
{
  std::string name;
  double x{0.0};
  double y{0.0};
  double yaw{0.0};  // In radians per 06 §4.1 schema
  std::string description;
};

/**
 * @brief Target Admission thin module implementing GAP-01 to GAP-04 (SYS-008, SYS-009, SYS-032, SYS-033).
 */
class TargetAdmission
{
public:
  TargetAdmission() = default;
  explicit TargetAdmission(const std::string & catalog_path);

  /**
   * @brief Load station catalog from YAML file (06 §4.1 schema).
   */
  bool load_station_catalog(const std::string & catalog_path, std::string * error_msg = nullptr);

  /**
   * @brief Load station catalog from YAML formatted string.
   */
  bool load_station_catalog_from_string(
    const std::string & yaml_content,
    std::string * error_msg = nullptr);

  /**
   * @brief GAP-01: Target Discriminator and unified entrypoint (SYS-008).
   */
  AdmissionResult admit_target(const TargetInput & input) const;

  /**
   * @brief Convenience entrypoint for Goal Pose admission (SYS-008, SYS-009, SYS-033).
   */
  AdmissionResult admit_goal_pose(
    double x, double y, double yaw_deg,
    const std::string & frame_id = "map") const;

  /**
   * @brief Convenience entrypoint for Station admission (SYS-008, SYS-032, SYS-033).
   */
  AdmissionResult admit_station(const std::string & station_id) const;

  /**
   * @brief GAP-02: Goal Pose Normalizer (SYS-009).
   * Converts (x, y, yaw_deg) into canonical PoseStamped with quaternion orientation.
   */
  static AdmissionResult normalize_goal_pose(
    double x, double y, double yaw_deg,
    const std::string & frame_id = "map");

  /**
   * @brief GAP-03: Station Catalog Resolver (SYS-032).
   * Exact-matches station_id against loaded catalog and produces canonical PoseStamped.
   */
  AdmissionResult resolve_station(const std::string & station_id) const;

  /**
   * @brief GAP-04: Canonical Goal Pose Validator (SYS-033).
   * Validates finite coordinates, non-empty/correct frame_id, and valid normalized quaternion.
   */
  static AdmissionResult validate_canonical_pose(
    const geometry_msgs::msg::PoseStamped & pose,
    const std::string & expected_frame = "map");

  /**
   * @brief Get count of loaded stations.
   */
  size_t station_count() const;

  /**
   * @brief Check whether catalog contains exact station ID.
   */
  bool has_station(const std::string & station_id) const;

  /**
   * @brief Get station definition if present.
   */
  std::optional<StationEntry> get_station(const std::string & station_id) const;

  /**
   * @brief Get all loaded stations.
   */
  const std::unordered_map<std::string, StationEntry> & get_all_stations() const;

  /**
   * @brief Clear all loaded stations.
   */
  void clear_stations();

private:
  std::unordered_map<std::string, StationEntry> stations_;
  std::string catalog_namespace_;
  std::string catalog_version_;
  bool catalog_loaded_{false};
};

}  // namespace mobile_base_navigation

#endif  // MOBILE_BASE_NAVIGATION__TARGET_ADMISSION_HPP_
