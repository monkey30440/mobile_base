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

#include <algorithm>
#include <chrono>
#include <exception>
#include <iomanip>
#include <memory>
#include <optional>
#include <string>
#include <thread>
#include <utility>

#include "mobile_base_navigation/target_admission.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

namespace mobile_base_navigation
{
namespace
{

using NavigateToPose = nav2_msgs::action::NavigateToPose;
using GoalHandle = rclcpp_action::ClientGoalHandle<NavigateToPose>;
using SteadyClock = std::chrono::steady_clock;

constexpr int kExitSuccess = 0;
constexpr int kExitResolutionFailure = 3;
constexpr int kExitNav2Unavailable = 4;
constexpr int kExitNavigationFailure = 5;
constexpr int kExitCanceled = 130;

void print_native_result(
  std::ostream & stream, const std::string & event,
  const NavigateToPose::Result::SharedPtr & result)
{
  stream << event;
  if (result) {
    stream << " error_code=" << result->error_code << " error_msg=\"" << result->error_msg << '"';
  }
  stream << '\n';
}

bool cancellation_expired(
  const std::optional<SteadyClock::time_point> & requested_at,
  std::chrono::milliseconds timeout)
{
  return requested_at && SteadyClock::now() - *requested_at >= timeout;
}

}  // namespace

CliParseResult parse_cli_arguments(const std::vector<std::string> & arguments)
{
  CliParseResult result;
  bool station_seen = false;
  bool catalog_seen = false;

  for (size_t index = 1; index < arguments.size(); ++index) {
    const auto & argument = arguments[index];
    if (argument == "--help") {
      if (arguments.size() != 2) {
        result.error = "--help cannot be combined with other application arguments";
        return result;
      }
      result.valid = true;
      result.options.help = true;
      return result;
    }

    const bool is_station = argument == "--station";
    const bool is_catalog = argument == "--catalog";
    if (!is_station && !is_catalog) {
      result.error = "Unknown option or positional argument: " + argument;
      return result;
    }
    if (index + 1 >= arguments.size() || arguments[index + 1].empty()) {
      result.error = "Missing or empty value for " + argument;
      return result;
    }
    if ((is_station && station_seen) || (is_catalog && catalog_seen)) {
      result.error = "Repeated option: " + argument;
      return result;
    }
    if (is_station) {
      station_seen = true;
      result.options.station_id = arguments[++index];
    } else {
      catalog_seen = true;
      result.options.catalog_path = arguments[++index];
    }
  }

  if (!station_seen || !catalog_seen) {
    result.error = "Both --station and --catalog are required";
    return result;
  }
  result.valid = true;
  return result;
}

std::string usage_text()
{
  return "Usage: ros2 run mobile_base_navigation navigate_to_station "
         "--station <station_id> --catalog <stations.yaml>\n";
}

int run_navigate_to_station(
  const CliOptions & options,
  const CancellationCheck & cancellation_requested,
  std::ostream & output,
  std::ostream & error,
  const ApplicationConfig & config)
{
  try {
    TargetAdmission admission;
    std::string catalog_error;
    if (!admission.load_station_catalog(options.catalog_path, &catalog_error)) {
      error << "RESOLUTION_FAILED station=" << options.station_id <<
        " status=REJECTED_CATALOG_MALFORMED message=\"" << catalog_error << "\"\n";
      return kExitResolutionFailure;
    }
    const auto resolution = admission.resolve_station(options.station_id);
    if (!resolution.admitted || !resolution.canonical_pose) {
      error << "RESOLUTION_FAILED station=" << options.station_id << " status=" <<
        to_string(resolution.status) << " message=\"" << resolution.message << "\"\n";
      return kExitResolutionFailure;
    }
    if (cancellation_requested()) {
      error << "CANCELLATION_UNCONFIRMED phase=pre_navigation\n";
      return kExitCanceled;
    }

    auto node = std::make_shared<rclcpp::Node>("navigate_to_station");
    auto client = rclcpp_action::create_client<NavigateToPose>(node, "navigate_to_pose");
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(node);

    const auto server_deadline = SteadyClock::now() + config.server_wait_timeout;
    while (SteadyClock::now() < server_deadline) {
      if (cancellation_requested()) {
        error << "CANCELLATION_UNCONFIRMED phase=server_wait\n";
        return kExitCanceled;
      }
      const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
        server_deadline - SteadyClock::now());
      if (client->wait_for_action_server(std::min(remaining, std::chrono::milliseconds(50)))) {
        break;
      }
    }
    if (!client->action_server_is_ready()) {
      error << "NAV2_UNAVAILABLE action=navigate_to_pose\n";
      return kExitNav2Unavailable;
    }
    if (cancellation_requested()) {
      error << "CANCELLATION_UNCONFIRMED phase=pre_submission\n";
      return kExitCanceled;
    }

    NavigateToPose::Goal goal;
    goal.pose = *resolution.canonical_pose;
    goal.pose.header.stamp = node->now();
    goal.behavior_tree.clear();

    auto last_feedback = SteadyClock::time_point::min();
    rclcpp_action::Client<NavigateToPose>::SendGoalOptions send_options;
    send_options.feedback_callback =
      [&output, &last_feedback, &config](
      GoalHandle::SharedPtr, const std::shared_ptr<const NavigateToPose::Feedback> feedback) {
        const auto now = SteadyClock::now();
        if (last_feedback != SteadyClock::time_point::min() &&
          now - last_feedback < config.feedback_period)
        {
          return;
        }
        last_feedback = now;
        output << std::setprecision(8) << "NAV_FEEDBACK distance_remaining=" <<
          feedback->distance_remaining << " navigation_time_sec=" <<
          rclcpp::Duration(feedback->navigation_time).seconds() <<
          " estimated_time_remaining_sec=" <<
          rclcpp::Duration(feedback->estimated_time_remaining).seconds() <<
          " number_of_recoveries=" << feedback->number_of_recoveries <<
          " current_x=" << feedback->current_pose.pose.position.x <<
          " current_y=" << feedback->current_pose.pose.position.y << '\n';
      };

    auto goal_future = client->async_send_goal(goal, send_options);
    std::optional<SteadyClock::time_point> cancellation_started;
    while (goal_future.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready) {
      executor.spin_some();
      if (cancellation_requested() && !cancellation_started) {
        cancellation_started = SteadyClock::now();
      }
      if (cancellation_expired(cancellation_started, config.cancellation_timeout)) {
        error << "CANCELLATION_UNCONFIRMED phase=goal_acceptance\n";
        return kExitCanceled;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    const auto goal_handle = goal_future.get();
    if (!goal_handle) {
      if (cancellation_started) {
        error << "CANCELLATION_UNCONFIRMED phase=goal_rejected_after_interrupt\n";
        return kExitCanceled;
      }
      error << "GOAL_REJECTED action=navigate_to_pose\n";
      return kExitNav2Unavailable;
    }
    output << "GOAL_ACCEPTED station=" << options.station_id << " action=navigate_to_pose\n";

    bool cancel_sent = false;
    auto result_future = client->async_get_result(goal_handle);
    while (result_future.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready) {
      executor.spin_some();
      if (cancellation_requested() && !cancellation_started) {
        cancellation_started = SteadyClock::now();
      }
      if (cancellation_started && !cancel_sent) {
        client->async_cancel_goal(goal_handle);
        cancel_sent = true;
      }
      if (cancellation_expired(cancellation_started, config.cancellation_timeout)) {
        error << "CANCELLATION_UNCONFIRMED phase=active_goal\n";
        return kExitCanceled;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    const auto wrapped_result = result_future.get();
    switch (wrapped_result.code) {
      case rclcpp_action::ResultCode::SUCCEEDED:
        print_native_result(output, "NAV_SUCCEEDED", wrapped_result.result);
        return kExitSuccess;
      case rclcpp_action::ResultCode::CANCELED:
        print_native_result(output, "NAV_CANCELED", wrapped_result.result);
        return kExitCanceled;
      case rclcpp_action::ResultCode::ABORTED:
        print_native_result(error, "NAV_ABORTED", wrapped_result.result);
        return kExitNavigationFailure;
      default:
        print_native_result(error, "NAV_UNKNOWN_RESULT", wrapped_result.result);
        return kExitNavigationFailure;
    }
  } catch (const std::exception & exception) {
    error << "NAV_CLIENT_FAILURE message=\"" << exception.what() << "\"\n";
    return kExitNavigationFailure;
  }
}

}  // namespace mobile_base_navigation
