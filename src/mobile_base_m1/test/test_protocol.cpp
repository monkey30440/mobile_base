#include <gtest/gtest.h>
#include "mobile_base_m1/protocol.hpp"
TEST(M1Protocol, MapsWheelRadiansToSignedMotorRPMWithoutGuessingDirection) {
  mobile_base_m1::Scale scale{10.0, -1.0, 1.0};
  EXPECT_EQ(mobile_base_m1::command_rpm(6.283185307179586, scale), -600);
  EXPECT_NEAR(mobile_base_m1::feedback_velocity(600, scale), -6.283185307179586, 1e-10);
}
TEST(M1Protocol, RejectsNonzeroRPMBelowDocumentedMinimumRatherThanOverspeeding) {
  EXPECT_THROW(mobile_base_m1::command_rpm(0.1, {1, 1, 1}), std::invalid_argument);
  EXPECT_EQ(mobile_base_m1::command_rpm(0, {1, 1, 1}), 0);
}
TEST(M1Protocol, FaultedOrInhibitedFeedbackIsNotAMeasurement) {
 EXPECT_THROW(mobile_base_m1::checked_feedback(5, 13, 600, {10, 1, 1}), std::runtime_error);
 EXPECT_THROW(mobile_base_m1::checked_feedback(9, 0, 600, {10, 1, 1}), std::runtime_error);
 EXPECT_NEAR(mobile_base_m1::checked_feedback(2, 0, 64936, {10, -1, 1}), 6.283185307179586, 1e-10);
}
