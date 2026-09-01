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

#include "mobile_base_navigation/apriltag_dock_trigger_node.hpp"

#include <chrono>
#include <memory>
#include <string>
#include <utility>

namespace mobile_base_navigation
{

ApriltagDockTriggerNode::ApriltagDockTriggerNode(const rclcpp::NodeOptions & options)
: Node("apriltag_dock_trigger", options),
  is_active_(false)
{
  service_callback_group_ = create_callback_group(
    rclcpp::CallbackGroupType::MutuallyExclusive);
  action_callback_group_ = create_callback_group(
    rclcpp::CallbackGroupType::MutuallyExclusive);
  subscription_callback_group_ = create_callback_group(
    rclcpp::CallbackGroupType::MutuallyExclusive);

  rclcpp::SubscriptionOptions sub_options;
  sub_options.callback_group = subscription_callback_group_;

  pose_sub_ = create_subscription<geometry_msgs::msg::PoseStamped>(
    "/detected_dock_pose",
    rclcpp::QoS(10),
    [this](const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
      std::lock_guard<std::mutex> lock(pose_mutex_);
      cached_pose_ = *msg;
    },
    sub_options);

  action_client_ = rclcpp_action::create_client<DockRobot>(
    this,
    "/dock_robot",
    action_callback_group_);

  trigger_service_ = create_service<std_srvs::srv::Trigger>(
    "/apriltag_dock",
    [this](
      const std::shared_ptr<std_srvs::srv::Trigger::Request> request,
      std::shared_ptr<std_srvs::srv::Trigger::Response> response)
    {
      handle_trigger(request, response);
    },
    rclcpp::ServicesQoS(),
    service_callback_group_);
}

void ApriltagDockTriggerNode::handle_trigger(
  const std::shared_ptr<std_srvs::srv::Trigger::Request>,
  std::shared_ptr<std_srvs::srv::Trigger::Response> response)
{
  bool expected = false;
  if (!is_active_.compare_exchange_strong(expected, true)) {
    response->success = false;
    response->message = "Docking already in progress";
    return;
  }

  struct ScopeGuard
  {
    std::atomic<bool> & active;
    ~ScopeGuard()
    {
      active.store(false);
    }
  } guard{is_active_};

  geometry_msgs::msg::PoseStamped target_pose;
  {
    std::lock_guard<std::mutex> lock(pose_mutex_);
    if (!cached_pose_.has_value()) {
      response->success = false;
      response->message = "No detected dock pose received yet";
      return;
    }
    target_pose = *cached_pose_;
  }

  if (!action_client_->wait_for_action_server(std::chrono::seconds(2))) {
    response->success = false;
    response->message = "DockRobot action server unavailable";
    return;
  }

  DockRobot::Goal goal;
  goal.use_dock_id = false;
  goal.dock_id = "";
  goal.dock_pose = target_pose;
  goal.dock_type = "apriltag_dock";
  goal.navigate_to_staging_pose = false;

  auto goal_handle_future = action_client_->async_send_goal(goal);
  if (goal_handle_future.wait_for(std::chrono::seconds(5)) != std::future_status::ready) {
    response->success = false;
    response->message = "Timeout waiting for DockRobot goal response";
    return;
  }

  auto goal_handle = goal_handle_future.get();
  if (!goal_handle) {
    response->success = false;
    response->message = "DockRobot goal rejected by server";
    return;
  }

  auto result_future = action_client_->async_get_result(goal_handle);
  result_future.wait();
  auto wrapped_result = result_future.get();

  switch (wrapped_result.code) {
    case rclcpp_action::ResultCode::SUCCEEDED:
      if (wrapped_result.result && wrapped_result.result->success) {
        response->success = true;
        response->message = "Docking succeeded";
      } else {
        response->success = false;
        if (wrapped_result.result) {
          response->message = "Docking failed: " + wrapped_result.result->error_msg +
            " (code " + std::to_string(wrapped_result.result->error_code) + ")";
        } else {
          response->message = "Docking failed with empty result";
        }
      }
      break;

    case rclcpp_action::ResultCode::ABORTED:
      response->success = false;
      if (wrapped_result.result) {
        response->message = "Docking aborted: " + wrapped_result.result->error_msg +
          " (code " + std::to_string(wrapped_result.result->error_code) + ")";
      } else {
        response->message = "Docking aborted";
      }
      break;

    case rclcpp_action::ResultCode::CANCELED:
      response->success = false;
      response->message = "Docking canceled";
      break;

    default:
      response->success = false;
      response->message = "Unknown action result code";
      break;
  }
}

}  // namespace mobile_base_navigation
