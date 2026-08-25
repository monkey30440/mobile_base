// Copyright 2026 mobile_base developer
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

#include "navigate_to_station_app.hpp"

#include <csignal>
#include <iostream>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"

namespace
{

volatile std::sig_atomic_t g_cancellation_requested = 0;

void handle_sigint(int signal_number)
{
  if (signal_number == SIGINT) {
    g_cancellation_requested = 1;
  }
}

}  // namespace

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv, rclcpp::InitOptions(), rclcpp::SignalHandlerOptions::None);
  std::signal(SIGINT, handle_sigint);

  int exit_code = 5;
  try {
    const auto non_ros_arguments = rclcpp::remove_ros_arguments(argc, argv);
    const auto parsed = mobile_base_navigation::parse_cli_arguments(non_ros_arguments);
    if (!parsed.valid) {
      std::cerr << "INVALID_CLI message=\"" << parsed.error << "\"\n" <<
        mobile_base_navigation::usage_text();
      exit_code = 2;
    } else if (parsed.options.help) {
      std::cout << mobile_base_navigation::usage_text();
      exit_code = 0;
    } else {
      exit_code = mobile_base_navigation::run_navigate_to_station(
        parsed.options, []() {return g_cancellation_requested != 0;}, std::cout, std::cerr);
    }
  } catch (const std::exception & exception) {
    std::cerr << "NAV_CLIENT_FAILURE message=\"" << exception.what() << "\"\n";
    exit_code = 5;
  }
  rclcpp::shutdown();
  return exit_code;
}
