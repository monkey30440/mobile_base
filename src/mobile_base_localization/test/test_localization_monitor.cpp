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

#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <memory>
#include <string>
#include <thread>
#include <limits>
#include <stdexcept>
#include <vector>

#include "mobile_base_localization/localization_monitor.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2/LinearMath/Transform.h"

using mobile_base_localization::LocalizationHealthState;
using mobile_base_localization::LocalizationLostDetector;
using mobile_base_localization::LocalizationLostDetectorConfig;
using mobile_base_localization::ScanMapQualityEvaluator;
using mobile_base_localization::ScanMapQualityEvaluatorConfig;

namespace
{

nav_msgs::msg::OccupancyGrid create_box_map(
  int width = 100, int height = 100, double resolution = 0.05,
  double origin_x = -2.5, double origin_y = -2.5, double origin_yaw = 0.0)
{
  nav_msgs::msg::OccupancyGrid map;
  map.info.width = width;
  map.info.height = height;
  map.info.resolution = resolution;
  map.info.origin.position.x = origin_x;
  map.info.origin.position.y = origin_y;
  map.info.origin.position.z = 0.0;

  tf2::Quaternion q;
  q.setRPY(0.0, 0.0, origin_yaw);
  map.info.origin.orientation.x = q.x();
  map.info.origin.orientation.y = q.y();
  map.info.origin.orientation.z = q.z();
  map.info.origin.orientation.w = q.w();

  map.data.assign(width * height, 0);  // all free

  // Place a vertical wall at x = 1.0 m:
  // cell_x = (1.0 - origin_x) / resolution = (1.0 - (-2.5)) / 0.05 = 3.5 / 0.05 = 70
  int wall_col = static_cast<int>(std::round((1.0 - origin_x) / resolution));
  if (wall_col >= 0 && wall_col < width) {
    for (int r = 0; r < height; ++r) {
      map.data[r * width + wall_col] = 100;  // occupied
    }
  }

  return map;
}

sensor_msgs::msg::LaserScan create_scan_facing_wall(
  int num_beams = 50, float wall_distance = 1.0f,
  float angle_min = -0.5f, float angle_max = 0.5f)
{
  sensor_msgs::msg::LaserScan scan;
  scan.header.frame_id = "base_lidar_link_FL_1";
  scan.angle_min = angle_min;
  scan.angle_max = angle_max;
  scan.angle_increment = (num_beams > 1) ? ((angle_max - angle_min) / (num_beams - 1)) : 0.0f;
  scan.range_min = 0.05f;
  scan.range_max = 20.0f;
  scan.ranges.resize(num_beams);

  for (int i = 0; i < num_beams; ++i) {
    float angle = scan.angle_min + i * scan.angle_increment;
    // For a flat vertical wall at x = wall_distance:
    // x = r * cos(angle) = wall_distance => r = wall_distance / cos(angle)
    scan.ranges[i] = wall_distance / std::cos(angle);
  }
  return scan;
}

tf2::Transform identity_transform()
{
  tf2::Transform tf;
  tf.setIdentity();
  return tf;
}

}  // namespace

// 1. perfect/strong map match gives high quality
TEST(TestLocalizationMonitor, PerfectStrongMapMatchGivesHighQuality)
{
  ScanMapQualityEvaluatorConfig config;
  config.match_dist_m = 0.15;
  config.occupied_threshold = 65;
  config.min_valid_beams = 30;
  config.beam_stride = 1;

  ScanMapQualityEvaluator evaluator(config);
  auto map = create_box_map();
  EXPECT_TRUE(evaluator.set_map(map));

  auto scan = create_scan_facing_wall(50, 1.0f);
  auto tf = identity_transform();

  auto quality = evaluator.evaluate(scan, tf);
  ASSERT_TRUE(quality.has_value());
  EXPECT_GE(quality.value(), 0.95f);
}

