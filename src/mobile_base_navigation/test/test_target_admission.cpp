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

#include <gtest/gtest.h>
#include <cmath>
#include <limits>
#include <string>

#include "mobile_base_navigation/target_admission.hpp"

using mobile_base_navigation::AdmissionResult;
using mobile_base_navigation::AdmissionStatus;
using mobile_base_navigation::GoalPoseTarget;
using mobile_base_navigation::StationTarget;
using mobile_base_navigation::TargetAdmission;
using mobile_base_navigation::TargetInput;

static const char kValidCatalogYaml[] =
  "version: \"1.0.0\"\n"
  "namespace: \"test_factory\"\n"
  "stations:\n"
  "  - name: \"STATION_A\"\n"
  "    x: 2.50\n"
  "    y: 1.20\n"
  "    yaw: 0.0\n"
  "    metadata:\n"
  "      description: \"Loading dock 1\"\n"
  "  - name: \"STATION_B\"\n"
  "    x: 8.00\n"
  "    y: 5.50\n"
  "    yaw: 1.57079632679\n"
  "    metadata:\n"
  "      description: \"Unloading dock 2\"\n";

/* =========================================================================
 * 1. Goal Pose Normalization Tests (SYS-009 / GAP-02)
 * ========================================================================= */

TEST(TargetAdmissionGoalPose, NormalizesZeroHeading)
{
  auto res = TargetAdmission::normalize_goal_pose(0.0, 0.0, 0.0, "map");
  ASSERT_TRUE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::SUCCESS);
  ASSERT_TRUE(res.canonical_pose.has_value());

  const auto & pose = *res.canonical_pose;
  EXPECT_EQ(pose.header.frame_id, "map");
  EXPECT_DOUBLE_EQ(pose.pose.position.x, 0.0);
  EXPECT_DOUBLE_EQ(pose.pose.position.y, 0.0);
  EXPECT_DOUBLE_EQ(pose.pose.position.z, 0.0);
  EXPECT_DOUBLE_EQ(pose.pose.orientation.x, 0.0);
  EXPECT_DOUBLE_EQ(pose.pose.orientation.y, 0.0);
  EXPECT_DOUBLE_EQ(pose.pose.orientation.z, 0.0);
  EXPECT_DOUBLE_EQ(pose.pose.orientation.w, 1.0);
}

TEST(TargetAdmissionGoalPose, Normalizes90DegreeHeading)
{
  auto res = TargetAdmission::normalize_goal_pose(2.5, -1.2, 90.0, "map");
  ASSERT_TRUE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::SUCCESS);
  ASSERT_TRUE(res.canonical_pose.has_value());

  const auto & pose = *res.canonical_pose;
  EXPECT_DOUBLE_EQ(pose.pose.position.x, 2.5);
  EXPECT_DOUBLE_EQ(pose.pose.position.y, -1.2);
  EXPECT_NEAR(pose.pose.orientation.z, std::sin(M_PI / 4.0), 1e-6);
  EXPECT_NEAR(pose.pose.orientation.w, std::cos(M_PI / 4.0), 1e-6);
}

TEST(TargetAdmissionGoalPose, NormalizesNegativeAngle)
{
  auto res = TargetAdmission::normalize_goal_pose(-3.0, 4.0, -90.0, "map");
  ASSERT_TRUE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::SUCCESS);
  ASSERT_TRUE(res.canonical_pose.has_value());

  const auto & pose = *res.canonical_pose;
  EXPECT_NEAR(pose.pose.orientation.z, -std::sin(M_PI / 4.0), 1e-6);
  EXPECT_NEAR(pose.pose.orientation.w, std::cos(M_PI / 4.0), 1e-6);
}

