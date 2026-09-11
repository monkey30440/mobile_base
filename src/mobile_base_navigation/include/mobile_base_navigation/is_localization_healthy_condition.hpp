// Copyright (c) 2026 mobile_base Developer
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

#ifndef MOBILE_BASE_NAVIGATION__IS_LOCALIZATION_HEALTHY_CONDITION_HPP_
#define MOBILE_BASE_NAVIGATION__IS_LOCALIZATION_HEALTHY_CONDITION_HPP_

#include <memory>
#include <mutex>
#include <string>

#include "behaviortree_cpp/condition_node.h"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/bool.hpp"

namespace mobile_base_navigation
{

/**
 * @brief Behavior tree condition node that evaluates localization health
 * based on the /localization/lost topic and message freshness.
 *
 * Returns SUCCESS only when a message has been received within freshness_timeout_s
 * and lost is false. Returns FAILURE otherwise. Never returns RUNNING.
 */
class IsLocalizationHealthyCondition : public BT::ConditionNode
{
public:
  IsLocalizationHealthyCondition(
    const std::string & condition_name,
    const BT::NodeConfig & conf);

  IsLocalizationHealthyCondition() = delete;
  ~IsLocalizationHealthyCondition() override;

  BT::NodeStatus tick() override;

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<std::string>(
        "topic",
        std::string("/localization/lost"),
        "Topic for localization lost status"),
      BT::InputPort<double>(
        "freshness_timeout_s",
        1.0,
        "Maximum age in seconds for localization health evidence to be considered fresh"),
    };
  }

private:
  void initialize();
  void onMessage(const std_msgs::msg::Bool::SharedPtr msg);

  rclcpp::Node::SharedPtr node_;
  rclcpp::CallbackGroup::SharedPtr callback_group_;
  rclcpp::executors::SingleThreadedExecutor callback_group_executor_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr sub_;

  std::string topic_;
  double freshness_timeout_s_{1.0};

  std::mutex mutex_;
  rclcpp::Time last_msg_time_{0, 0, RCL_ROS_TIME};
  bool last_lost_{false};
  bool has_msg_{false};
  bool initialized_{false};
};

}  // namespace mobile_base_navigation

#endif  // MOBILE_BASE_NAVIGATION__IS_LOCALIZATION_HEALTHY_CONDITION_HPP_
