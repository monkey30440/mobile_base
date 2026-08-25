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

#ifndef NAVIGATE_TO_STATION_APP_HPP_
#define NAVIGATE_TO_STATION_APP_HPP_

#include <chrono>
#include <functional>
#include <ostream>
#include <string>
#include <vector>

namespace mobile_base_navigation
{

struct CliOptions
{
  std::string station_id;
  std::string catalog_path;
  bool help{false};
};

struct CliParseResult
{
  bool valid{false};
  CliOptions options;
  std::string error;
};

struct ApplicationConfig
{
  std::chrono::milliseconds server_wait_timeout{std::chrono::seconds(10)};
  std::chrono::milliseconds cancellation_timeout{std::chrono::seconds(5)};
  std::chrono::milliseconds feedback_period{std::chrono::seconds(1)};
};

using CancellationCheck = std::function<bool()>;

CliParseResult parse_cli_arguments(const std::vector<std::string> & arguments);
std::string usage_text();

int run_navigate_to_station(
  const CliOptions & options,
  const CancellationCheck & cancellation_requested,
  std::ostream & output,
  std::ostream & error,
  const ApplicationConfig & config = ApplicationConfig{});

}  // namespace mobile_base_navigation

#endif  // NAVIGATE_TO_STATION_APP_HPP_
