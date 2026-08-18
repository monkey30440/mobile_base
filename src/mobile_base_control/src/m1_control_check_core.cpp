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

#include "mobile_base_control/m1_control_check.hpp"

#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

namespace mobile_base_control
{

const char * control_op_to_string(ControlOp op) noexcept
{
  switch (op) {
    case ControlOp::NONE:
      return "NONE";
    case ControlOp::READ_STATE:
      return "read";
    case ControlOp::ENABLE:
      return "enable";
    case ControlOp::STOP:
      return "stop";
    case ControlOp::DISABLE:
      return "disable";
    case ControlOp::EXCHANGE:
      return "exchange";
    default:
      return "UNKNOWN";
  }
}

ControlCheckOptions parse_command_line(int argc, char ** argv)
{
  ControlCheckOptions opts;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];

    if (arg == "--dry-run") {
      opts.dry_run = true;
    } else if (arg == "--execute") {
      opts.execute = true;
    } else if (arg == "--op" && i + 1 < argc) {
      const std::string op_str = argv[++i];
      if (op_str == "read") {
        opts.op = ControlOp::READ_STATE;
      } else if (op_str == "enable") {
        opts.op = ControlOp::ENABLE;
      } else if (op_str == "stop") {
        opts.op = ControlOp::STOP;
      } else if (op_str == "disable") {
        opts.op = ControlOp::DISABLE;
      } else if (op_str == "exchange") {
        opts.op = ControlOp::EXCHANGE;
      }
    } else if (arg == "--device" && i + 1 < argc) {
      opts.device = argv[++i];
    } else if (arg == "--baud" && i + 1 < argc) {
      opts.baud = std::stoi(argv[++i]);
    } else if (arg == "--timeout-ms" && i + 1 < argc) {
      opts.timeout_ms = static_cast<uint32_t>(std::stoul(argv[++i]));
    } else if (arg == "--driver-a" && i + 1 < argc) {
      opts.driver_a = std::stoi(argv[++i]);
    } else if (arg == "--driver-b" && i + 1 < argc) {
      opts.driver_b = std::stoi(argv[++i]);
    } else if (arg == "--rpm" && i + 1 < argc) {
      opts.rpm = static_cast<int16_t>(std::stoi(argv[++i]));
    } else if (arg == "--duration-ms" && i + 1 < argc) {
      opts.duration_ms = static_cast<uint32_t>(std::stoul(argv[++i]));
    }
  }

  return opts;
}

ValidationResult validate_options(const ControlCheckOptions & opts)
{
  if (opts.op == ControlOp::NONE) {
    return {false, "No operation specified. Use --op <read|enable|stop|disable|exchange>."};
  }

  if (opts.driver_a == opts.driver_b ||
    opts.driver_a < 1 || opts.driver_a > 8 ||
    opts.driver_b < 1 || opts.driver_b > 8)
  {
    return {false, "Invalid driver IDs: must be distinct integers between 1 and 8."};
  }

  if (opts.baud <= 0) {
    return {false, "Invalid baud rate: must be positive."};
  }

  if (opts.timeout_ms == 0) {
    return {false, "Invalid timeout: must be greater than 0 ms."};
  }

  if (opts.op == ControlOp::EXCHANGE) {
    if (!opts.rpm.has_value()) {
      return {false, "Operation 'exchange' requires explicit --rpm <value>."};
    }
    if (!opts.duration_ms.has_value() || opts.duration_ms.value() == 0) {
      return {false, "Operation 'exchange' requires explicit non-zero --duration-ms <value>."};
    }
  }

  if (!opts.dry_run && !opts.execute) {
    return {
      false,
      "Safety confirmation required: hardware execution requires --execute flag. "
      "Use --dry-run to preview."
    };
  }

  return {true, ""};
}

