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

#ifndef MOBILE_BASE_CONTROL__M1_CONTROL_CHECK_HPP_
#define MOBILE_BASE_CONTROL__M1_CONTROL_CHECK_HPP_

#include <cstdint>
#include <iosfwd>
#include <optional>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"

namespace mobile_base_control
{

enum class ControlOp
{
  NONE,
  READ_STATE,
  ENABLE,
  STOP,
  DISABLE,
  EXCHANGE
};

struct ControlCheckOptions
{
  ControlOp op{ControlOp::NONE};
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  uint32_t timeout_ms{100};
  int driver_a{1};
  int driver_b{2};
  std::optional<int16_t> rpm{std::nullopt};
  std::optional<uint32_t> duration_ms{std::nullopt};
  bool dry_run{false};
  bool execute{false};
};

struct ValidationResult
{
  bool valid{false};
  std::string error_message;
};

/// \brief Parse command-line arguments into ControlCheckOptions
ControlCheckOptions parse_command_line(int argc, char ** argv);

/// \brief Validate options consistency and safety requirements
ValidationResult validate_options(const ControlCheckOptions & opts);

/// \brief Execute or preview the requested controlled operation
int run_control_check(
  const ControlCheckOptions & opts,
  M1Driver & driver,
  std::ostream & out,
  std::ostream & err);

const char * control_op_to_string(ControlOp op) noexcept;

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_CONTROL_CHECK_HPP_