// 2. mismatching scan gives low quality
TEST(TestLocalizationMonitor, MismatchingScanGivesLowQuality)
{
  ScanMapQualityEvaluatorConfig config;
  config.match_dist_m = 0.15;
  config.occupied_threshold = 65;
  config.min_valid_beams = 30;

  ScanMapQualityEvaluator evaluator(config);
  auto map = create_box_map();
  EXPECT_TRUE(evaluator.set_map(map));

  // Scan returns endpoints at 1.8m, while wall is at 1.0m (0.8m error >> 0.15m match_dist)
  auto scan = create_scan_facing_wall(50, 1.8f);
  auto tf = identity_transform();

  auto quality = evaluator.evaluate(scan, tf);
  ASSERT_TRUE(quality.has_value());
  EXPECT_LE(quality.value(), 0.10f);
}

// 3. invalid LaserScan ranges are ignored
TEST(TestLocalizationMonitor, InvalidLaserScanRangesAreIgnored)
{
  ScanMapQualityEvaluatorConfig config;
  config.match_dist_m = 0.15;
  config.occupied_threshold = 65;
  config.min_valid_beams = 20;

  ScanMapQualityEvaluator evaluator(config);
  auto map = create_box_map();
  EXPECT_TRUE(evaluator.set_map(map));

  auto scan = create_scan_facing_wall(50, 1.0f);
  // Corrupt 20 beams with NaN, Inf, negative, < range_min, > range_max
  scan.ranges[0] = std::numeric_limits<float>::quiet_NaN();
  scan.ranges[1] = std::numeric_limits<float>::infinity();
  scan.ranges[2] = -1.0f;
  scan.ranges[3] = 0.01f;   // below range_min (0.05)
  scan.ranges[4] = 25.0f;   // above range_max (20.0)

  auto tf = identity_transform();
  auto quality = evaluator.evaluate(scan, tf);
  ASSERT_TRUE(quality.has_value());
  // The remaining 45 valid beams all hit the wall
  EXPECT_GE(quality.value(), 0.95f);
}

// 4. endpoints outside OccupancyGrid do not contaminate the denominator
TEST(TestLocalizationMonitor, EndpointsOutsideOccupancyGridDoNotContaminateDenominator)
{
  ScanMapQualityEvaluatorConfig config;
  config.match_dist_m = 0.15;
  config.occupied_threshold = 65;
  config.min_valid_beams = 20;

  ScanMapQualityEvaluator evaluator(config);
  // Map size: 5m x 5m (from -2.5 to +2.5)
  auto map = create_box_map(100, 100, 0.05, -2.5, -2.5, 0.0);
  EXPECT_TRUE(evaluator.set_map(map));

  auto scan = create_scan_facing_wall(50, 1.0f);
  // Set 15 beams to 15.0m (points at x = 15.0m, far outside the map +2.5m boundary)
  for (int i = 0; i < 15; ++i) {
    scan.ranges[i] = 15.0f;
  }

  auto tf = identity_transform();
  auto quality = evaluator.evaluate(scan, tf);
  ASSERT_TRUE(quality.has_value());
  // The 35 beams inside the map hit the wall; out-of-map beams must NOT contaminate denominator
  EXPECT_GE(quality.value(), 0.95f);
}

// 5. fewer than min_valid_beams returns no valid measurement
TEST(TestLocalizationMonitor, FewerThanMinValidBeamsReturnsNoValidMeasurement)
{
  ScanMapQualityEvaluatorConfig config;
  config.match_dist_m = 0.15;
  config.occupied_threshold = 65;
  config.min_valid_beams = 30;

  ScanMapQualityEvaluator evaluator(config);
  auto map = create_box_map();
  EXPECT_TRUE(evaluator.set_map(map));

  // Only 10 beams in scan, which is < min_valid_beams (30)
  auto scan = create_scan_facing_wall(10, 1.0f);
  auto tf = identity_transform();

  auto quality = evaluator.evaluate(scan, tf);
  EXPECT_FALSE(quality.has_value());
}

