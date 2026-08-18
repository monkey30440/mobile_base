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

#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_latency_stats.hpp"

using mobile_base_control::ErrorCode;
using mobile_base_control::M1Driver;
using mobile_base_control::LatencyStats;
using mobile_base_control::SampleRecord;
using mobile_base_control::error_code_to_string;

namespace
{

struct CliOptions
{
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  int timeout_ms{100};  // TEST CONDITION ONLY; NOT PRODUCTION DEFAULT
  int driver_a{1};      // Right
  int driver_b{2};      // Left
  size_t warmup_samples{20};
  size_t measured_samples{1000};
  int delay_ms{0};
  std::string raw_output_file{""};
};

CliOptions parse_cli(int argc, char ** argv)
{
  CliOptions opts;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
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
    } else if (arg == "--warmup" && i + 1 < argc) {
      opts.warmup_samples = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--samples" && i + 1 < argc) {
      opts.measured_samples = static_cast<size_t>(std::stoul(argv[++i]));
    } else if (arg == "--delay-ms" && i + 1 < argc) {
      opts.delay_ms = std::stoi(argv[++i]);
    } else if (arg == "--raw-output" && i + 1 < argc) {
      opts.raw_output_file = argv[++i];
    }
  }
  return opts;
}

}  // namespace

int main(int argc, char ** argv)
{
  const auto opts = parse_cli(argc, argv);

  std::cout << "================================================================" << std::endl;
  std::cout << "IMP-008 Level 2 Read-Only Hardware Latency / Jitter Measurement" << std::endl;
  std::cout << "Safety Boundary : STRICTLY READ-ONLY (No enable/stop/disable/writes)" << std::endl;
  std::cout << "Target Device   : " << opts.device << " @ " << opts.baud << " bps (8N1)" <<
    std::endl;
  std::cout << "Driver IDs      : Driver A (Right)=" << opts.driver_a
            << ", Driver B (Left)=" << opts.driver_b << std::endl;
  std::cout << "Timeout (Test)  : " << opts.timeout_ms
            << " ms [TEST CONDITION ONLY; NOT PRODUCTION DEFAULT]" << std::endl;
  std::cout << "Warm-up Samples : " << opts.warmup_samples << std::endl;
  std::cout << "Measured Samples: " << opts.measured_samples << std::endl;
  std::cout << "================================================================" << std::endl;

  M1Driver driver;

  // 1. Connect
  std::cout << "\n[Step 1] Connecting to serial bus..." << std::endl;
  auto conn_res = driver.connect(opts.device, opts.baud, opts.timeout_ms, 'N', 8, 1);
  if (!conn_res.ok) {
    std::cerr << "ABORT: Connection failed: " << error_code_to_string(conn_res.error) << std::endl;
    return 1;
  }
  std::cout << "Connected successfully." << std::endl;

  // 2. Pre-flight Read Baseline Checks
  std::cout << "\n[Step 2] Performing pre-flight read-only baseline checks..." << std::endl;
  auto init_state = driver.read_state(opts.driver_a, opts.driver_b);
  if (!init_state.ok) {
    std::cerr << "ABORT: Initial read_state failed: "
              << error_code_to_string(init_state.error) << std::endl;
    driver.disconnect();
    return 2;
  }

  const auto & st_a = init_state.value.states[0];
  const auto & st_b = init_state.value.states[1];
  std::cout << "Driver " << opts.driver_a << ": Status=" << st_a.status
            << ", Alarm=" << st_a.alarm << ", Actual RPM=" << st_a.actual_rpm
            << ", Pos=" << st_a.position_steps << std::endl;
  std::cout << "Driver " << opts.driver_b << ": Status=" << st_b.status
            << ", Alarm=" << st_b.alarm << ", Actual RPM=" << st_b.actual_rpm
            << ", Pos=" << st_b.position_steps << std::endl;

  if (st_a.alarm != 0 || st_b.alarm != 0) {
    std::cerr << "ABORT: Active alarm detected on drivers before test." << std::endl;
    driver.disconnect();
    return 3;
  }
  if (st_a.actual_rpm != 0 || st_b.actual_rpm != 0) {
    std::cerr << "ABORT: Non-zero RPM detected on wheels before test." << std::endl;
    driver.disconnect();
    return 4;
  }

  // Check static watchdog / MD2 configuration registers
  auto wd_a = driver.read_register(opts.driver_a, 0x0511);  // 05-17
  auto wd_b = driver.read_register(opts.driver_b, 0x0511);
  if (wd_a.ok && wd_b.ok) {
    std::cout << "Register 05-17 (Watchdog ms): ID " << opts.driver_a << "=" << wd_a.value
              << ", ID " << opts.driver_b << "=" << wd_b.value << std::endl;
  }

  // 3. Warm-up Phase
  if (opts.warmup_samples > 0) {
    std::cout << "\n[Step 3] Executing " << opts.warmup_samples
              << " warm-up transactions (discarded from statistics)..." << std::endl;
    for (size_t i = 0; i < opts.warmup_samples; ++i) {
      auto res = driver.read_state(opts.driver_a, opts.driver_b);
      if (!res.ok) {
        std::cerr << "WARNING: Warm-up sample " << i + 1 << " failed: "
                  << error_code_to_string(res.error) << std::endl;
      }
    }
    std::cout << "Warm-up completed." << std::endl;
  }

  // 4. Measured Latency Phase
  std::cout << "\n[Step 4] Measuring " << opts.measured_samples
            << " dual-driver read_state(" << opts.driver_a << ", " << opts.driver_b
            << ") transactions..." << std::endl;

  std::vector<SampleRecord> records;
  records.reserve(opts.measured_samples);

  for (size_t i = 0; i < opts.measured_samples; ++i) {
    SampleRecord rec;
    rec.seq = i + 1;

    const auto t_start = std::chrono::steady_clock::now();
    auto res = driver.read_state(opts.driver_a, opts.driver_b);
    const auto t_end = std::chrono::steady_clock::now();

    rec.elapsed_us = std::chrono::duration<double, std::micro>(t_end - t_start).count();
    rec.ok = res.ok;
    rec.error = res.error;

    if (res.ok) {
      rec.driver1_alarm = res.value.states[0].alarm;
      rec.driver1_rpm = res.value.states[0].actual_rpm;
      rec.driver2_alarm = res.value.states[1].alarm;
      rec.driver2_rpm = res.value.states[1].actual_rpm;

      // Anomaly detection: safety violation if motion or alarm occurs
      if (rec.driver1_alarm != 0 || rec.driver2_alarm != 0 ||
        rec.driver1_rpm != 0 || rec.driver2_rpm != 0)
      {
        std::cerr << "EMERGENCY ABORT at sample " << rec.seq
                  << ": Unexpected drive state detected! (D1: alarm=" << rec.driver1_alarm
                  << " rpm=" << rec.driver1_rpm << ", D2: alarm=" << rec.driver2_alarm
                  << " rpm=" << rec.driver2_rpm << ")" << std::endl;
        records.push_back(rec);
        driver.disconnect();
        return 10;
      }
    }

    records.push_back(rec);

    if (opts.delay_ms > 0) {
      std::this_thread::sleep_for(std::chrono::milliseconds(opts.delay_ms));
    }
  }

  // 5. Post-flight Verification
  std::cout << "\n[Step 5] Performing post-flight verification..." << std::endl;
  auto post_state = driver.read_state(opts.driver_a, opts.driver_b);
  if (post_state.ok) {
    const auto & pst_a = post_state.value.states[0];
    const auto & pst_b = post_state.value.states[1];
    std::cout << "Post-check Driver " << opts.driver_a << ": Status=" << pst_a.status
              << ", Alarm=" << pst_a.alarm << ", Actual RPM=" << pst_a.actual_rpm << std::endl;
    std::cout << "Post-check Driver " << opts.driver_b << ": Status=" << pst_b.status
              << ", Alarm=" << pst_b.alarm << ", Actual RPM=" << pst_b.actual_rpm << std::endl;

    if (pst_a.status != st_a.status || pst_b.status != st_b.status) {
      std::cout << "NOTE: Status word changed from (" << st_a.status << ", " << st_b.status
                << ") to (" << pst_a.status << ", " << pst_b.status << ")." << std::endl;
    }
  }

  driver.disconnect();

  // 6. Statistical Computation & Reporting
  const auto stats = LatencyStats::compute(records);

  std::cout << "\n================================================================" << std::endl;
  std::cout << "                    LATENCY MEASUREMENT RESULTS                 " << std::endl;
  std::cout << "================================================================" << std::endl;
  std::cout << "Total Samples     : " << stats.total_samples << std::endl;
  std::cout << "Successful Samples: " << stats.success_count << " ("
            << std::fixed << std::setprecision(2)
            << (100.0 * stats.success_count / (stats.total_samples ? stats.total_samples : 1))
            << " %)" << std::endl;
  std::cout << "Failed Samples    : " << stats.failure_count << std::endl;
  std::cout << "Timeouts          : " << stats.timeout_count << std::endl;
  std::cout << "----------------------------------------------------------------" << std::endl;
  std::cout << std::left << std::setw(20) << "Metric"
            << std::right << std::setw(15) << "Microseconds (us)"
            << std::setw(18) << "Milliseconds (ms)" << std::endl;
  std::cout << "----------------------------------------------------------------" << std::endl;
  std::cout << std::left << std::setw(20) << "Min"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.min_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.min_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "Mean"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.mean_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.mean_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "Median (p50)"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p50_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.p50_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "p90"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p90_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.p90_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "p95"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p95_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.p95_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "p99"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.p99_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.p99_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "Max"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.max_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.max_us / 1000.0
            << std::endl;
  std::cout << std::left << std::setw(20) << "StdDev"
            << std::right << std::setw(15) << std::fixed << std::setprecision(1) << stats.stddev_us
            << std::setw(18) << std::fixed << std::setprecision(3) << stats.stddev_us / 1000.0
            << std::endl;
  std::cout << "----------------------------------------------------------------" << std::endl;

  // Jitter / Outlier Observation
  const double max_to_median_ratio = (stats.p50_us > 0.0) ? (stats.max_us / stats.p50_us) : 0.0;
  const double p99_minus_p50_us = stats.p99_us - stats.p50_us;
  std::cout << "Max / Median Ratio: " << std::fixed << std::setprecision(2)
            << max_to_median_ratio << "x" << std::endl;
  std::cout << "p99 - Median (us) : " << std::fixed << std::setprecision(1)
            << p99_minus_p50_us << " us (" << (p99_minus_p50_us / 1000.0) << " ms)" << std::endl;

  // 20 ms Cycle Feasibility Analysis
  const double period_20ms_us = 20000.0;
  std::cout << "\n----------------------------------------------------------------" << std::endl;
  std::cout << "           MODEL A2 (50 Hz / 20 ms Cycle) TIMING ANALYSIS       " << std::endl;
  std::cout << "----------------------------------------------------------------" << std::endl;
  std::cout << "Mean Latency / 20 ms Period : " << std::fixed << std::setprecision(2)
            << (stats.mean_us / period_20ms_us * 100.0) << " %" << std::endl;
  std::cout << "p99  Latency / 20 ms Period : " << std::fixed << std::setprecision(2)
            << (stats.p99_us / period_20ms_us * 100.0) << " %" << std::endl;
  std::cout << "Max  Latency / 20 ms Period : " << std::fixed << std::setprecision(2)
            << (stats.max_us / period_20ms_us * 100.0) << " %" << std::endl;

  if (stats.max_us < period_20ms_us * 0.7) {
    std::cout << "Feasibility Observation     : Read latency envelope is well within 20 ms "
              << "(margin >= 30%), supporting 50 Hz controller cycle as viable for next testing."
              << std::endl;
  } else {
    std::cout << "Feasibility Observation     : Read latency approaches or exceeds 20 ms; "
              << "50 Hz controller cycle carries timing risk." << std::endl;
  }
  std::cout << "NOTE: Observation only. Final production update rate remains UNFROZEN." <<
    std::endl;
  std::cout << "================================================================" << std::endl;

  // 7. Optional Raw Output Export
  if (!opts.raw_output_file.empty()) {
    std::ofstream out(opts.raw_output_file);
    if (out.is_open()) {
      out << "seq,elapsed_us,ok,error,driver1_alarm,driver1_rpm,driver2_alarm,driver2_rpm\n";
      for (const auto & rec : records) {
        out << rec.seq << "," << std::fixed << std::setprecision(2) << rec.elapsed_us << ","
            << (rec.ok ? 1 : 0) << "," << static_cast<int>(rec.error) << ","
            << rec.driver1_alarm << "," << rec.driver1_rpm << ","
            << rec.driver2_alarm << "," << rec.driver2_rpm << "\n";
      }
      std::cout << "Raw sample records saved to: " << opts.raw_output_file << std::endl;
    }
  }

  return 0;
}
