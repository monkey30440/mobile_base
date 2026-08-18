// Copyright 2026 mobile_base contributors
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

#include "mobile_base_control/m1_dynamic_stage_d2_check.hpp"

#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "hardware_interface/resource_manager.hpp"
#include "lifecycle_msgs/msg/state.hpp"
#include "rclcpp/rclcpp.hpp"

namespace mobile_base_control
{

DynamicStageD2ValidationResult validate_stage_d2_options(
  const DynamicStageD2Options & options) noexcept
{
  if (options.driver_a == options.driver_b) {
    return {false, "Driver A and Driver B must have distinct IDs."};
  }
  if (options.driver_a < 1 || options.driver_a > 8 ||
    options.driver_b < 1 || options.driver_b > 8)
  {
    return {false, "Driver IDs must be in the range [1, 8]."};
  }
  if (options.timeout_ms <= 0) {
    return {false, "Timeout must be greater than 0 ms."};
  }
  if (options.target_rate_hz <= 0.0 || options.target_rate_hz > 100.0) {
    return {false, "Target rate must be in the range (0.0, 100.0] Hz."};
  }
  if (std::isnan(options.right_wheel_cmd_rad_s) || std::isinf(options.right_wheel_cmd_rad_s)) {
    return {false, "Right wheel velocity command must be a finite number."};
  }
  if (options.right_wheel_cmd_rad_s <= 0.0) {
    return {false, "Stage D2 requires a strictly positive right wheel velocity command."};
  }
  if (options.right_wheel_cmd_rad_s > STAGE_D2_MAX_RIGHT_WHEEL_VEL_RAD_S) {
    return {false, "Right wheel velocity exceeds Stage D2 harness sanity limit (" +
      std::to_string(STAGE_D2_MAX_RIGHT_WHEEL_VEL_RAD_S) + " rad/s)."};
  }
  if (options.warmup_cycles > STAGE_D2_MAX_WARMUP_CYCLES) {
    return {false, "Warm-up cycles exceeds maximum limit (" +
      std::to_string(STAGE_D2_MAX_WARMUP_CYCLES) + ")."};
  }
  if (options.active_cycles < 10 || options.active_cycles > STAGE_D2_MAX_ACTIVE_CYCLES) {
    return {false, "Active cycles must be in the range [10, " +
      std::to_string(STAGE_D2_MAX_ACTIVE_CYCLES) + "]."};
  }
  if (options.cooldown_cycles > STAGE_D2_MAX_COOLDOWN_CYCLES) {
    return {false, "Cooldown cycles exceeds maximum limit (" +
      std::to_string(STAGE_D2_MAX_COOLDOWN_CYCLES) + ")."};
  }
  return {true, ""};
}

DynamicStageD2Options parse_stage_d2_command_line(int argc, char ** argv)
{
  DynamicStageD2Options opts;

  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];

    // Prohibit prohibited CLI arguments
    if (arg == "--rpm" || arg == "--left" || arg == "--left-vel" ||
      arg == "--both" || arg == "--reverse" || arg == "--linear" ||
      arg == "--angular" || arg == "--cmd_vel")
    {
      throw std::invalid_argument(
              "CRITICAL SAFETY VIOLATION: Argument (" + arg +
              ") is strictly prohibited. Stage D2 only exercises positive right wheel velocity.");
    }

    if ((arg == "--right-vel" || arg == "--right-velocity" || arg == "--right-rad-s") &&
      i + 1 < argc)
    {
      opts.right_wheel_cmd_rad_s = std::stod(argv[++i]);
    } else if (arg == "--device" && i + 1 < argc) {
      opts.device = argv[++i];
    } else if (arg == "--baud" && i + 1 < argc) {
      opts.baud = std::stoi(argv[++i]);
    } else if (arg == "--timeout-ms" && i + 1 < argc) {
      opts.timeout_ms = std::stoi(argv[++i]);
    } else if (arg == "--driver-a" && i + 1 < argc) {
      opts.driver_a = std::stoi(argv[++i]);
    } else if (arg == "--driver-b" && i + 1 < argc) {
      opts.driver_b = std::stoi(argv[++i]);
    } else if (arg == "--active-cycles" && i + 1 < argc) {
      opts.active_cycles = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--warmup" && i + 1 < argc) {
      opts.warmup_cycles = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--cooldown" && i + 1 < argc) {
      opts.cooldown_cycles = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--raw-output" && i + 1 < argc) {
      opts.raw_output_path = argv[++i];
    } else if (arg == "--dry-run") {
      opts.dry_run = true;
      opts.execute = false;
    } else if (arg == "--execute") {
      opts.execute = true;
      opts.dry_run = false;
    } else {
      throw std::invalid_argument("Unknown argument: " + arg);
    }
  }

  return opts;
}