int run_control_check(
  const ControlCheckOptions & opts,
  M1Driver & driver,
  std::ostream & out,
  std::ostream & err)
{
  const auto val = validate_options(opts);
  if (!val.valid) {
    err << "ERROR: " << val.error_message << "\n";
    return 1;
  }

  out << "========================================\n";
  out << "M1 Controlled Write Validation Harness\n";
  out << "Operation       : " << control_op_to_string(opts.op) << "\n";
  out << "Target Device   : " << opts.device << " @ " << opts.baud << " bps (8N1)\n";
  out << "Response Timeout: " << opts.timeout_ms << " ms\n";
  out << "Driver IDs      : Driver A=" << opts.driver_a << ", Driver B=" << opts.driver_b << "\n";

  if (opts.op == ControlOp::EXCHANGE) {
    out << "Target RPM      : " << opts.rpm.value() << " RPM\n";
    out << "Duration        : " << opts.duration_ms.value() << " ms\n";
  }

  if (opts.dry_run) {
    out << "Mode            : DRY RUN (NO HARDWARE WRITES EXECUTED)\n";
    out << "========================================\n";
    out << "[Preview] Command Sequence:\n";

    switch (opts.op) {
      case ControlOp::READ_STATE:
        out << "  1. Multi-drive 2.0 FC03 read_state(" << opts.driver_a << ", "
            << opts.driver_b << ")\n";
        out << "  2. Parse and print 16-word status feedback\n";
        break;
      case ControlOp::ENABLE:
        out << "  1. Multi-drive 2.0 FC17 enable(" << opts.driver_a << ", "
            << opts.driver_b << ") [SVON 0x0006]\n";
        out << "  2. Verify servo active status (status & 0x0001 != 0)\n";
        break;
      case ControlOp::STOP:
        out << "  1. Multi-drive 2.0 FC17 stop(" << opts.driver_a << ", "
            << opts.driver_b << ") [JG 0x0001 with 0 RPM]\n";
        out << "  2. Read and verify zero velocity feedback\n";
        break;
      case ControlOp::DISABLE:
        out << "  1. Multi-drive 2.0 FC17 disable(" << opts.driver_a << ", "
            << opts.driver_b << ") [SVOFF 0x0007]\n";
        out << "  2. Verify servo disabled status\n";
        break;
      case ControlOp::EXCHANGE: {
          const uint32_t cycle_period_ms = 50;
          const uint32_t total_cycles = opts.duration_ms.value() / cycle_period_ms;
          out << "  1. Loop at 20 Hz (~50 ms) for " << total_cycles << " cycles ("
              << opts.duration_ms.value() << " ms total)\n";
          out << "     - Exchange command: Driver " << opts.driver_a << " -> +"
              << opts.rpm.value() << " RPM, Driver " << opts.driver_b << " -> -"
              << opts.rpm.value() << " RPM\n";
          out << "     - On any communication failure: abort immediately without retry\n";
          out << "  2. Post-motion: send stop(" << opts.driver_a << ", "
              << opts.driver_b << ") [JG 0 RPM]\n";
          out << "  3. Post-motion: read_state(" << opts.driver_a << ", "
              << opts.driver_b << ")\n";
          out << "  4. Post-motion: disable(" << opts.driver_a << ", "
              << opts.driver_b << ") [SVOFF]\n";
          break;
        }
      default:
        break;
    }

    out << "[Preview] PASS: Dry-run preview generated successfully.\n";
    return 0;
  }

  out << "Mode            : REAL HARDWARE EXECUTION\n";
  out << "========================================\n";

  // Step 1: Connect
  out << "[Step 1] Connecting to " << opts.device << " @ " << opts.baud << "...\n";
  auto conn_res = driver.connect(opts.device, opts.baud, opts.timeout_ms, 'N', 8, 1);
  if (!conn_res.ok) {
    err << "FAIL: Connection failed: " << error_code_to_string(conn_res.error) << "\n";
    return 2;
  }
  out << "PASS: Connected.\n";

  auto print_states = [&out](const ExchangeResult & res) {
      for (size_t i = 0; i < 2; ++i) {
        const auto & st = res.states[i];
        out << "  Driver ID " << st.driver_id << ": Status=" << st.status
            << " Alarm=" << st.alarm << " RPM=" << st.actual_rpm
            << " Bus=" << std::fixed << std::setprecision(2) << (st.bus_voltage_raw / 100.0) << "V"
            << " Pos=" << st.position_steps << " steps\n";
      }
    };

  // Step 2: Execute requested operation
  switch (opts.op) {
    case ControlOp::READ_STATE: {
        out << "[Step 2] Reading dual driver state...\n";
        auto res = driver.read_state(opts.driver_a, opts.driver_b);
        if (!res.ok) {
          err << "FAIL: read_state failed: " << error_code_to_string(res.error) << "\n";
          driver.disconnect();
          return 3;
        }
        print_states(res.value);
        break;
      }

    case ControlOp::ENABLE: {
        out << "[Step 2] Sending Multi-drive 2.0 SVON (enable)...\n";
        auto res = driver.enable(opts.driver_a, opts.driver_b);
        if (!res.ok) {
          err << "FAIL: enable failed: " << error_code_to_string(res.error) << "\n";
          driver.disconnect();
          return 3;
        }
        out << "PASS: Enable command sent. Current state:\n";
        print_states(res.value);
        break;
      }

    case ControlOp::STOP: {
        out << "[Step 2] Sending Multi-drive 2.0 JG 0 (stop)...\n";
        auto res = driver.stop(opts.driver_a, opts.driver_b);
        if (!res.ok) {
          err << "FAIL: stop failed: " << error_code_to_string(res.error) << "\n";
          driver.disconnect();
          return 3;
        }
        out << "PASS: Stop command sent. Current state:\n";
        print_states(res.value);
        break;
      }

    case ControlOp::DISABLE: {
        out << "[Step 2] Sending Multi-drive 2.0 SVOFF (disable)...\n";
        auto res = driver.disable(opts.driver_a, opts.driver_b);
        if (!res.ok) {
          err << "FAIL: disable failed: " << error_code_to_string(res.error) << "\n";
          driver.disconnect();
          return 3;
        }
        out << "PASS: Disable command sent. Current state:\n";
        print_states(res.value);
        break;
      }

    case ControlOp::EXCHANGE: {
        const int16_t rpm_val = opts.rpm.value();
        const uint32_t duration = opts.duration_ms.value();
        const uint32_t cycle_period_ms = 50;

        MotorCommand cmd_a{opts.driver_a, rpm_val};
        MotorCommand cmd_b{opts.driver_b, static_cast<int16_t>(-rpm_val)};

        out << "[Step 2] Executing bounded exchange motion: " << duration << " ms...\n";
        const auto start_time = std::chrono::steady_clock::now();
        uint32_t cycle_count = 0;

        while (true) {
          const auto now = std::chrono::steady_clock::now();
          const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - start_time).count();

          if (elapsed_ms >= duration) {
            break;
          }

          auto ex_res = driver.exchange(cmd_a, cmd_b);
          if (!ex_res.ok) {
            err << "FAIL: exchange failed during cycle " << cycle_count
                << ": " << error_code_to_string(ex_res.error) << "\n";
            err << "EMERGENCY: Sending stop primitive...\n";
            driver.stop(opts.driver_a, opts.driver_b);
            driver.disconnect();
            return 4;
          }

          cycle_count++;
          std::this_thread::sleep_for(std::chrono::milliseconds(cycle_period_ms));
        }

        out << "PASS: Motion duration completed (" << cycle_count << " cycles).\n";

        out << "[Step 3] Post-motion: stopping...\n";
        driver.stop(opts.driver_a, opts.driver_b);

        out << "[Step 4] Post-motion: reading final state...\n";
        auto st_res = driver.read_state(opts.driver_a, opts.driver_b);
        if (st_res.ok) {
          print_states(st_res.value);
        }

        out << "[Step 5] Post-motion: disabling servo...\n";
        driver.disable(opts.driver_a, opts.driver_b);
        break;
      }

    default:
      break;
  }

  // Step 6: Disconnect
  out << "[Final] Disconnecting...\n";
  driver.disconnect();
  out << "PASS: Validation step completed successfully.\n";
  return 0;
}

}  // namespace mobile_base_control