// 6. transient quality below lost_ratio does not declare LOST
TEST(TestLocalizationMonitor, TransientQualityBelowLostRatioDoesNotDeclareLost)
{
  LocalizationLostDetectorConfig config;
  config.lost_ratio = 0.35;
  config.recover_ratio = 0.60;
  config.lost_hold_s = 1.5;
  config.recover_hold_s = 1.5;

  LocalizationLostDetector detector(config);

  // Establish initial healthy state
  EXPECT_EQ(detector.update(0.90f, 0.0), LocalizationHealthState::HEALTHY);

  // Transient bad measurement at t = 1.0
  EXPECT_EQ(detector.update(0.20f, 1.0), LocalizationHealthState::HEALTHY);

  // Another bad measurement at t = 1.8 (< 1.5s hold time from t=1.0)
  EXPECT_EQ(detector.update(0.20f, 1.8), LocalizationHealthState::HEALTHY);

  // Recovers at t = 2.0
  EXPECT_EQ(detector.update(0.85f, 2.0), LocalizationHealthState::HEALTHY);

  // Another bad measurement at t = 2.5 (timer should have been reset)
  EXPECT_EQ(detector.update(0.10f, 2.5), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::HEALTHY);
}

// 7. sustained low quality declares LOST
TEST(TestLocalizationMonitor, SustainedLowQualityDeclaresLost)
{
  LocalizationLostDetectorConfig config;
  config.lost_ratio = 0.35;
  config.recover_ratio = 0.60;
  config.lost_hold_s = 1.5;
  config.recover_hold_s = 1.5;

  LocalizationLostDetector detector(config);
  EXPECT_EQ(detector.update(0.90f, 0.0), LocalizationHealthState::HEALTHY);

  // Low quality starts at t = 1.0
  EXPECT_EQ(detector.update(0.20f, 1.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.20f, 2.0), LocalizationHealthState::HEALTHY);

  // At t = 2.6s (1.6s >= 1.5s lost_hold_s), declare LOST
  EXPECT_EQ(detector.update(0.20f, 2.6), LocalizationHealthState::LOST);
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::LOST);
}

// 8. LOST does not immediately recover in hysteresis band
TEST(TestLocalizationMonitor, LostDoesNotImmediatelyRecoverInHysteresisBand)
{
  LocalizationLostDetectorConfig config;
  config.lost_ratio = 0.35;
  config.recover_ratio = 0.60;
  config.lost_hold_s = 1.0;
  config.recover_hold_s = 1.0;

  LocalizationLostDetector detector(config);
  EXPECT_EQ(detector.update(0.90f, 0.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.10f, 1.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.10f, 2.1), LocalizationHealthState::LOST);

  // Hysteresis band: quality 0.50 (0.35 <= 0.50 < 0.60)
  EXPECT_EQ(detector.update(0.50f, 2.5), LocalizationHealthState::LOST);
  EXPECT_EQ(detector.update(0.50f, 4.0), LocalizationHealthState::LOST);
  EXPECT_EQ(detector.update(0.50f, 6.0), LocalizationHealthState::LOST);
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::LOST);
}

// 9. sustained quality >= recover_ratio recovers to HEALTHY
TEST(TestLocalizationMonitor, SustainedQualityGeRecoverRatioRecoversToHealthy)
{
  LocalizationLostDetectorConfig config;
  config.lost_ratio = 0.35;
  config.recover_ratio = 0.60;
  config.lost_hold_s = 1.0;
  config.recover_hold_s = 1.5;

  LocalizationLostDetector detector(config);
  EXPECT_EQ(detector.update(0.90f, 0.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.10f, 1.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.10f, 2.1), LocalizationHealthState::LOST);

  // High quality begins at t = 3.0
  EXPECT_EQ(detector.update(0.80f, 3.0), LocalizationHealthState::LOST);
  // At t = 4.0 (1.0s < 1.5s recover_hold_s), still LOST
  EXPECT_EQ(detector.update(0.80f, 4.0), LocalizationHealthState::LOST);
  // At t = 4.6 (1.6s >= 1.5s recover_hold_s), recovers to HEALTHY
  EXPECT_EQ(detector.update(0.80f, 4.6), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::HEALTHY);
}

