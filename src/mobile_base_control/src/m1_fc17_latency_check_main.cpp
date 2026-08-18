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

#include <iostream>

#include "mobile_base_control/m1_driver.hpp"
#include "mobile_base_control/m1_fc17_latency_check.hpp"

using mobile_base_control::M1Driver;
using mobile_base_control::parse_fc17_latency_command_line;
using mobile_base_control::run_fc17_latency_check;

int main(int argc, char ** argv)
{
  try {
    const auto opts = parse_fc17_latency_command_line(argc, argv);
    M1Driver driver;
    return run_fc17_latency_check(opts, driver, std::cout, std::cerr);
  } catch (const std::exception & ex) {
    std::cerr << "Error: " << ex.what() << std::endl;
    return 1;
  }
}
