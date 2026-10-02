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
TEST(M1Protocol, FaultedOrSTOFeedbackIsNotAMeasurement) {
 EXPECT_THROW(mobile_base_m1::checked_feedback(5, 13, 600, {10, 1, 1}), std::runtime_error);
 EXPECT_THROW(mobile_base_m1::checked_feedback(9, 0, 600, {10, 1, 1}), std::runtime_error);
 EXPECT_NEAR(mobile_base_m1::checked_feedback(2, 0, 64936, {10, -1, 1}), 6.283185307179586, 1e-10);
}
TEST(M1Protocol, ValidatesObservedTargetPerDrivePrefixCRCWithoutConfusingItWithSpeed) {
 // Independent literal from a real FC03-only response on 2026-10-02:
 // 65031000060000000076440006000000000e194ffe (final frame CRC4ffe).
 const std::array<uint16_t,8> live{6,0,0,0x7644,6,0,0,0x0e19};
 EXPECT_NO_THROW(mobile_base_m1::validate_error_checks(live));
 auto damaged=live; damaged[6]=1;
 EXPECT_THROW(mobile_base_m1::validate_error_checks(damaged),std::runtime_error);
}