// Missing evidence invalidates the detector; the monitor owns the freshness timer.
TEST(TestLocalizationMonitor, UnavailableMeasurementsResetToUnknown)
{
  LocalizationLostDetector detector;
  detector.update(0.8f, 1.0);
  detector.reset();
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::UNKNOWN);
  EXPECT_EQ(detector.update(0.1f, 10.0), LocalizationHealthState::UNKNOWN);
}

// 11. map origin with unsupported non-zero yaw is rejected
TEST(TestLocalizationMonitor, MapOriginWithUnsupportedNonZeroYawIsRejected)
{
  ScanMapQualityEvaluatorConfig config;
  ScanMapQualityEvaluator evaluator(config);

  // Map with non-zero yaw (0.5 rad)
  auto map = create_box_map(100, 100, 0.05, -2.5, -2.5, 0.5);
  EXPECT_FALSE(evaluator.set_map(map));
  EXPECT_FALSE(evaluator.has_map());

  // Without a valid map, evaluate returns nullopt
  auto scan = create_scan_facing_wall(50, 1.0f);
  auto tf = identity_transform();
  EXPECT_FALSE(evaluator.evaluate(scan, tf).has_value());
}

// 12. first valid quality >= recover_ratio transitions UNKNOWN -> HEALTHY
TEST(TestLocalizationMonitor, FirstHealthyMeasurementTransitionsUnknownToHealthy)
{
  LocalizationLostDetectorConfig config;
  config.lost_ratio = 0.35;
  config.recover_ratio = 0.60;
  config.lost_hold_s = 1.5;
  config.recover_hold_s = 2.0;

  LocalizationLostDetector detector(config);
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::UNKNOWN);

  // First healthy measurement immediately establishes HEALTHY without waiting recover_hold_s
  EXPECT_EQ(detector.update(0.85f, 0.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::HEALTHY);
}

// 13. invalid beam_stride is rejected (< 1)
TEST(TestLocalizationMonitor, RejectInvalidBeamStride)
{
  ScanMapQualityEvaluatorConfig config;
  config.beam_stride = 0;
  EXPECT_THROW(ScanMapQualityEvaluator evaluator(config), std::invalid_argument);

  ScanMapQualityEvaluator evaluator;
  EXPECT_THROW(evaluator.set_config(config), std::invalid_argument);
}

// 14. invalid lost_ratio/recover_ratio relationship is rejected (lost_ratio >= recover_ratio)
TEST(TestLocalizationMonitor, RejectInvalidRatioRelationship)
{
  LocalizationLostDetectorConfig config;
  config.lost_ratio = 0.70;
  config.recover_ratio = 0.50;
  EXPECT_THROW(LocalizationLostDetector detector(config), std::invalid_argument);

  LocalizationLostDetector detector;
  EXPECT_THROW(detector.set_config(config), std::invalid_argument);
}

