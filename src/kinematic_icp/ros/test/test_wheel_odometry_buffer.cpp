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

#include <cmath>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/time.hpp>

#include "kinematic_icp_ros/utils/WheelOdometryBuffer.hpp"

using kinematic_icp_ros::utils::WheelOdometryBuffer;
using kinematic_icp_ros::utils::WheelPoseSample;

class WheelOdometryBufferTest : public ::testing::Test {
protected:
    void SetUp() override {
        buffer_ = std::make_unique<WheelOdometryBuffer>(5.0);
    }

    std::unique_ptr<WheelOdometryBuffer> buffer_;
};

// 1. Exact timestamp lookup
TEST_F(WheelOdometryBufferTest, ExactTimestampLookup) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);

    buffer_->AddSample({t0, 1.0, 2.0, 0.5});
    buffer_->AddSample({t1, 3.0, 4.0, 1.0});

    auto p0 = buffer_->InterpolatePose(t0);
    ASSERT_TRUE(p0.has_value());
    EXPECT_NEAR(p0->x, 1.0, 1e-6);
    EXPECT_NEAR(p0->y, 2.0, 1e-6);
    EXPECT_NEAR(p0->yaw, 0.5, 1e-6);

    auto p1 = buffer_->InterpolatePose(t1);
    ASSERT_TRUE(p1.has_value());
    EXPECT_NEAR(p1->x, 3.0, 1e-6);
    EXPECT_NEAR(p1->y, 4.0, 1e-6);
    EXPECT_NEAR(p1->yaw, 1.0, 1e-6);
}

// 2. Midpoint x/y interpolation
TEST_F(WheelOdometryBufferTest, MidpointXYInterpolation) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);
    rclcpp::Time t_mid(1, 500000000, RCL_ROS_TIME);  // 1.5s

    buffer_->AddSample({t0, 10.0, 20.0, 0.0});
    buffer_->AddSample({t1, 20.0, 40.0, 0.0});

    auto p_mid = buffer_->InterpolatePose(t_mid);
    ASSERT_TRUE(p_mid.has_value());
    EXPECT_NEAR(p_mid->x, 15.0, 1e-6);
    EXPECT_NEAR(p_mid->y, 30.0, 1e-6);
    EXPECT_NEAR(p_mid->yaw, 0.0, 1e-6);
}

// 3. Yaw interpolation
TEST_F(WheelOdometryBufferTest, YawInterpolation) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);
    rclcpp::Time t_mid(1, 500000000, RCL_ROS_TIME);

    buffer_->AddSample({t0, 0.0, 0.0, 0.2});
    buffer_->AddSample({t1, 0.0, 0.0, 0.8});

    auto p_mid = buffer_->InterpolatePose(t_mid);
    ASSERT_TRUE(p_mid.has_value());
    EXPECT_NEAR(p_mid->yaw, 0.5, 1e-6);
}

// 4. Yaw crossing +pi / -pi boundary
TEST_F(WheelOdometryBufferTest, YawCrossingPiBoundary) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);
    rclcpp::Time t_mid(1, 500000000, RCL_ROS_TIME);

    // +3.0 rad (~171.9 deg) to -3.0 rad (~-171.9 deg)
    // Shortest angular path crosses pi: delta = +0.2831853 rad
    buffer_->AddSample({t0, 0.0, 0.0, 3.0});
    buffer_->AddSample({t1, 0.0, 0.0, -3.0});

    auto p_mid = buffer_->InterpolatePose(t_mid);
    ASSERT_TRUE(p_mid.has_value());

    // At midpoint (alpha=0.5), angle should be ~ 3.0 + 0.14159 = 3.14159 rad (= pi)
    EXPECT_NEAR(std::abs(p_mid->yaw), M_PI, 1e-3);
}

// 5. Stationary delta = identity
TEST_F(WheelOdometryBufferTest, StationaryDeltaIsIdentity) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);

    buffer_->AddSample({t0, 5.0, 7.0, 1.23});
    buffer_->AddSample({t1, 5.0, 7.0, 1.23});

    auto delta = buffer_->ComputeDeltaTransform(t0, t1);
    ASSERT_TRUE(delta.has_value());
    EXPECT_NEAR(delta->translation().norm(), 0.0, 1e-6);
    EXPECT_NEAR(delta->log().norm(), 0.0, 1e-6);
}

// 6. Straight forward delta in world-aligned frame
TEST_F(WheelOdometryBufferTest, StraightForwardDeltaAligned) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);

    // Heading 0 rad (facing +X), moves forward 2 meters
    buffer_->AddSample({t0, 1.0, 0.0, 0.0});
    buffer_->AddSample({t1, 3.0, 0.0, 0.0});

    auto delta = buffer_->ComputeDeltaTransform(t0, t1);
    ASSERT_TRUE(delta.has_value());
    EXPECT_NEAR(delta->translation().x(), 2.0, 1e-6);
    EXPECT_NEAR(delta->translation().y(), 0.0, 1e-6);
    EXPECT_NEAR(delta->translation().z(), 0.0, 1e-6);
    EXPECT_NEAR(delta->so3().log().norm(), 0.0, 1e-6);
}

