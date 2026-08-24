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

#include "mobile_base_control/m1_fc17_latency_check.hpp"

#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

namespace mobile_base_control
{

namespace
{
bool write_detailed_csv(
  const std::string & path, const std::vector<SampleRecord> & records, std::ostream & err)
{
  if (path.empty()) {
    return true;
  }
  std::ofstream out_file(path);
  if (!out_file.is_open()) {
    err << "FAIL: Could not open raw timing output: " << path << std::endl;
    return false;
  }
  out_file << "seq,tx_syscall_us,wait_first_rx_us,rx_duration_us,total_us,ok,error,"
    "driver1_alarm,driver1_rpm,driver2_alarm,driver2_rpm\n";
  for (const auto & rec : records) {
    out_file << rec.seq << "," << std::fixed << std::setprecision(2)
             << rec.tx_syscall_us << "," << rec.wait_first_rx_us << ","
             << rec.rx_duration_us << "," << rec.detailed_total_us << ","
             << (rec.ok ? 1 : 0) << "," << static_cast<int>(rec.error) << ","
             << rec.driver1_alarm << "," << rec.driver1_rpm << ","
             << rec.driver2_alarm << "," << rec.driver2_rpm << "\n";
  }
  return true;
}
}  // namespace

Fc17LatencyCheckOptions parse_fc17_latency_command_line(int argc, char ** argv)
{
  Fc17LatencyCheckOptions opts;

  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];

    // Explicit rejection of motion parameters
    if (arg.rfind("--rpm", 0) == 0 || arg.rfind("--vel", 0) == 0 ||
      arg.rfind("--speed", 0) == 0 || arg.rfind("--linear", 0) == 0 ||
      arg.rfind("--angular", 0) == 0)
    {
      throw std::invalid_argument(
              "Security Error: Non-zero motion parameter '" + arg + "' is strictly forbidden.");
    }

    if (arg == "--device" && i + 1 < argc) {
      opts.device = argv[++i];
    } else if (arg == "--baud" && i + 1 < argc) {
      opts.baud = std::stoi(argv[++i]);
    } else if (arg == "--timeout-ms" && i + 1 < argc) {
      opts.timeout_ms = static_cast<uint32_t>(std::stoul(argv[++i]));
    } else if (arg == "--driver-a" && i + 1 < argc) {
      opts.driver_a = std::stoi(argv[++i]);
    } else if (arg == "--driver-b" && i + 1 < argc) {
      opts.driver_b = std::stoi(argv[++i]);
    } else if (arg == "--warmup" && i + 1 < argc) {
      opts.warmup_samples = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--samples" && i + 1 < argc) {
      opts.measured_samples = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--delay-ms" && i + 1 < argc) {
      opts.delay_ms = std::stoi(argv[++i]);
    } else if (arg == "--dry-run") {
      opts.dry_run = true;
    } else if (arg == "--execute") {
      opts.execute = true;
    } else if (arg == "--raw-output" && i + 1 < argc) {
      opts.raw_output_file = argv[++i];
    }
  }

  return opts;
}

Fc17ValidationResult validate_fc17_latency_options(const Fc17LatencyCheckOptions & opts)
{
  if (opts.driver_a < 1 || opts.driver_a > 8) {
    return {false, "driver-a ID must be between 1 and 8"};
  }
  if (opts.driver_b < 1 || opts.driver_b > 8) {
    return {false, "driver-b ID must be between 1 and 8"};
  }
  if (opts.driver_a == opts.driver_b) {
    return {false, "driver-a and driver-b IDs must be distinct"};
  }
  if (opts.timeout_ms < 1 || opts.timeout_ms > 1000) {
    return {false, "timeout_ms must be between 1 and 1000 ms"};
  }
  if (opts.warmup_samples > FC17_MAX_WARMUP_SAMPLES) {
    return {false, "warmup_samples exceeds hard maximum limit of 100"};
  }
  if (opts.measured_samples == 0 || opts.measured_samples > FC17_MAX_MEASURED_SAMPLES) {
    return {false, "measured_samples must be between 1 and 2000"};
  }

  return {true, ""};
}

