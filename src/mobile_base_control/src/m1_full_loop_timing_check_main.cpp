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
#include <memory>
#include <stdexcept>

#include "mobile_base_control/m1_full_loop_timing_check.hpp"

int main(int argc, char ** argv)
{
  try {
    auto opts = mobile_base_control::parse_full_loop_command_line(argc, argv);
    return mobile_base_control::run_full_loop_timing_check(opts, nullptr, std::cout, std::cerr);
  } catch (const std::exception & e) {
    std::cerr << "ERROR: " << e.what() << std::endl;
    return 1;
  }
}
