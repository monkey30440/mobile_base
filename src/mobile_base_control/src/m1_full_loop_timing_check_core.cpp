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

#include "mobile_base_control/m1_full_loop_timing_check.hpp"

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

#include "diff_drive_controller/diff_drive_controller.hpp"
#include "hardware_interface/resource_manager.hpp"
#include "lifecycle_msgs/msg/state.hpp"
#include "rclcpp/rclcpp.hpp"

namespace mobile_base_control
{

FullLoopValidationResult validate_full_loop_options(
  const FullLoopTimingOptions & options) noexcept
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
  if (options.warmup_cycles > FULL_LOOP_MAX_WARMUP_CYCLES) {
    return {false, "Warm-up cycles exceeds maximum limit (" +
      std::to_string(FULL_LOOP_MAX_WARMUP_CYCLES) + ")."};
  }
  if (options.measured_cycles > FULL_LOOP_MAX_MEASURED_CYCLES) {
    return {false, "Measured cycles exceeds maximum limit (" +
      std::to_string(FULL_LOOP_MAX_MEASURED_CYCLES) + ")."};
  }
  if (options.measured_cycles == 0) {
    return {false, "Measured cycles must be at least 1."};
  }
  return {true, ""};
}

FullLoopTimingOptions parse_full_loop_command_line(int argc, char ** argv)
{
  FullLoopTimingOptions opts;

  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];

    // Strictly prohibit any motion specification CLI arguments
    if (arg == "--rpm" || arg == "--velocity" || arg == "--speed" ||
      arg == "--linear" || arg == "--angular" || arg == "--cmd_vel" ||
      arg.rfind("--vel", 0) == 0)
    {
      throw std::invalid_argument(
              "CRITICAL SAFETY VIOLATION: Non-zero motion CLI arguments (" + arg +
              ") are strictly prohibited in the zero-speed timing harness.");
    }

    if (arg == "--device" && i + 1 < argc) {
      opts.device = argv[++i];
    } else if (arg == "--baud" && i + 1 < argc) {
      opts.baud = std::stoi(argv[++i]);
    } else if (arg == "--timeout-ms" && i + 1 < argc) {
      opts.timeout_ms = std::stoi(argv[++i]);
    } else if (arg == "--driver-a" && i + 1 < argc) {
      opts.driver_a = std::stoi(argv[++i]);
    } else if (arg == "--driver-b" && i + 1 < argc) {
      opts.driver_b = std::stoi(argv[++i]);
    } else if (arg == "--rate" && i + 1 < argc) {
      opts.target_rate_hz = std::stod(argv[++i]);
    } else if (arg == "--warmup" && i + 1 < argc) {
      opts.warmup_cycles = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--cycles" && i + 1 < argc) {
      opts.measured_cycles = static_cast<size_t>(std::stoul(argv[++i]));
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

std::string build_full_loop_urdf(const FullLoopTimingOptions & opts)
{
  std::ostringstream ss;
  ss                                  <<
    R"xml(<?xml version="1.0"?>
<robot name="mobile_base_timing_check">
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
                                      << opts.device <<
    R"xml(</param>
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

namespace
{

std::shared_ptr<diff_drive_controller::DiffDriveController> create_diff_drive_controller(
  double update_rate_hz)
{
  auto controller = std::make_shared<diff_drive_controller::DiffDriveController>();
  rclcpp::NodeOptions node_options;
  node_options.parameter_overrides({
        {"left_wheel_names", std::vector<std::string>{"driving_wheel_joint_L"}},
        {"right_wheel_names", std::vector<std::string>{"driving_wheel_joint_R"}},
        {"wheel_separation", 0.5545},
        {"wheel_radius", 0.08},
        {"use_stamped_vel", false},
        {"open_loop", false},
        {"publish_rate", update_rate_hz},
        {"cmd_vel_timeout", 0.5},
  });

  const auto init_ret = controller->init("diff_drive_controller", "", update_rate_hz, "",
        node_options);
  if (init_ret != controller_interface::return_type::OK) {
    return nullptr;
  }
  const auto & state = controller->configure();
  if (state.id() != lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE) {
    return nullptr;
  }
  return controller;
}

}  // namespace

int run_full_loop_timing_check(
  const FullLoopTimingOptions & options,
  std::shared_ptr<M1Driver> mock_driver,
  std::ostream & out,
  std::ostream & err)
{
  auto val = validate_full_loop_options(options);
  if (!val.valid) {
    err << "FAIL: Invalid options: " << val.error_message << std::endl;
    return 1;
  }

  const double target_period_us = (1.0 / options.target_rate_hz) * 1e6;
  const double target_period_ms = target_period_us / 1000.0;
  const size_t total_expected_writes = 1 + options.warmup_cycles + options.measured_cycles + 1 + 1;

  if (options.dry_run && !options.execute) {
    out << "================================================================" << std::endl;
    out << "IMP-008 Full ros2_control Loop Timing Check (DRY-RUN)" << std::endl;
    out << "================================================================" << std::endl;
    out << "[SAFETY HAZARD NOTIFICATION]" << std::endl;
    out << "1. Servo-On creates holding torque on both drive wheels." << std::endl;
    out << "2. diff_drive_controller holds exactly 0 rad/s software zero-speed intent." <<
      std::endl;
    out << "3. Full ros2_control loop: "
        << "ResourceManager.read() -> DDC.update() -> ResourceManager.write()." << std::endl;
    out << "4. Physical E-Stop and power isolation remain strictly required on-site." << std::endl;
    out << "5. CRITICAL ARCHITECTURAL SAFETY: ALL COMMANDS HARD-BOUND TO ZERO VELOCITY." <<
      std::endl;
    out << "----------------------------------------------------------------" << std::endl;
    out << "Target Serial Port : " << options.device << " @ " << options.baud << " bps (8N1)" <<
      std::endl;
    out << "Driver IDs         : Driver A (Right)=" << options.driver_a
        << ", Driver B (Left)=" << options.driver_b << std::endl;
    out << "Target Loop Rate   : " << options.target_rate_hz << " Hz (Period = "
        << std::fixed << std::setprecision(3) << target_period_ms << " ms)" << std::endl;
    out << "Timeout Condition  : " << options.timeout_ms
        << " ms [PROVISIONAL LEVEL-3 TEST CONDITION; NOT PRODUCTION DEFAULT]" << std::endl;
    out << "Warm-up Cycles     : " << options.warmup_cycles << std::endl;
    out << "Measured Cycles    : " << options.measured_cycles << std::endl;
    out << "Expected Writes    : " << total_expected_writes << " control writes" << std::endl;
    out << "Mode               : DRY RUN / PREVIEW (0 transport calls)" << std::endl;
    out << "----------------------------------------------------------------" << std::endl;
    out << "PLANNED EXECUTION SEQUENCE:" << std::endl;
    out << "  1. Read-only pre-flight baseline (verify Status=6, Alarm=0, RPM=0)" << std::endl;
    out << "  2. Initialize ResourceManager (instantiates M1Hardware via pluginlib)" << std::endl;
    out << "  3. Activate M1Hardware lifecycle (issues SVON enable)" << std::endl;
    out << "  4. Configure and activate diff_drive_controller (zero cmd_vel reference)" <<
      std::endl;
    out << "  5. Warm-up Loop: " << options.warmup_cycles << " full ros2_control cycles @ "
        << options.target_rate_hz << " Hz" << std::endl;
    out << "  6. Measured Loop: " << options.measured_cycles << " full ros2_control cycles @ "
        << options.target_rate_hz << " Hz with in-memory timestamp recording" << std::endl;
    out << "  7. Anomaly detection: Immediate abort & best-effort cleanup "
        << "if RPM!=0, Alarm!=0, or error" << std::endl;
    out << "  8. Deactivate diff_drive_controller" << std::endl;
    out << "  9. Deactivate M1Hardware (issues stop(0) and disable(SVOFF))" << std::endl;
    out << " 10. Read-only post-check: verify Status=6, Alarm=0, RPM=0" << std::endl;
    out << " 11. Compute latency distributions, period jitter, and deadline overruns" << std::endl;
    out << "================================================================" << std::endl;
    return 0;
  }

  // Real execution mode
  if (!rclcpp::ok()) {
    rclcpp::init(0, nullptr);
  }

  out << "================================================================" << std::endl;
  out << "IMP-008 Full ros2_control Loop Timing Check (EXECUTING)" << std::endl;
  out << "Target Device     : " << options.device << " @ " << options.baud << " bps" << std::endl;
  out << "Target Loop Rate  : " << options.target_rate_hz << " Hz (Period = "
      << std::fixed << std::setprecision(3) << target_period_ms << " ms)" << std::endl;
  out << "Timeout Condition : " << options.timeout_ms
      << " ms [PROVISIONAL LEVEL-3 TEST CONDITION; NOT PRODUCTION DEFAULT]" << std::endl;
  out << "================================================================" << std::endl;

  // Step 1: Pre-flight baseline check
  if (!mock_driver) {
    M1Driver baseline_driver;
    auto conn_res = baseline_driver.connect(options.device, options.baud, options.timeout_ms, 'N',
        8, 1);
    if (!conn_res.ok) {
      err << "FAIL: Baseline connection failed: " << error_code_to_string(conn_res.error) <<
        std::endl;
      return 2;
    }
    auto pre_res = baseline_driver.read_state(options.driver_a, options.driver_b);
    if (!pre_res.ok) {
      err << "FAIL: Baseline read_state failed: " << error_code_to_string(pre_res.error) <<
        std::endl;
      baseline_driver.disconnect();
      return 3;
    }
    const auto & pre_a = pre_res.value.states[0];
    const auto & pre_b = pre_res.value.states[1];
    if (pre_a.status != 6 || pre_b.status != 6 || pre_a.alarm != 0 || pre_b.alarm != 0 ||
      pre_a.actual_rpm != 0 || pre_b.actual_rpm != 0)
    {
      err << "ABORT: Pre-flight check failed (not in clean Servo-Off baseline)." << std::endl;
      baseline_driver.disconnect();
      return 4;
    }
    baseline_driver.disconnect();
  }

  // Step 2: Build URDF and initialize ResourceManager
  const std::string urdf = build_full_loop_urdf(options);
  auto clock = std::make_shared<rclcpp::Clock>(RCL_ROS_TIME);
  auto logger = rclcpp::get_logger("full_loop_timing_check");

  std::unique_ptr<hardware_interface::ResourceManager> rm;
  try {
    rm = std::make_unique<hardware_interface::ResourceManager>(urdf, clock, logger, true);
  } catch (const std::exception & e) {
    err << "FAIL: ResourceManager initialization exception: " << e.what() << std::endl;
    return 5;
  }

  if (!rm->are_components_initialized()) {
    err << "FAIL: ResourceManager components failed to initialize." << std::endl;
    return 6;
  }

  // Step 3: Configure diff_drive_controller
  auto controller = create_diff_drive_controller(options.target_rate_hz);
  if (!controller) {
    err << "FAIL: diff_drive_controller creation/configuration failed." << std::endl;
    return 7;
  }

  std::vector<hardware_interface::LoanedCommandInterface> loaned_commands;
  loaned_commands.emplace_back(rm->claim_command_interface("driving_wheel_joint_L/velocity"));
  loaned_commands.emplace_back(rm->claim_command_interface("driving_wheel_joint_R/velocity"));

  std::vector<hardware_interface::LoanedStateInterface> loaned_states;
  loaned_states.emplace_back(rm->claim_state_interface("driving_wheel_joint_L/position"));
  loaned_states.emplace_back(rm->claim_state_interface("driving_wheel_joint_L/velocity"));
  loaned_states.emplace_back(rm->claim_state_interface("driving_wheel_joint_R/position"));
  loaned_states.emplace_back(rm->claim_state_interface("driving_wheel_joint_R/velocity"));

  controller->assign_interfaces(std::move(loaned_commands), std::move(loaned_states));

  const auto & active_state = controller->get_node()->activate();
  if (active_state.id() != lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE) {
    err << "FAIL: diff_drive_controller activation failed." << std::endl;
    return 8;
  }

  const auto loop_period = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::duration<double>(1.0 / options.target_rate_hz));
  const auto period_duration = rclcpp::Duration(loop_period);
  auto current_time = clock->now();

  // Step 4: Warm-up Loop
  if (options.warmup_cycles > 0) {
    out << "[Step 4] Executing " << options.warmup_cycles << " warm-up cycles @ "
        << options.target_rate_hz << " Hz..." << std::endl;
    for (size_t i = 0; i < options.warmup_cycles; ++i) {
      const auto cycle_start = std::chrono::steady_clock::now();
      current_time = current_time + period_duration;

      rm->read(current_time, period_duration);
      controller->update(current_time, period_duration);
      rm->write(current_time, period_duration);

      const auto cycle_end = std::chrono::steady_clock::now();
      const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(cycle_end -
          cycle_start);
      if (loop_period > elapsed) {
        std::this_thread::sleep_for(loop_period - elapsed);
      }
    }
  }

  // Step 5: Measured Loop (In-Memory Collection)
  out << "[Step 5] Measuring " << options.measured_cycles << " full ros2_control cycles @ "
      << options.target_rate_hz << " Hz..." << std::endl;

  std::vector<FullLoopCycleSample> samples;
  samples.reserve(options.measured_cycles);
  bool abort_triggered = false;

  auto prev_cycle_start = std::chrono::steady_clock::now();
  const auto measurement_anchor = prev_cycle_start;

  for (size_t i = 0; i < options.measured_cycles; ++i) {
    FullLoopCycleSample sample{};
    sample.seq = i + 1;

    const auto cycle_start = std::chrono::steady_clock::now();
    current_time = current_time + period_duration;

    if (i > 0) {
      sample.period_interval_us = std::chrono::duration<double, std::micro>(
        cycle_start - prev_cycle_start).count();
    } else {
      sample.period_interval_us = target_period_us;
    }
    prev_cycle_start = cycle_start;

    // A. Read Phase
    const auto read_start = std::chrono::steady_clock::now();
    const auto read_ret = rm->read(current_time, period_duration);
    const auto read_end = std::chrono::steady_clock::now();
    sample.read_duration_us = std::chrono::duration<double,
        std::micro>(read_end - read_start).count();

    // B. Controller Update Phase
    const auto ctrl_start = std::chrono::steady_clock::now();
    const auto ctrl_ret = controller->update(current_time, period_duration);
    const auto ctrl_end = std::chrono::steady_clock::now();
    sample.controller_duration_us = std::chrono::duration<double,
        std::micro>(ctrl_end - ctrl_start).count();

    // C. Write Phase (FC17 transaction)
    const auto write_start = std::chrono::steady_clock::now();
    const auto write_ret = rm->write(current_time, period_duration);
    const auto write_end = std::chrono::steady_clock::now();
    sample.write_duration_us = std::chrono::duration<double,
        std::micro>(write_end - write_start).count();

    // Total Cycle Duration
    sample.cycle_duration_us = std::chrono::duration<double,
        std::micro>(write_end - cycle_start).count();
    sample.deadline_missed = (sample.cycle_duration_us > target_period_us);
    sample.ok = (read_ret.result == hardware_interface::return_type::OK &&
      ctrl_ret == controller_interface::return_type::OK &&
      write_ret.result == hardware_interface::return_type::OK);

    samples.push_back(sample);

    if (!sample.ok) {
      err << "FAIL: ros2_control cycle returned error at cycle " << sample.seq << std::endl;
      abort_triggered = true;
      break;
    }

    // Precise sleep to next cycle boundary
    const auto next_cycle_target = measurement_anchor + (i + 1) * loop_period;
    const auto now = std::chrono::steady_clock::now();
    if (next_cycle_target > now) {
      std::this_thread::sleep_for(next_cycle_target - now);
    }
  }

  // Step 6: Safe Cleanup Sequence
  out << "[Step 6] Executing safe shutdown sequence..." << std::endl;
  controller->get_node()->deactivate();
  rm.reset();  // Calls M1Hardware destructor -> safe stop & disable

  // Step 7: Post-flight read-only state check
  if (!mock_driver) {
    M1Driver post_driver;
    if (post_driver.connect(options.device, options.baud, options.timeout_ms, 'N', 8, 1).ok) {
      auto post_res = post_driver.read_state(options.driver_a, options.driver_b);
      if (post_res.ok) {
        out << "Post-check Driver 1: Status=" << post_res.value.states[0].status
            << ", Alarm=" << post_res.value.states[0].alarm
            << ", Actual RPM=" << post_res.value.states[0].actual_rpm << std::endl;
        out << "Post-check Driver 2: Status=" << post_res.value.states[1].status
            << ", Alarm=" << post_res.value.states[1].alarm
            << ", Actual RPM=" << post_res.value.states[1].actual_rpm << std::endl;
      }
      post_driver.disconnect();
    }
  }

  // Write Raw CSV if requested
  if (!options.raw_output_path.empty()) {
    std::ofstream csv(options.raw_output_path);
    if (csv.is_open()) {
      csv << "seq,cycle_duration_us,period_interval_us,read_duration_us,"
          << "controller_duration_us,write_duration_us,deadline_missed,ok\n";
      for (const auto & s : samples) {
        csv << s.seq << ","
            << std::fixed << std::setprecision(2)
            << s.cycle_duration_us << ","
            << s.period_interval_us << ","
            << s.read_duration_us << ","
            << s.controller_duration_us << ","
            << s.write_duration_us << ","
            << (s.deadline_missed ? 1 : 0) << ","
            << (s.ok ? 1 : 0) << "\n";
      }
      csv.close();
      out << "Raw timing CSV saved to: " << options.raw_output_path << std::endl;
    } else {
      err << "WARNING: Could not open raw output path: " << options.raw_output_path << std::endl;
    }
  }

  // Step 8: Statistics Aggregation & Reporting
  std::vector<double> cycle_durations, write_durations, read_durations, ctrl_durations,
    period_intervals;
  size_t deadline_miss_count = 0;
  size_t success_count = 0;

  for (const auto & s : samples) {
    if (s.ok) {
      ++success_count;
      cycle_durations.push_back(s.cycle_duration_us);
      write_durations.push_back(s.write_duration_us);
      read_durations.push_back(s.read_duration_us);
      ctrl_durations.push_back(s.controller_duration_us);
      period_intervals.push_back(s.period_interval_us);
    }
    if (s.deadline_missed) {
      ++deadline_miss_count;
    }
  }

  auto cycle_stats = LatencyStats::compute_from_values(cycle_durations);
  auto write_stats = LatencyStats::compute_from_values(write_durations);
  auto period_stats = LatencyStats::compute_from_values(period_intervals);

  out << "\n================================================================" << std::endl;
  out << "       FULL ROS2_CONTROL LOOP 30 HZ TIMING RESULTS              " << std::endl;
  out << "================================================================" << std::endl;
  out << "Target Rate       : " << options.target_rate_hz << " Hz (Period = "
      << std::fixed << std::setprecision(3) << target_period_ms << " ms)" << std::endl;
  out << "Total Samples     : " << samples.size() << std::endl;
  out << "Successful Samples: " << success_count << std::endl;
  out << "Failed Samples    : " << (samples.size() - success_count) << std::endl;
  out << "Deadline Misses   : " << deadline_miss_count << " ("
      << std::fixed << std::setprecision(2)
      << (samples.empty() ? 0.0 : (static_cast<double>(deadline_miss_count) * 100.0 /
  static_cast<double>(samples.size())))
      << " %)" << std::endl;
  out << "----------------------------------------------------------------" << std::endl;
  out << "Metric                     Full Cycle (ms)  FC17 Write (ms)  Period Interval (ms)" <<
    std::endl;
  out << "----------------------------------------------------------------" << std::endl;
  out << "Min                      : " << std::setw(15) << cycle_stats.min_us / 1000.0
      << "  " << std::setw(15) << write_stats.min_us / 1000.0
      << "  " << std::setw(18) << period_stats.min_us / 1000.0 << std::endl;
  out << "Mean                     : " << std::setw(15) << cycle_stats.mean_us / 1000.0
      << "  " << std::setw(15) << write_stats.mean_us / 1000.0
      << "  " << std::setw(18) << period_stats.mean_us / 1000.0 << std::endl;
  out << "Median (p50)             : " << std::setw(15) << cycle_stats.p50_us / 1000.0
      << "  " << std::setw(15) << write_stats.p50_us / 1000.0
      << "  " << std::setw(18) << period_stats.p50_us / 1000.0 << std::endl;
  out << "p90                      : " << std::setw(15) << cycle_stats.p90_us / 1000.0
      << "  " << std::setw(15) << write_stats.p90_us / 1000.0
      << "  " << std::setw(18) << period_stats.p90_us / 1000.0 << std::endl;
  out << "p95                      : " << std::setw(15) << cycle_stats.p95_us / 1000.0
      << "  " << std::setw(15) << write_stats.p95_us / 1000.0
      << "  " << std::setw(18) << period_stats.p95_us / 1000.0 << std::endl;
  out << "p99                      : " << std::setw(15) << cycle_stats.p99_us / 1000.0
      << "  " << std::setw(15) << write_stats.p99_us / 1000.0
      << "  " << std::setw(18) << period_stats.p99_us / 1000.0 << std::endl;
  out << "Max                      : " << std::setw(15) << cycle_stats.max_us / 1000.0
      << "  " << std::setw(15) << write_stats.max_us / 1000.0
      << "  " << std::setw(18) << period_stats.max_us / 1000.0 << std::endl;
  out << "StdDev                   : " << std::setw(15) << cycle_stats.stddev_us / 1000.0
      << "  " << std::setw(15) << write_stats.stddev_us / 1000.0
      << "  " << std::setw(18) << period_stats.stddev_us / 1000.0 << std::endl;
  out << "================================================================" << std::endl;

  if (abort_triggered) {
    err << "PRIMARY MEASUREMENT FAILED: Loop aborted due to fault/anomaly." << std::endl;
    return 10;
  }

  return 0;
}

}  // namespace mobile_base_control
