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
#include <stdexcept>

#include "mobile_base_control/m1_dynamic_stage_d2_check.hpp"

int main(int argc, char ** argv)
{
  try {
    mobile_base_control::DynamicStageD2Options options =
      mobile_base_control::parse_stage_d2_command_line(argc, argv);
    return mobile_base_control::run_dynamic_stage_d2_check(
      options, nullptr, std::cout, std::cerr);
  } catch (const std::exception & e) {
    std::cerr << "Fatal Error: " << e.what() << "\n";
    return 1;
  }
}