TEST(TargetAdmissionGoalPose, RejectsNonFiniteCoordinates)
{
  const double nan_val = std::numeric_limits<double>::quiet_NaN();
  const double inf_val = std::numeric_limits<double>::infinity();

  auto res_nan_x = TargetAdmission::normalize_goal_pose(nan_val, 1.0, 0.0);
  EXPECT_FALSE(res_nan_x.admitted);
  EXPECT_EQ(res_nan_x.status, AdmissionStatus::REJECTED_NON_FINITE_COORDINATES);
  EXPECT_FALSE(res_nan_x.canonical_pose.has_value());

  auto res_inf_y = TargetAdmission::normalize_goal_pose(1.0, inf_val, 0.0);
  EXPECT_FALSE(res_inf_y.admitted);
  EXPECT_EQ(res_inf_y.status, AdmissionStatus::REJECTED_NON_FINITE_COORDINATES);

  auto res_nan_yaw = TargetAdmission::normalize_goal_pose(1.0, 1.0, nan_val);
  EXPECT_FALSE(res_nan_yaw.admitted);
  EXPECT_EQ(res_nan_yaw.status, AdmissionStatus::REJECTED_NON_FINITE_COORDINATES);
}

TEST(TargetAdmissionGoalPose, RejectsEmptyFrameId)
{
  auto res = TargetAdmission::normalize_goal_pose(1.0, 2.0, 45.0, "");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_EMPTY_FRAME_ID);
  EXPECT_FALSE(res.canonical_pose.has_value());
}

/* =========================================================================
 * 2. Station Resolution Tests (SYS-032 / GAP-03)
 * ========================================================================= */

TEST(TargetAdmissionStation, LoadsValidCatalog)
{
  TargetAdmission admission;
  std::string err;
  EXPECT_TRUE(admission.load_station_catalog_from_string(kValidCatalogYaml, &err)) << err;
  EXPECT_EQ(admission.station_count(), 2u);
  EXPECT_TRUE(admission.has_station("STATION_A"));
  EXPECT_TRUE(admission.has_station("STATION_B"));
  EXPECT_FALSE(admission.has_station("STATION_UNKNOWN"));
}

TEST(TargetAdmissionStation, ResolvesExactMatchStation)
{
  TargetAdmission admission;
  ASSERT_TRUE(admission.load_station_catalog_from_string(kValidCatalogYaml));

  auto res_a = admission.resolve_station("STATION_A");
  ASSERT_TRUE(res_a.admitted);
  EXPECT_EQ(res_a.status, AdmissionStatus::SUCCESS);
  ASSERT_TRUE(res_a.canonical_pose.has_value());
  EXPECT_EQ(res_a.canonical_pose->header.frame_id, "map");
  EXPECT_DOUBLE_EQ(res_a.canonical_pose->pose.position.x, 2.50);
  EXPECT_DOUBLE_EQ(res_a.canonical_pose->pose.position.y, 1.20);
  EXPECT_DOUBLE_EQ(res_a.canonical_pose->pose.orientation.w, 1.0);

  auto res_b = admission.resolve_station("STATION_B");
  ASSERT_TRUE(res_b.admitted);
  EXPECT_DOUBLE_EQ(res_b.canonical_pose->pose.position.x, 8.00);
  EXPECT_DOUBLE_EQ(res_b.canonical_pose->pose.position.y, 5.50);
  EXPECT_NEAR(res_b.canonical_pose->pose.orientation.z, std::sin(M_PI / 4.0), 1e-6);
  EXPECT_NEAR(res_b.canonical_pose->pose.orientation.w, std::cos(M_PI / 4.0), 1e-6);
}

TEST(TargetAdmissionStation, LoadsValidCatalogFromFile)
{
#ifdef TEST_DATA_DIR
  TargetAdmission admission;
  std::string fixture_path = std::string(TEST_DATA_DIR) + "/test_station_catalog.yaml";
  std::string err;
  EXPECT_TRUE(admission.load_station_catalog(fixture_path, &err)) << err;
  EXPECT_EQ(admission.station_count(), 2u);
  EXPECT_TRUE(admission.has_station("STATION_A"));
  EXPECT_TRUE(admission.has_station("STATION_B"));

  auto res = admission.resolve_station("STATION_A");
  ASSERT_TRUE(res.admitted);
  EXPECT_DOUBLE_EQ(res.canonical_pose->pose.position.x, 2.50);
#endif
}