// 15. invalid numeric parameters are rejected
TEST(TestLocalizationMonitor, RejectInvalidNumericParameters)
{
  // occupied_threshold > 100 or < 0
  {
    ScanMapQualityEvaluatorConfig config;
    config.occupied_threshold = 150;
    EXPECT_THROW(ScanMapQualityEvaluator evaluator(config), std::invalid_argument);
  }
  {
    ScanMapQualityEvaluatorConfig config;
    config.occupied_threshold = -1;
    EXPECT_THROW(ScanMapQualityEvaluator evaluator(config), std::invalid_argument);
  }

  // match_dist_m <= 0
  {
    ScanMapQualityEvaluatorConfig config;
    config.match_dist_m = 0.0;
    EXPECT_THROW(ScanMapQualityEvaluator evaluator(config), std::invalid_argument);
  }

  // min_valid_beams <= 0
  {
    ScanMapQualityEvaluatorConfig config;
    config.min_valid_beams = 0;
    EXPECT_THROW(ScanMapQualityEvaluator evaluator(config), std::invalid_argument);
  }

  // negative hold time
  {
    LocalizationLostDetectorConfig config;
    config.lost_hold_s = -0.5;
    EXPECT_THROW(LocalizationLostDetector detector(config), std::invalid_argument);
  }
  {
    LocalizationLostDetectorConfig config;
    config.recover_hold_s = -1.0;
    EXPECT_THROW(LocalizationLostDetector detector(config), std::invalid_argument);
  }

  // lost_ratio or recover_ratio out of [0.0, 1.0]
  {
    LocalizationLostDetectorConfig config;
    config.lost_ratio = -0.1;
    EXPECT_THROW(LocalizationLostDetector detector(config), std::invalid_argument);
  }
  {
    LocalizationLostDetectorConfig config;
    config.recover_ratio = 1.5;
    EXPECT_THROW(LocalizationLostDetector detector(config), std::invalid_argument);
  }
}

TEST(TestLocalizationMonitor, InvalidAndNonAdvancingEvidenceResetsToUnknown)
{
  LocalizationLostDetector detector;
  EXPECT_EQ(detector.update(0.8f, 2.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.8f, 2.0), LocalizationHealthState::UNKNOWN);
  EXPECT_EQ(detector.update(0.8f, 3.0), LocalizationHealthState::HEALTHY);
  EXPECT_EQ(detector.update(0.8f, 1.0), LocalizationHealthState::UNKNOWN);
  EXPECT_EQ(detector.update(std::numeric_limits<float>::quiet_NaN(), 4.0),
    LocalizationHealthState::UNKNOWN);
}

class LocalizationMonitorRuntimeTest : public ::testing::Test
{
protected:
  using State = mobile_base_localization::msg::LocalizationState;

  static void SetUpTestSuite() {rclcpp::init(0, nullptr);}
  static void TearDownTestSuite() {rclcpp::shutdown();}

  void SetUp() override
  {
    rclcpp::NodeOptions options;
    options.parameter_overrides({
      {"measurement_timeout_s", 0.2}, {"lost_hold_s", 0.05},
      {"recover_hold_s", 0.05}, {"tf_timeout_s", 0.0}});
    monitor = std::make_shared<mobile_base_localization::LocalizationMonitorNode>(options);
    io = std::make_shared<rclcpp::Node>("test_monitor_io");
    map_pub = io->create_publisher<nav_msgs::msg::OccupancyGrid>(
      "/map", rclcpp::QoS(1).reliable().transient_local());
    scan_pub = io->create_publisher<sensor_msgs::msg::LaserScan>("/scan_front", 10);
    sub = io->create_subscription<State>(
      "/localization/state", rclcpp::QoS(1).reliable().transient_local(),
      [this](State::ConstSharedPtr msg) {last = *msg; ++received;});
    executor.add_node(monitor);
    executor.add_node(io);
    pump(150);
  }

  void TearDown() override
  {
    executor.remove_node(monitor);
    executor.remove_node(io);
    monitor.reset();
    io.reset();
  }

  void pump(int ms)
  {
    const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
    do {
      executor.spin_some();
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    } while (std::chrono::steady_clock::now() < end);
  }

  void scan(float distance = 1.0f, const std::string & frame = "map", double age = 0.0)
  {
    auto msg = create_scan_facing_wall(50, distance);
    msg.header.frame_id = frame;
    msg.header.stamp = io->now() - rclcpp::Duration::from_seconds(age);
    scan_pub->publish(msg);
    pump(30);
  }

  rclcpp::Node::SharedPtr monitor, io;
  rclcpp::executors::SingleThreadedExecutor executor;
  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr map_pub;
  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr scan_pub;
  rclcpp::Subscription<State>::SharedPtr sub;
  State last;
  int received{0};
};