// 7. Straight forward delta in rotated frame (Mandatory transform-direction check)
TEST_F(WheelOdometryBufferTest, StraightForwardDeltaRotatedHeading) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);

    // Heading pi/2 (facing +Y in world), moves forward 2 meters along robot body-X
    // In world frame: pos(t0) = (10, 20), pos(t1) = (10, 22)
    buffer_->AddSample({t0, 10.0, 20.0, M_PI / 2.0});
    buffer_->AddSample({t1, 10.0, 22.0, M_PI / 2.0});

    auto delta = buffer_->ComputeDeltaTransform(t0, t1);
    ASSERT_TRUE(delta.has_value());

    // In robot body frame at t0, motion MUST be +2.0m in body X, 0m in body Y!
    // If delta was calculated as naive world subtraction or inverted order, this would fail.
    EXPECT_NEAR(delta->translation().x(), 2.0, 1e-5);
    EXPECT_NEAR(delta->translation().y(), 0.0, 1e-5);
    EXPECT_NEAR(delta->translation().z(), 0.0, 1e-5);
    EXPECT_NEAR(delta->so3().log().norm(), 0.0, 1e-5);
}

// 8. Pure rotation delta
TEST_F(WheelOdometryBufferTest, PureRotationDelta) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);

    buffer_->AddSample({t0, 4.0, 5.0, 0.2});
    buffer_->AddSample({t1, 4.0, 5.0, 0.8});

    auto delta = buffer_->ComputeDeltaTransform(t0, t1);
    ASSERT_TRUE(delta.has_value());
    EXPECT_NEAR(delta->translation().norm(), 0.0, 1e-6);
    EXPECT_NEAR(delta->so3().log().z(), 0.6, 1e-5);
}

// 9. Insufficient history / Out of range policy
TEST_F(WheelOdometryBufferTest, InsufficientHistoryOutOfRange) {
    // Empty buffer
    EXPECT_FALSE(buffer_->InterpolatePose(rclcpp::Time(1, 0, RCL_ROS_TIME)).has_value());

    rclcpp::Time t0(2, 0, RCL_ROS_TIME);
    rclcpp::Time t1(3, 0, RCL_ROS_TIME);
    buffer_->AddSample({t0, 0.0, 0.0, 0.0});
    buffer_->AddSample({t1, 1.0, 0.0, 0.0});

    // Query 1 second before oldest sample (outside 0.05s tolerance) -> returns nullopt
    rclcpp::Time t_too_old(1, 0, RCL_ROS_TIME);
    EXPECT_FALSE(buffer_->InterpolatePose(t_too_old, 0.05).has_value());

    // Query within tolerance before oldest sample -> returns oldest sample
    rclcpp::Time t_slight_old(1, 980000000, RCL_ROS_TIME);  // 1.98s (diff 0.02s <= 0.05s)
    auto p_near = buffer_->InterpolatePose(t_slight_old, 0.05);
    ASSERT_TRUE(p_near.has_value());
    EXPECT_NEAR(p_near->x, 0.0, 1e-6);
}

// 10. Future timestamp outside tolerance
TEST_F(WheelOdometryBufferTest, FutureTimestampOutsideTolerance) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(2, 0, RCL_ROS_TIME);
    buffer_->AddSample({t0, 0.0, 0.0, 0.0});
    buffer_->AddSample({t1, 1.0, 0.0, 0.0});

    // Query 1 second into future -> returns nullopt
    rclcpp::Time t_future(3, 0, RCL_ROS_TIME);
    EXPECT_FALSE(buffer_->InterpolatePose(t_future, 0.05).has_value());

    // Query within 0.05s tolerance into future -> returns newest sample
    rclcpp::Time t_near_future(2, 20000000, RCL_ROS_TIME);  // 2.02s
    auto p_future_near = buffer_->InterpolatePose(t_near_future, 0.05);
    ASSERT_TRUE(p_future_near.has_value());
    EXPECT_NEAR(p_future_near->x, 1.0, 1e-6);
}

// 11. Bounded buffer history cleanup
TEST_F(WheelOdometryBufferTest, BoundedBufferCleanup) {
    WheelOdometryBuffer short_buffer(2.0);  // 2.0 seconds retention

    for (int sec = 0; sec < 10; ++sec) {
        short_buffer.AddSample({rclcpp::Time(sec, 0, RCL_ROS_TIME), static_cast<double>(sec), 0.0, 0.0});
    }

    // Newest is t=9. Retention is 2.0s, so samples older than t=7 should be pruned
    EXPECT_FALSE(short_buffer.InterpolatePose(rclcpp::Time(5, 0, RCL_ROS_TIME), 0.01).has_value());
    EXPECT_TRUE(short_buffer.InterpolatePose(rclcpp::Time(8, 0, RCL_ROS_TIME), 0.01).has_value());
    EXPECT_TRUE(short_buffer.InterpolatePose(rclcpp::Time(9, 0, RCL_ROS_TIME), 0.01).has_value());
}

// 12. Out-of-order odometry sample handling
TEST_F(WheelOdometryBufferTest, OutOfOrderOdometryInsertion) {
    rclcpp::Time t0(1, 0, RCL_ROS_TIME);
    rclcpp::Time t1(3, 0, RCL_ROS_TIME);
    rclcpp::Time t_mid(2, 0, RCL_ROS_TIME);

    buffer_->AddSample({t0, 1.0, 0.0, 0.0});
    buffer_->AddSample({t1, 3.0, 0.0, 0.0});
    // Add out-of-order sample at t=2.0
    buffer_->AddSample({t_mid, 2.0, 0.0, 0.0});

    // Interpolate between t=2.0 and t=3.0 (at t=2.5)
    rclcpp::Time t_query(2, 500000000, RCL_ROS_TIME);
    auto p = buffer_->InterpolatePose(t_query);
    ASSERT_TRUE(p.has_value());
    EXPECT_NEAR(p->x, 2.5, 1e-6);
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
