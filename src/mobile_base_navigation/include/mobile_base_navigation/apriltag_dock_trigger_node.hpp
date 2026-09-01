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

#ifndef MOBILE_BASE_NAVIGATION__APRILTAG_DOCK_TRIGGER_NODE_HPP_
#define MOBILE_BASE_NAVIGATION__APRILTAG_DOCK_TRIGGER_NODE_HPP_

#include <atomic>
#include <memory>
#include <mutex>
#include <optional>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav2_msgs/action/dock_robot.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "std_srvs/srv/trigger.hpp"

namespace mobile_base_navigation
{

class ApriltagDockTriggerNode : public rclcpp::Node
{
public:
  using DockRobot = nav2_msgs::action::DockRobot;
  using GoalHandleDockRobot = rclcpp_action::ClientGoalHandle<DockRobot>;

  explicit ApriltagDockTriggerNode(
    const rclcpp::NodeOptions & options = rclcpp::NodeOptions());
  virtual ~ApriltagDockTriggerNode() = default;

private:
  void handle_trigger(
    const std::shared_ptr<std_srvs::srv::Trigger::Request> request,
    std::shared_ptr<std_srvs::srv::Trigger::Response> response);

  rclcpp::CallbackGroup::SharedPtr service_callback_group_;
  rclcpp::CallbackGroup::SharedPtr action_callback_group_;
  rclcpp::CallbackGroup::SharedPtr subscription_callback_group_;

  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;
  rclcpp_action::Client<DockRobot>::SharedPtr action_client_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr trigger_service_;

  std::mutex pose_mutex_;
  std::optional<geometry_msgs::msg::PoseStamped> cached_pose_;
  std::atomic<bool> is_active_{false};
};

}  // namespace mobile_base_navigation

#endif  // MOBILE_BASE_NAVIGATION__APRILTAG_DOCK_TRIGGER_NODE_HPP_