TEST_F(LocalizationMonitorRuntimeTest, StartupAndMissingMapPublishUnknown)
{
  ASSERT_GT(received, 0);
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan();
  EXPECT_EQ(last.state, State::UNKNOWN);
}

TEST_F(LocalizationMonitorRuntimeTest, MeasurementFreshnessAndInvalidInputsAreOwnedByMonitor)
{
  map_pub->publish(create_box_map());
  pump(30);
  scan();
  ASSERT_EQ(last.state, State::HEALTHY);
  const auto stamp = last.measurement_stamp;
  pump(60);
  EXPECT_EQ(last.measurement_stamp, stamp);  // Heartbeats do not invent evidence.
  pump(200);
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan();
  ASSERT_EQ(last.state, State::HEALTHY);
  scan(1.0f, "missing_tf");
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan();
  ASSERT_EQ(last.state, State::HEALTHY);
  scan(std::numeric_limits<float>::infinity());
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan(1.0f, "map", 1.0);
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan(1.0f, "map", -1.0);
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan();
  ASSERT_EQ(last.state, State::HEALTHY);
  map_pub->publish(create_box_map(100, 100, 0.05, -2.5, -2.5, 0.5));
  pump(30);
  EXPECT_EQ(last.state, State::UNKNOWN);
}

TEST_F(LocalizationMonitorRuntimeTest, SustainedBadEvidenceLostThenHealthyAndUnknown)
{
  map_pub->publish(create_box_map());
  pump(30);
  scan();
  ASSERT_EQ(last.state, State::HEALTHY);
  scan(0.5f);
  scan(0.5f);
  scan(0.5f);
  EXPECT_EQ(last.state, State::LOST);
  scan();
  scan();
  scan();
  EXPECT_EQ(last.state, State::HEALTHY);
  pump(260);
  EXPECT_EQ(last.state, State::UNKNOWN);
}

TEST(TestLocalizationMonitor, LostHistorySurvivesUnavailableEvidence)
{
  LocalizationLostDetectorConfig config;
  config.lost_hold_s = 1.0;
  config.recover_hold_s = 2.0;
  LocalizationLostDetector detector(config);
  EXPECT_EQ(detector.update(0.8f, 1.0), LocalizationHealthState::HEALTHY);
  detector.update(0.1f, 2.0);
  ASSERT_EQ(detector.update(0.1f, 3.0), LocalizationHealthState::LOST);
  detector.update(0.8f, 4.0);
  detector.update(0.8f, 5.0);
  detector.reset();  // Measurement unavailable interrupts the recovery interval.
  EXPECT_EQ(detector.get_state(), LocalizationHealthState::UNKNOWN);
  EXPECT_EQ(detector.update(0.8f, 100.0), LocalizationHealthState::UNKNOWN);
  EXPECT_EQ(detector.update(0.8f, 101.9), LocalizationHealthState::UNKNOWN);
  EXPECT_EQ(detector.update(0.8f, 102.0), LocalizationHealthState::HEALTHY);
  detector.reset();  // Completed recovery permits the normal startup rule again.
  EXPECT_EQ(detector.update(0.8f, 103.0), LocalizationHealthState::HEALTHY);
}

TEST_F(LocalizationMonitorRuntimeTest, LostRecoveryRequirementSurvivesTfAndScanUnavailability)
{
  map_pub->publish(create_box_map());
  pump(30);
  scan(0.5f);
  scan(0.5f);
  scan(0.5f);
  ASSERT_EQ(last.state, State::LOST);
  scan();  // Start, but do not finish, recovery.
  scan(1.0f, "missing_tf");
  ASSERT_EQ(last.state, State::UNKNOWN);
  pump(260);  // Longer than recover_hold_s; must not count as good evidence.
  scan();
  EXPECT_EQ(last.state, State::UNKNOWN);
  scan();
  scan();
  EXPECT_EQ(last.state, State::HEALTHY);
}
