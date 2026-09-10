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

#include "mobile_base_control/m1_unicast_read_check.hpp"

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace mobile_base_control
{

UnicastReadOptions parse_unicast_read_args(int argc, char ** argv)
{
  UnicastReadOptions opts;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--device" && i + 1 < argc) {
      opts.device = argv[++i];
    } else if (arg == "--baud" && i + 1 < argc) {
      opts.baud = std::stoi(argv[++i]);
    } else if (arg == "--timeout-ms" && i + 1 < argc) {
      opts.timeout_ms = static_cast<uint32_t>(std::stoul(argv[++i]));
    } else if (arg == "--driver-id" && i + 1 < argc) {
      opts.driver_id = std::stoi(argv[++i]);
      opts.driver_id_specified = true;
    } else if (arg == "--register" && i + 1 < argc) {
      opts.reg = static_cast<uint16_t>(std::stoul(argv[++i], nullptr, 0));
      opts.register_specified = true;
    } else if (arg == "--read" && i + 1 < argc) {
      const std::string read = argv[++i];
      try {
        const auto colon = read.find(':');
        if (colon == std::string::npos || colon == 0 || colon + 1 == read.size() ||
          read.find(':', colon + 1) != std::string::npos)
        {
          throw std::invalid_argument("expected ID:REGISTER");
        }
        const auto id_text = read.substr(0, colon);
        const auto reg_text = read.substr(colon + 1);
        size_t id_end = 0;
        size_t reg_end = 0;
        const auto id = std::stoi(id_text, &id_end);
        const auto reg = std::stoul(reg_text, &reg_end, 0);
        if (id_end != id_text.size() || reg_end != reg_text.size() ||
          id < 1 || id > 247 || reg_text.front() == '-' || reg > 0xFFFF)
        {
          throw std::invalid_argument("ID must be 1-247 and register must be 0-65535");
        }
        opts.reads.push_back({id, static_cast<uint16_t>(reg)});
      } catch (const std::exception &) {
        opts.parse_error = "--read requires ID:REGISTER (ID 1-247, register 0-65535): " + read;
        return opts;
      }
    } else if (arg == "--help" || arg == "-h") {
      opts.help = true;
    } else {
      opts.parse_error = "Unknown option or missing value: " + arg;
      return opts;
    }
  }
  return opts;
}

UnicastReadValidationResult validate_unicast_read_options(const UnicastReadOptions & opts)
{
  if (!opts.parse_error.empty()) {
    return {false, opts.parse_error};
  }
  if (opts.device.empty()) {
    return {false, "--device must not be empty"};
  }
  if (opts.baud <= 0) {
    return {false, "--baud must be positive"};
  }
  if (opts.timeout_ms == 0) {
    return {false, "--timeout-ms must be positive"};
  }
  if (opts.driver_id < 1 || opts.driver_id > 247) {
    return {false, "--driver-id must be between 1 and 247"};
  }
  if (!opts.reads.empty() && (opts.driver_id_specified || opts.register_specified)) {
    return {false, "Use --read entries OR --driver-id/--register; do not mix them"};
  }
  for (const auto & read : opts.reads) {
    if (read.driver_id < 1 || read.driver_id > 247) {
      return {false, "--read slave ID must be between 1 and 247"};
    }
  }
  if (opts.reads.empty() && !opts.register_specified) {
    return {false, "Specify --read ID:REGISTER or --register (e.g. 0x3D05)"};
  }
  return {true, ""};
}

int run_unicast_read_check(
  const UnicastReadOptions & opts,
  M1Driver & driver,
  std::ostream & out,
  std::ostream & err)
{
  if (opts.help) {
    out << "Usage: m1_unicast_read_check [options]\n"
        << "Options:\n"
        << "  --device <path>      Serial device path (default: /dev/ttyUSB0)\n"
        << "  --baud <rate>        Baud rate (default: 230400)\n"
        << "  --timeout-ms <ms>    Response timeout in milliseconds (default: 50)\n"
        << "  --read <id:addr>     Ordered FC03 single-register read; repeat for a sequence\n"
        << "  --driver-id <id>     Modbus slave ID (1-247)\n"
        << "  --register <addr>    Register address in hex (e.g. 0x3D05) or decimal\n"
        << "  --help, -h           Show this help message\n"
        << "Use --read entries OR the legacy --driver-id/--register form.\n"
        << "Read-only: one connection, supplied order, stop on first failure, no retry/delay.\n"
        << "Results are printed after disconnect; remaining reads are NOT EXECUTED.\n";
    return 0;
  }

  const auto validation = validate_unicast_read_options(opts);
  if (!validation.valid) {
    err << "INVALID_ARGUMENT: " << validation.error_message << "\n";
    return 1;
  }

  const bool sequence = !opts.reads.empty();
  const auto reads = sequence ? opts.reads :
    std::vector<UnicastRegisterRead>{{opts.driver_id, opts.reg}};
  // Allocate result storage before connecting. No output or allocation of result
  // storage between reads: preserve the existing production transport semantics.
  std::vector<Result<uint16_t>> results(reads.size());

  auto conn_res = driver.connect(opts.device, opts.baud, opts.timeout_ms, 'N', 8, 1);
  if (!conn_res.ok) {
    err << "ERROR: Failed to connect to " << opts.device << ": "
        << error_code_to_string(conn_res.error) << "\n";
    return 2;
  }

  size_t executed = 0;
  bool failed = false;
  for (size_t i = 0; i < reads.size(); ++i) {
    results[i] = driver.read_register(reads[i].driver_id, reads[i].reg);
    ++executed;
    if (!results[i].ok) {
      failed = true;
      break;
    }
  }
  driver.disconnect();

  if (sequence) {
    for (size_t i = 0; i < reads.size(); ++i) {
      out << "READ " << i + 1 << ": ID " << reads[i].driver_id << " register 0x"
          << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << reads[i].reg
          << std::dec;
      if (i >= executed) {
        out << " NOT EXECUTED\n";
      } else if (results[i].ok) {
        out << " SUCCESS = " << results[i].value << "\n";
      } else {
        out << " " << error_code_to_string(results[i].error) << "\n";
      }
    }
    return failed ? 3 : 0;
  }

  // Preserve legacy single-read output and exit codes.
  const auto & read_res = results.front();
  if (!read_res.ok) {
    err << "ERROR: ID " << opts.driver_id << " register 0x"
        << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << opts.reg
        << std::dec << ": " << error_code_to_string(read_res.error) << "\n";
    return 3;
  }

  out << "SUCCESS: ID " << opts.driver_id << " register 0x"
      << std::hex << std::uppercase << std::setw(4) << std::setfill('0') << opts.reg
      << std::dec << " = " << read_res.value
      << " (0x" << std::hex << std::uppercase << std::setw(4) << std::setfill('0')
      << read_res.value << std::dec << ")\n";
  return 0;
}

}  // namespace mobile_base_control