TEST(TargetAdmissionStation, RejectsMalformedCatalogFile)
{
#ifdef TEST_DATA_DIR
  TargetAdmission admission;
  std::string fixture_path = std::string(TEST_DATA_DIR) + "/malformed_station_catalog.yaml";
  std::string err;
  EXPECT_FALSE(admission.load_station_catalog(fixture_path, &err));
  EXPECT_EQ(admission.station_count(), 0u);
#endif
}

TEST(TargetAdmissionStation, RejectsNonExistentCatalogFile)
{
#ifdef TEST_DATA_DIR
  TargetAdmission admission;
  std::string fixture_path = std::string(TEST_DATA_DIR) + "/non_existent_catalog.yaml";
  std::string err;
  EXPECT_FALSE(admission.load_station_catalog(fixture_path, &err));
  EXPECT_EQ(admission.station_count(), 0u);
#endif
}

TEST(TargetAdmissionStation, RejectsEmptyStationId)
{
  TargetAdmission admission;
  ASSERT_TRUE(admission.load_station_catalog_from_string(kValidCatalogYaml));

  auto res = admission.resolve_station("");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_EMPTY_STATION_ID);
  EXPECT_FALSE(res.canonical_pose.has_value());
}

TEST(TargetAdmissionStation, RejectsUnknownStation)
{
  TargetAdmission admission;
  ASSERT_TRUE(admission.load_station_catalog_from_string(kValidCatalogYaml));

  auto res = admission.resolve_station("STATION_NON_EXISTENT");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_STATION_NOT_FOUND);
  EXPECT_FALSE(res.canonical_pose.has_value());
}

TEST(TargetAdmissionStation, RejectsWhenCatalogNotLoaded)
{
  TargetAdmission admission;
  auto res = admission.resolve_station("STATION_A");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_CATALOG_UNAVAILABLE);
  EXPECT_FALSE(res.canonical_pose.has_value());
}

TEST(TargetAdmissionStation, RejectsMalformedCatalog)
{
  TargetAdmission admission;
  std::string malformed_yaml = "stations: not_a_list";
  std::string err;
  EXPECT_FALSE(admission.load_station_catalog_from_string(malformed_yaml, &err));
  EXPECT_EQ(admission.station_count(), 0u);
}

/* =========================================================================
 * 3. Canonical Pose Validation Tests (SYS-033 / GAP-04)
 * ========================================================================= */

TEST(TargetAdmissionValidation, ValidatesCanonicalPose)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "map";
  pose.pose.position.x = 1.0;
  pose.pose.position.y = 2.0;
  pose.pose.position.z = 0.0;
  pose.pose.orientation.x = 0.0;
  pose.pose.orientation.y = 0.0;
  pose.pose.orientation.z = 0.0;
  pose.pose.orientation.w = 1.0;

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_TRUE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::SUCCESS);
}

TEST(TargetAdmissionValidation, RejectsNonFinitePosition)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "map";
  pose.pose.position.x = std::numeric_limits<double>::quiet_NaN();
  pose.pose.orientation.w = 1.0;

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_NON_FINITE_COORDINATES);
}

TEST(TargetAdmissionValidation, RejectsNonFiniteOrientation)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "map";
  pose.pose.position.x = 1.0;
  pose.pose.orientation.w = std::numeric_limits<double>::infinity();

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_NON_FINITE_COORDINATES);
}

TEST(TargetAdmissionValidation, RejectsEmptyFrame)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "";
  pose.pose.orientation.w = 1.0;

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_EMPTY_FRAME_ID);
}