std::string build_stage_d2_urdf(const DynamicStageD2Options & opts)
{
  std::ostringstream ss;
  ss <<
    R"xml(<?xml version="1.0"?>
<robot name="mobile_base_stage_d2">
  <link name="base_link"/>
  <link name="left_wheel"/>
  <link name="right_wheel"/>
  <joint name="driving_wheel_joint_L" type="continuous">
    <parent link="base_link"/>
    <child link="left_wheel"/>
  </joint>
  <joint name="driving_wheel_joint_R" type="continuous">
    <parent link="base_link"/>
    <child link="right_wheel"/>
  </joint>
  <ros2_control name="M1Hardware" type="system">
    <hardware>
      <plugin>mobile_base_control/M1Hardware</plugin>
      <param name="serial_port">)xml"
     << opts.device << R"xml(</param>
      <param name="baud_rate">)xml" << opts.baud <<
    R"xml(</param>
      <param name="response_timeout_ms">)xml" << opts.timeout_ms <<
    R"xml(</param>
      <param name="left_driver_id">)xml" << opts.driver_b <<
    R"xml(</param>
      <param name="right_driver_id">)xml" << opts.driver_a <<
    R"xml(</param>
      <param name="gear_ratio">20.0</param>
      <param name="left_wheel_sign">1</param>
      <param name="right_wheel_sign">-1</param>
      <param name="motor_steps_per_rev">10000.0</param>
      <param name="max_motor_rpm">3000.0</param>
    </hardware>
    <joint name="driving_wheel_joint_L">
      <command_interface name="velocity"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
    <joint name="driving_wheel_joint_R">
      <command_interface name="velocity"/>
      <state_interface name="position"/>
      <state_interface name="velocity"/>
    </joint>
  </ros2_control>
</robot>)xml";
  return ss.str();
}

static void print_stage_d2_plan(
  const DynamicStageD2Options & opts,
  std::ostream & out)
{
  const double right_rad_s = opts.right_wheel_cmd_rad_s;
  const int16_t right_rpm = M1Hardware::wheel_rad_s_to_motor_rpm(right_rad_s, 20.0, -1, 3000.0);
  const double linear_speed_m_s = right_rad_s * 0.08;
  const double expected_rot_rad = right_rad_s * (static_cast<double>(opts.active_cycles) / 30.0);
  const double expected_rot_deg = expected_rot_rad * 180.0 / M_PI;

  out << "================================================================\n"
      << "IMP-008 Level 4 Stage D2: Right Wheel Dynamic Feedback Plan\n"
      << "================================================================\n"
      << "Target Device         : " << opts.device << " @ " << opts.baud << " bps\n"
      << "Control Loop Rate     : 30.0 Hz (Period = 33.333 ms)\n"
      << "Response Timeout      : " << opts.timeout_ms << " ms [PROVISIONAL TEST CONDITION]\n"
      << "Target Wheel          : RIGHT WHEEL ONLY (Driver ID " << opts.driver_a << ", Sign -1)\n"
      << "Commanded Velocity    : " << right_rad_s << " rad/s (~"
      << std::fixed << std::setprecision(2) << linear_speed_m_s << " m/s surface speed)\n"
      << "Converted Target RPM  : " << right_rpm << " RPM (Right motor, negative native sign)\n"
      << "Left Wheel Target     : 0.0 rad/s (0 RPM, strictly hard-bound)\n"
      << "Active Cycles / Time  : " << opts.active_cycles << " cycles ("
      << std::fixed << std::setprecision(2) << (static_cast<double>(opts.active_cycles) / 30.0) <<
    " s)\n"
      << "Expected Rotation     : ~" << std::fixed << std::setprecision(1) << expected_rot_deg
      << " deg (~" << std::setprecision(2) << expected_rot_rad << " rad)\n"
      << "Warmup / Cooldown     : " << opts.warmup_cycles << " warmup / "
      << opts.cooldown_cycles << " cooldown cycles (0 RPM)\n"
      << "Expected Physical Dir : Expected Robot-Forward (CW viewed from robot's right side; "
      << "UNVERIFIED; requires operator visual confirmation)\n"
      << "================================================================\n";
}

