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

#ifndef MOBILE_BASE_NAVIGATION__WAIT_FOR_LOCALIZATION_HEALTHY_NODE_HPP_
#define MOBILE_BASE_NAVIGATION__WAIT_FOR_LOCALIZATION_HEALTHY_NODE_HPP_

#include <memory>
#include <mutex>
#include <string>

#include "behaviortree_cpp/action_node.h"
#include "rclcpp/rclcpp.hpp"
#include "mobile_base_localization/msg/localization_state.hpp"

namespace mobile_base_navigation
{

/** Waits for HEALTHY with a measurement timestamp after this recovery wait began. */
class WaitForLocalizationHealthyNode : public BT::StatefulActionNode
{
public:
  WaitForLocalizationHealthyNode(
    const std::string & action_name,
    const BT::NodeConfig & conf);

  WaitForLocalizationHealthyNode() = delete;
  ~WaitForLocalizationHealthyNode() override;

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<std::string>(
        "topic",
        std::string("/localization/state"),
        "Topic for authoritative localization state"),
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

  std::mutex mutex_;
  rclcpp::Time last_msg_time_{0, 0, RCL_ROS_TIME};
  uint8_t state_{mobile_base_localization::msg::LocalizationState::UNKNOWN};
  uint64_t msg_count_{0};
  uint64_t start_msg_count_{0};
  rclcpp::Time recovery_start_{0, 0, RCL_ROS_TIME};
  bool initialized_{false};
};

}  // namespace mobile_base_navigation

#endif  // MOBILE_BASE_NAVIGATION__WAIT_FOR_LOCALIZATION_HEALTHY_NODE_HPP_