int run_fc17_latency_check(
  const Fc17LatencyCheckOptions & opts,
  M1Driver & driver,
  std::ostream & out,
  std::ostream & err)
{
  auto val = validate_fc17_latency_options(opts);
  if (!val.valid) {
    err << "Configuration validation failed: " << val.error_message << std::endl;
    return 1;
  }

  // Dry-run mode (default if --execute is not provided or --dry-run is set)
  if (opts.dry_run || !opts.execute) {
    out << "================================================================" << std::endl;
    out << "IMP-008 Level 3 FC17 Zero-Speed Latency Measurement (DRY-RUN)" << std::endl;
    out << "================================================================" << std::endl;
    out << "[SAFETY HAZARD NOTIFICATION]" << std::endl;
    out << "1. Servo-On creates holding torque on both drive wheels." << std::endl;
    out << "2. JG 0 represents software zero-speed intent; it is NOT a certified safety stop."
        << std::endl;
    out << "3. Process crash (SIGKILL/segfault/hang) can prevent execution of stop()/disable()."
        << std::endl;
    out << "4. Physical E-Stop and power isolation remain strictly required on-site." << std::endl;
    out << "5. CRITICAL ARCHITECTURAL SAFETY: BOTH MOTOR TARGETS HARD-BOUND TO 0 RPM." << std::endl;
    out << "----------------------------------------------------------------" << std::endl;
    out << "Target Serial Port : " << opts.device << " @ " << opts.baud << " bps (8N1)" <<
      std::endl;
    out << "Driver IDs         : Driver A (Right)=" << opts.driver_a
        << ", Driver B (Left)=" << opts.driver_b << std::endl;
    out << "Timeout Condition  : " << opts.timeout_ms
        << " ms [PROVISIONAL LEVEL-3 TEST CONDITION; NOT PRODUCTION DEFAULT]" << std::endl;
    out << "Warm-up Samples    : " << opts.warmup_samples << std::endl;
    out << "Measured Samples   : " << opts.measured_samples << std::endl;
    out << "Mode               : DRY RUN / PREVIEW (0 transport calls)" << std::endl;
    out << "----------------------------------------------------------------" << std::endl;
    out << "PLANNED EXECUTION SEQUENCE:" << std::endl;
    out << "  1. Connect to " << opts.device << std::endl;
    out << "  2. Read-only pre-flight baseline (read_state, verify Alarm=0, RPM=0)" << std::endl;
    out << "  3. enable(" << opts.driver_a << ", " << opts.driver_b << ") (SVON write)" <<
      std::endl;
    out << "  4. Bounded polling until drives reach Active (Status=0, Alarm=0, RPM=0)" << std::endl;
    out << "  5. Warm-up: " << opts.warmup_samples << " x FC17 JG 0 exchange_zero()" << std::endl;
    out << "  6. Measured Loop: " << opts.measured_samples
        << " x FC17 JG 0 exchange_zero() with monotonic steady_clock timing" << std::endl;
    out << "  7. Anomaly detection: Immediate abort & best-effort cleanup if RPM!=0 or Alarm!=0"
        << std::endl;
    out << "  8. stop(" << opts.driver_a << ", " << opts.driver_b << ") (JG 0 write)" << std::endl;
    out << "  9. disable(" << opts.driver_a << ", " << opts.driver_b << ") (SVOFF write)" <<
      std::endl;
    out << " 10. Read-only post-check: verify Status=6, Alarm=0, RPM=0" << std::endl;
    out << " 11. Disconnect and output LatencyStats summary" << std::endl;
    out << "================================================================" << std::endl;
    return 0;
  }

  // Real execution path (strictly for operator execution-time authorized sessions)
  out << "================================================================" << std::endl;
  out << "IMP-008 Level 3 FC17 Zero-Speed Latency Measurement (EXECUTING)" << std::endl;
  out << "Target Device     : " << opts.device << " @ " << opts.baud << " bps" << std::endl;
  out << "Timeout Condition : " << opts.timeout_ms
      << " ms [PROVISIONAL LEVEL-3 TEST CONDITION; NOT PRODUCTION DEFAULT]" << std::endl;
  out << "================================================================" << std::endl;

  // Step 1: Connect
  auto conn_res = driver.connect(opts.device, opts.baud, opts.timeout_ms, 'N', 8, 1);
  if (!conn_res.ok) {
    err << "FAIL: Connection failed: " << error_code_to_string(conn_res.error) << std::endl;
    return 2;
  }

  // Step 2: Read-Only Pre-flight Check
  auto pre_res = driver.read_state(opts.driver_a, opts.driver_b);
  if (!pre_res.ok) {
    err << "FAIL: Pre-flight read_state failed: " << error_code_to_string(pre_res.error)
        << std::endl;
    driver.disconnect();
    return 3;
  }
  const auto & pre_a = pre_res.value.states[0];
  const auto & pre_b = pre_res.value.states[1];
  if (pre_a.alarm != 0 || pre_b.alarm != 0) {
    err << "ABORT: Pre-flight check failed: Active alarm detected (D" << opts.driver_a
        << "=" << pre_a.alarm << ", D" << opts.driver_b << "=" << pre_b.alarm << ")" << std::endl;
    driver.disconnect();
    return 4;
  }
  if (pre_a.actual_rpm != 0 || pre_b.actual_rpm != 0) {
    err << "ABORT: Pre-flight check failed: Non-zero RPM detected (D" << opts.driver_a
        << "=" << pre_a.actual_rpm << ", D" << opts.driver_b << "=" << pre_b.actual_rpm << ")"
        << std::endl;
    driver.disconnect();
    return 5;
  }

  // Step 3: Enable (SVON)
  out << "[Step 3] Enabling drivers (SVON)..." << std::endl;
  auto enable_res = driver.enable(opts.driver_a, opts.driver_b);
  if (!enable_res.ok) {
    err << "FAIL: Enable command failed: " << error_code_to_string(enable_res.error) << std::endl;
    driver.disable(opts.driver_a, opts.driver_b);
    driver.disconnect();
    return 6;
  }

  // Bounded polling for Servo-On confirmation
  bool activated = false;
  for (int attempt = 0; attempt < 10; ++attempt) {
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    auto poll_res = driver.read_state(opts.driver_a, opts.driver_b);
    if (!poll_res.ok) {
      continue;
    }
    const auto & st_a = poll_res.value.states[0];
    const auto & st_b = poll_res.value.states[1];
    if (st_a.alarm != 0 || st_b.alarm != 0 || st_a.actual_rpm != 0 || st_b.actual_rpm != 0) {
      err << "EMERGENCY ABORT during activation: Drive fault detected." << std::endl;
      driver.stop(opts.driver_a, opts.driver_b);
      driver.disable(opts.driver_a, opts.driver_b);
      driver.disconnect();
      return 7;
    }
    if (st_a.status == 0 && st_b.status == 0) {
      activated = true;
      break;
    }
  }

  if (!activated) {
    err << "FAIL: Activation timed out waiting for Status=0" << std::endl;
    driver.stop(opts.driver_a, opts.driver_b);
    driver.disable(opts.driver_a, opts.driver_b);
    driver.disconnect();
    return 8;
  }

  // Step 4: Warm-up Phase
  if (opts.warmup_samples > 0) {
    out << "[Step 4] Executing " << opts.warmup_samples << " warm-up FC17 transactions..."
        << std::endl;
    for (size_t i = 0; i < opts.warmup_samples; ++i) {
      auto res = driver.exchange_zero(opts.driver_a, opts.driver_b);
      if (!res.ok) {
        err << "WARNING: Warm-up sample " << i + 1 << " failed: "
            << error_code_to_string(res.error) << std::endl;
      }
    }
  }

  // Step 5: Measured FC17 JG 0 Latency Phase
  out << "[Step 5] Measuring " << opts.measured_samples << " FC17 JG 0 transactions..." <<
    std::endl;
  std::vector<SampleRecord> records;
  records.reserve(opts.measured_samples);
  if (!opts.raw_output_file.empty()) {
    driver.begin_detailed_timing_capture(opts.measured_samples);
  }

  bool abort_triggered = false;
  for (size_t i = 0; i < opts.measured_samples; ++i) {
    SampleRecord rec;
    rec.seq = i + 1;

    const auto t_start = std::chrono::steady_clock::now();
    auto res = driver.exchange_zero(opts.driver_a, opts.driver_b);
    const auto t_end = std::chrono::steady_clock::now();

    rec.elapsed_us = std::chrono::duration<double, std::micro>(t_end - t_start).count();
    rec.ok = res.ok;
    rec.error = res.error;

    if (res.ok) {
      rec.driver1_alarm = res.value.states[0].alarm;
      rec.driver1_rpm = res.value.states[0].actual_rpm;
      rec.driver2_alarm = res.value.states[1].alarm;
      rec.driver2_rpm = res.value.states[1].actual_rpm;

      if (rec.driver1_alarm != 0 || rec.driver2_alarm != 0 ||
        rec.driver1_rpm != 0 || rec.driver2_rpm != 0)
      {
        err << "EMERGENCY ABORT at sample " << rec.seq << ": Non-zero RPM or Alarm detected!"
            << std::endl;
        records.push_back(rec);
        abort_triggered = true;
        break;
      }
    } else {
      err << "Communication failure at sample " << rec.seq << ": "
          << error_code_to_string(res.error) << std::endl;
      records.push_back(rec);
      abort_triggered = true;
      break;
    }

    records.push_back(rec);

    if (opts.delay_ms > 0) {
      std::this_thread::sleep_for(std::chrono::milliseconds(opts.delay_ms));
    }
  }

  std::vector<TransactionTiming> detailed_timings;
  if (!opts.raw_output_file.empty()) {
    detailed_timings = driver.end_detailed_timing_capture();
    for (size_t i = 0; i < records.size() && i < detailed_timings.size(); ++i) {
      records[i].tx_syscall_us = detailed_timings[i].tx_syscall_us;
      records[i].wait_first_rx_us = detailed_timings[i].wait_first_rx_us;
      records[i].rx_duration_us = detailed_timings[i].rx_duration_us;
      records[i].detailed_total_us = detailed_timings[i].total_us;
    }
  }

  // Step 6 & 7: Ordered Cleanup Sequence
  out << "[Step 6] Executing safe stop and disable cleanup sequence..." << std::endl;
  auto stop_res = driver.stop(opts.driver_a, opts.driver_b);
  std::this_thread::sleep_for(std::chrono::milliseconds(20));
  auto disable_res = driver.disable(opts.driver_a, opts.driver_b);

  if (!stop_res.ok || !disable_res.ok) {
    err << "CRITICAL: Cleanup stop or disable returned error! "
        << "(stop err=" << error_code_to_string(stop_res.error)
        << ", disable err=" << error_code_to_string(disable_res.error) << ")" << std::endl;
  }

  // Step 8: Final read-only check
  auto post_res = driver.read_state(opts.driver_a, opts.driver_b);
  if (post_res.ok) {
    const auto & pst_a = post_res.value.states[0];
    const auto & pst_b = post_res.value.states[1];
    out << "Post-check Driver " << opts.driver_a << ": Status=" << pst_a.status
        << ", Alarm=" << pst_a.alarm << ", Actual RPM=" << pst_a.actual_rpm << std::endl;
    out << "Post-check Driver " << opts.driver_b << ": Status=" << pst_b.status
        << ", Alarm=" << pst_b.alarm << ", Actual RPM=" << pst_b.actual_rpm << std::endl;
  }

  driver.disconnect();

  const bool csv_written = write_detailed_csv(opts.raw_output_file, records, err);

  if (abort_triggered) {
    err << "PRIMARY MEASUREMENT FAILED: Best-effort cleanup was executed, "
        << "but best-effort cleanup is NOT an independent safety guarantee." << std::endl;
    return 10;
  }
  if (!csv_written) {
    return 11;
  }

  // Step 9: Statistical output
  const auto stats = LatencyStats::compute(records);
  out << "\n================================================================" << std::endl;
  out << "            FC17 ZERO-SPEED LATENCY MEASUREMENT RESULTS         " << std::endl;
  out << "================================================================" << std::endl;
  out << "Total Samples     : " << stats.total_samples << std::endl;
  out << "Successful Samples: " << stats.success_count << std::endl;
  out << "Failed Samples    : " << stats.failure_count << std::endl;
  out << "Timeouts          : " << stats.timeout_count << std::endl;
  out << "----------------------------------------------------------------" << std::endl;
  out << std::left << std::setw(20) << "Metric"
      << std::right << std::setw(15) << "Microseconds (us)"
      << std::setw(18) << "Milliseconds (ms)" << std::endl;
  out << "----------------------------------------------------------------" << std::endl;
  out << std::left << std::setw(20) << "Min"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.min_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.min_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "Mean"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.mean_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.mean_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "Median (p50)"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p50_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.p50_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "p90"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p90_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.p90_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "p95"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p95_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.p95_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "p99"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p99_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.p99_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "Max"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.max_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.max_us / 1000.0 << std::endl;
  out << std::left << std::setw(20) << "StdDev"
      << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.stddev_us
      << std::setw(18) << std::fixed << std::setprecision(3) << stats.stddev_us / 1000.0 <<
    std::endl;
  out << "================================================================" << std::endl;

  return 0;
}

}  // namespace mobile_base_control