int run_dynamic_stage_d2_check(
  const DynamicStageD2Options & options,
  std::shared_ptr<M1Driver> mock_driver,
  std::ostream & out,
  std::ostream & err)
{
  const auto validation = validate_stage_d2_options(options);
  if (!validation.valid) {
    err << "Configuration Error: " << validation.error_message << "\n";
    return 1;
  }

  print_stage_d2_plan(options, out);

  if (options.dry_run) {
    out << "\n[DRY RUN MODE] - 0 physical hardware transport calls issued.\n"
        << "To execute, provide explicit execution-time operator authorization and '--execute'.\n"
        << "Physical Preflight Checklist (§6):\n"
        << "  [ ] /dev/ttyUSB0 confirmed connected to M1 dual-driver bus\n"
        << "  [ ] Driver 1 (Right) and Driver 2 (Left) confirmed\n"
        << "  [ ] BOTH driving wheels completely off the ground (elevated)\n"
        << "  [ ] Controlled area clear of cables and foreign objects\n"
        << "  [ ] Physical E-Stop / power isolation switch immediately accessible\n"
        << "  [ ] Operator physically present throughout hardware validation session\n"
        << "  [ ] Operator will visually observe and confirm RIGHT wheel "
        << "physical rotation direction\n"
        << "================================================================\n";
    return 0;
  }

  if (!rclcpp::ok()) {
    rclcpp::init(0, nullptr);
  }

  // Real Hardware Execution Path
  const std::string urdf = build_stage_d2_urdf(options);
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("m1_dynamic_stage_d2_check");
  std::unique_ptr<hardware_interface::ResourceManager> resource_manager;

  try {
    if (mock_driver) {
      resource_manager = std::make_unique<hardware_interface::ResourceManager>(
        urdf, clock, logger, false);
    } else {
      // Immediate read-only baseline check before activation
      M1Driver baseline_driver;
      auto conn_res = baseline_driver.connect(
        options.device, options.baud, options.timeout_ms, 'N', 8, 1);
      if (!conn_res.ok) {
        err << "Pre-flight Error: Failed to open " << options.device << " for baseline check.\n";
        return 1;
      }
      auto baseline_state = baseline_driver.read_state(options.driver_a, options.driver_b);
      baseline_driver.disconnect();

      if (!baseline_state.ok) {
        err << "Pre-flight Error: Failed to read initial driver state: "
            << error_code_to_string(baseline_state.error) << "\n";
        return 1;
      }
      const auto & d1 = baseline_state.value.states[0];
      const auto & d2 = baseline_state.value.states[1];
      if (d1.alarm != 0 || d2.alarm != 0 ||
        d1.actual_rpm != 0 || d2.actual_rpm != 0 ||
        d1.status != 6 || d2.status != 6)
      {
        err << "Pre-flight Error: Drivers not in clean baseline: Driver 1 (Status="
            << d1.status << ", Alarm=" << d1.alarm
            << ", RPM=" << d1.actual_rpm << "), Driver 2 (Status="
            << d2.status << ", Alarm=" << d2.alarm
            << ", RPM=" << d2.actual_rpm << "). ABORTING.\n";
        return 1;
      }

      resource_manager = std::make_unique<hardware_interface::ResourceManager>(
        urdf, clock, logger, true);
    }
  } catch (const std::exception & e) {
    err << "Failed to initialize ResourceManager: " << e.what() << "\n";
    return 1;
  }

  // Activate M1Hardware lifecycle
  rclcpp_lifecycle::State active_state(
    lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE, "active");
  resource_manager->set_component_state("M1Hardware", active_state);

  // Claim loaned interfaces
  hardware_interface::LoanedCommandInterface cmd_left =
    resource_manager->claim_command_interface("driving_wheel_joint_L/velocity");
  hardware_interface::LoanedCommandInterface cmd_right =
    resource_manager->claim_command_interface("driving_wheel_joint_R/velocity");

  hardware_interface::LoanedStateInterface pos_left =
    resource_manager->claim_state_interface("driving_wheel_joint_L/position");
  hardware_interface::LoanedStateInterface pos_right =
    resource_manager->claim_state_interface("driving_wheel_joint_R/position");
  hardware_interface::LoanedStateInterface vel_left =
    resource_manager->claim_state_interface("driving_wheel_joint_L/velocity");
  hardware_interface::LoanedStateInterface vel_right =
    resource_manager->claim_state_interface("driving_wheel_joint_R/velocity");

  // Initial zero reference
  static_cast<void>(cmd_left.set_value(0.0));
  static_cast<void>(cmd_right.set_value(0.0));

  const double target_period_s = 1.0 / options.target_rate_hz;
  const auto target_period_dur = std::chrono::duration<double>(target_period_s);
  const size_t total_cycles = options.warmup_cycles + options.active_cycles +
    options.cooldown_cycles;

  std::vector<DynamicStageD2Sample> samples;
  samples.reserve(total_cycles);

  out << "[Step 1] Executing Stage D2 dynamic motion loop ("
      << options.warmup_cycles << " warmup + "
      << options.active_cycles << " active @ " << options.right_wheel_cmd_rad_s << " rad/s + "
      << options.cooldown_cycles << " cooldown cycles)...\n";

  bool abort_triggered = false;
  std::string abort_reason = "";

  const auto loop_start_time = std::chrono::steady_clock::now();

  for (size_t i = 0; i < total_cycles; ++i) {
    const auto cycle_start_time = std::chrono::steady_clock::now();

    // 1. Read state
    const auto read_ret = resource_manager->read(
      rclcpp::Time(0, 0, RCL_ROS_TIME), rclcpp::Duration::from_seconds(target_period_s));

    // Determine phase & command
    std::string phase = "warmup";
    double right_cmd = 0.0;
    if (i >= options.warmup_cycles && i < options.warmup_cycles + options.active_cycles) {
      phase = "active";
      right_cmd = options.right_wheel_cmd_rad_s;
    } else if (i >= options.warmup_cycles + options.active_cycles) {
      phase = "cooldown";
      right_cmd = 0.0;
    }

    // Set command interfaces (Left wheel is strictly 0.0)
    static_cast<void>(cmd_left.set_value(0.0));
    static_cast<void>(cmd_right.set_value(right_cmd));

    // 2. Write command
    const auto write_ret = resource_manager->write(
      rclcpp::Time(0, 0, RCL_ROS_TIME), rclcpp::Duration::from_seconds(target_period_s));

    const auto cycle_end_time = std::chrono::steady_clock::now();
    const double cycle_duration_us = std::chrono::duration<double, std::micro>(
      cycle_end_time - cycle_start_time).count();

    DynamicStageD2Sample sample;
    sample.seq = i + 1;
    sample.phase = phase;
    sample.cycle_duration_us = cycle_duration_us;
    sample.left_cmd_rad_s = 0.0;
    sample.right_cmd_rad_s = right_cmd;
    sample.left_target_rpm = 0;
    sample.right_target_rpm = M1Hardware::wheel_rad_s_to_motor_rpm(right_cmd, 20.0, -1, 3000.0);
    sample.left_wheel_pos_rad = pos_left.get_value();
    sample.right_wheel_pos_rad = pos_right.get_value();
    sample.left_wheel_vel_rad_s = vel_left.get_value();
    sample.right_wheel_vel_rad_s = vel_right.get_value();
    sample.ok = (read_ret.result == hardware_interface::return_type::OK &&
      write_ret.result == hardware_interface::return_type::OK);

    samples.push_back(sample);

    if (!sample.ok) {
      abort_triggered = true;
      abort_reason = "ResourceManager read/write error";
      break;
    }

    // Anomaly checks
    if (phase == "active") {
      if (sample.left_wheel_vel_rad_s > 0.2 || sample.left_wheel_vel_rad_s < -0.2) {
        abort_triggered = true;
        abort_reason = "Unexpected left wheel motion observed during right-only test";
        break;
      }
      if (sample.right_wheel_vel_rad_s < -0.05) {
        abort_triggered = true;
        abort_reason = "Wrong right wheel rotation direction (negative velocity detected)";
        break;
      }
    }

    // Sleep until next cycle deadline
    const auto next_target_time = loop_start_time + std::chrono::duration_cast<
      std::chrono::steady_clock::duration>(target_period_dur * static_cast<double>(i + 1));
    const auto now = std::chrono::steady_clock::now();
    if (next_target_time > now) {
      std::this_thread::sleep_until(next_target_time);
    }
  }

  // Safe Deactivation
  static_cast<void>(cmd_left.set_value(0.0));
  static_cast<void>(cmd_right.set_value(0.0));
  resource_manager->write(
    rclcpp::Time(0, 0, RCL_ROS_TIME), rclcpp::Duration::from_seconds(target_period_s));

  resource_manager.reset();  // Calls M1Hardware destructor -> safe stop & disable

  out << "[Step 2] Hardware deactivated cleanly.\n";

  // Post-flight Read-Only Confirmation
  if (!mock_driver) {
    M1Driver post_driver;
    if (post_driver.connect(options.device, options.baud, options.timeout_ms, 'N', 8, 1).ok) {
      auto post_state = post_driver.read_state(options.driver_a, options.driver_b);
      post_driver.disconnect();
      if (post_state.ok) {
        out << "Post-check Driver 1 (Right): Status=" << post_state.value.states[0].status
            << ", Alarm=" << post_state.value.states[0].alarm
            << ", Actual RPM=" << post_state.value.states[0].actual_rpm << "\n"
            << "Post-check Driver 2 (Left) : Status=" << post_state.value.states[1].status
            << ", Alarm=" << post_state.value.states[1].alarm
            << ", Actual RPM=" << post_state.value.states[1].actual_rpm << "\n";
      }
    }
  }

  // Save CSV if requested
  if (!options.raw_output_path.empty()) {
    std::ofstream csv(options.raw_output_path);
    if (csv.is_open()) {
      csv << "seq,phase,cycle_duration_us,left_cmd_rad_s,right_cmd_rad_s,left_target_rpm,"
          << "right_target_rpm,left_wheel_pos_rad,right_wheel_pos_rad,left_wheel_vel_rad_s,"
          << "right_wheel_vel_rad_s,ok\n";
      for (const auto & s : samples) {
        csv << s.seq << "," << s.phase << ","
            << std::fixed << std::setprecision(2) << s.cycle_duration_us << ","
            << std::setprecision(4) << s.left_cmd_rad_s << "," << s.right_cmd_rad_s << ","
            << s.left_target_rpm << "," << s.right_target_rpm << ","
            << std::setprecision(5) << s.left_wheel_pos_rad << "," << s.right_wheel_pos_rad << ","
            << std::setprecision(4) << s.left_wheel_vel_rad_s << "," << s.right_wheel_vel_rad_s <<
          ","
            << (s.ok ? 1 : 0) << "\n";
      }
      out << "Raw timing CSV saved to: " << options.raw_output_path << "\n";
    }
  }

  if (abort_triggered) {
    err << "CRITICAL ERROR: Stage D2 aborted: " << abort_reason << "\n";
    return 1;
  }

  // Print results
  if (!samples.empty()) {
    const auto & first = samples.front();
    const auto & last = samples.back();
    const double delta_left_rad = last.left_wheel_pos_rad - first.left_wheel_pos_rad;
    const double delta_right_rad = last.right_wheel_pos_rad - first.right_wheel_pos_rad;

    out << "\n================================================================\n"
        << "       STAGE D2 RIGHT WHEEL DYNAMIC FEEDBACK RESULTS            \n"
        << "================================================================\n"
        << "Total Cycles Executed : " << samples.size() << "\n"
        << "Right Pos Start / End : " << std::fixed << std::setprecision(4)
        << first.right_wheel_pos_rad << " rad -> " << last.right_wheel_pos_rad << " rad\n"
        << "Right Pos Delta       : " << delta_right_rad << " rad ("
        << (delta_right_rad * 180.0 / M_PI) << " deg)\n"
        << "Left Pos Start / End  : " << first.left_wheel_pos_rad << " rad -> "
        << last.left_wheel_pos_rad << " rad\n"
        << "Left Pos Delta        : " << delta_left_rad << " rad\n"
        << "Direction Consistency : " << (delta_right_rad > 0.0 ? "PASS (Positive)" : "FAIL") <<
      "\n"
        << "Isolation Consistency : " << (std::abs(delta_left_rad) <
    0.05 ? "PASS (Zero)" : "FAIL") << "\n"
        << "================================================================\n";
  }

  return 0;
}

}  // namespace mobile_base_control
