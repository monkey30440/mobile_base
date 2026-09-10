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

#ifndef MOBILE_BASE_CONTROL__M1_UNICAST_READ_CHECK_HPP_
#define MOBILE_BASE_CONTROL__M1_UNICAST_READ_CHECK_HPP_

#include <cstdint>
#include <iosfwd>
#include <string>
#include <vector>

#include "mobile_base_control/m1_driver.hpp"

namespace mobile_base_control
{

struct UnicastRegisterRead
{
  int driver_id;
  uint16_t reg;
};

struct UnicastReadOptions
{
  std::string device{"/dev/ttyUSB0"};
  int baud{230400};
  uint32_t timeout_ms{50};
  int driver_id{1};
  uint16_t reg{0};
  bool register_specified{false};
  bool help{false};
  std::vector<UnicastRegisterRead> reads;
  bool driver_id_specified{false};
  std::string parse_error;
};

struct UnicastReadValidationResult
{
  bool valid{false};
  std::string error_message;
};

UnicastReadOptions parse_unicast_read_args(int argc, char ** argv);

UnicastReadValidationResult validate_unicast_read_options(const UnicastReadOptions & opts);

int run_unicast_read_check(
  const UnicastReadOptions & opts,
  M1Driver & driver,
  std::ostream & out,
  std::ostream & err);

}  // namespace mobile_base_control

#endif  // MOBILE_BASE_CONTROL__M1_UNICAST_READ_CHECK_HPP_