TEST(TargetAdmissionValidation, RejectsFrameMismatch)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "odom";
  pose.pose.orientation.w = 1.0;

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_INVALID_FRAME_ID);
}

TEST(TargetAdmissionValidation, RejectsZeroQuaternion)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "map";
  pose.pose.orientation.x = 0.0;
  pose.pose.orientation.y = 0.0;
  pose.pose.orientation.z = 0.0;
  pose.pose.orientation.w = 0.0;

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_INVALID_QUATERNION);
}

TEST(TargetAdmissionValidation, RejectsUnnormalizedQuaternion)
{
  geometry_msgs::msg::PoseStamped pose;
  pose.header.frame_id = "map";
  pose.pose.orientation.x = 0.5;
  pose.pose.orientation.y = 0.5;
  pose.pose.orientation.z = 0.0;
  pose.pose.orientation.w = 0.5;  // Norm^2 = 0.75, not 1.0

  auto res = TargetAdmission::validate_canonical_pose(pose, "map");
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_INVALID_QUATERNION);
}

/* =========================================================================
 * 4. Target Discriminator & Top-Level Admission Tests (SYS-008 / GAP-01)
 * ========================================================================= */

TEST(TargetAdmissionDiscriminator, AdmitsGoalPoseTarget)
{
  TargetAdmission admission;
  TargetInput input = GoalPoseTarget{3.0, 4.0, 180.0, "map"};

  auto res = admission.admit_target(input);
  ASSERT_TRUE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::SUCCESS);
  ASSERT_TRUE(res.canonical_pose.has_value());
  EXPECT_DOUBLE_EQ(res.canonical_pose->pose.position.x, 3.0);
  EXPECT_DOUBLE_EQ(res.canonical_pose->pose.position.y, 4.0);
  EXPECT_NEAR(res.canonical_pose->pose.orientation.z, 1.0, 1e-6);
  EXPECT_NEAR(res.canonical_pose->pose.orientation.w, 0.0, 1e-6);
}

TEST(TargetAdmissionDiscriminator, AdmitsStationTarget)
{
  TargetAdmission admission;
  ASSERT_TRUE(admission.load_station_catalog_from_string(kValidCatalogYaml));
  TargetInput input = StationTarget{"STATION_A"};

  auto res = admission.admit_target(input);
  ASSERT_TRUE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::SUCCESS);
  ASSERT_TRUE(res.canonical_pose.has_value());
  EXPECT_DOUBLE_EQ(res.canonical_pose->pose.position.x, 2.50);
  EXPECT_DOUBLE_EQ(res.canonical_pose->pose.position.y, 1.20);
}

TEST(TargetAdmissionDiscriminator, RejectsEmptyTarget)
{
  TargetAdmission admission;
  TargetInput input = std::monostate{};

  auto res = admission.admit_target(input);
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_EMPTY_TARGET);
  EXPECT_FALSE(res.canonical_pose.has_value());
}

TEST(TargetAdmissionDiscriminator, RejectsInvalidGoalPoseTarget)
{
  TargetAdmission admission;
  TargetInput input = GoalPoseTarget{std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0, "map"};

  auto res = admission.admit_target(input);
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_NON_FINITE_COORDINATES);
  EXPECT_FALSE(res.canonical_pose.has_value());
}

TEST(TargetAdmissionDiscriminator, RejectsInvalidStationTarget)
{
  TargetAdmission admission;
  ASSERT_TRUE(admission.load_station_catalog_from_string(kValidCatalogYaml));
  TargetInput input = StationTarget{"UNKNOWN_STATION"};

  auto res = admission.admit_target(input);
  EXPECT_FALSE(res.admitted);
  EXPECT_EQ(res.status, AdmissionStatus::REJECTED_STATION_NOT_FOUND);
  EXPECT_FALSE(res.canonical_pose.has_value());
}
