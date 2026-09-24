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

#include <chrono>
#include <memory>
#include <mutex>
#include <string>

#include "behaviortree_cpp/condition_node.h"
#include "rclcpp/rclcpp.hpp"
#include "mobile_base_localization/msg/localization_state.hpp"

namespace mobile_base_navigation
{

/** Accepts the Localization subsystem state; latches LOST as the failure cause. */
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
        std::string("/localization/state"),
        "Topic for authoritative localization state"),
      BT::InputPort<double>(
        "state_publisher_timeout_s", 1.0,
        "Maximum silence of localization state publisher, not measurement freshness"),
      BT::OutputPort<bool>("recovery_required", "True only for explicit LOST"),
    };
  }

private:
  void initialize();
  void onMessage(
    const mobile_base_localization::msg::LocalizationState::SharedPtr msg);

  rclcpp::Node::SharedPtr node_;
  rclcpp::CallbackGroup::SharedPtr callback_group_;
  rclcpp::executors::SingleThreadedExecutor callback_group_executor_;
  rclcpp::Subscription<mobile_base_localization::msg::LocalizationState>::SharedPtr sub_;

  std::string topic_;
  double state_publisher_timeout_s_{1.0};
  std::chrono::steady_clock::time_point last_state_received_;

  std::mutex mutex_;
  uint8_t state_{mobile_base_localization::msg::LocalizationState::UNKNOWN};
  bool has_msg_{false};
  bool initialized_{false};
};

}  // namespace mobile_base_navigation

#endif  // MOBILE_BASE_NAVIGATION__IS_LOCALIZATION_HEALTHY_CONDITION_HPP_
