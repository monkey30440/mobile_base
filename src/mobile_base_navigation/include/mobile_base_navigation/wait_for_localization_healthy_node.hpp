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
#include "std_msgs/msg/bool.hpp"

namespace mobile_base_navigation
{

/**
 * @brief Behavior tree stateful action node that waits for fresh localization health
 * evidence produced strictly after the recovery attempt begins.
 *
 * Used inside a recovery sequence wrapped by a Timeout decorator.
 * On start, establishes a recovery epoch and ignores any evidence received prior to start.
 * Returns RUNNING while waiting for new post-start evidence or while new evidence is lost=true.
 * Returns SUCCESS only when new post-start evidence reports lost=false and is fresh.
 */
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
  bool last_lost_{true};
  uint64_t msg_count_{0};
  uint64_t start_msg_count_{0};
  bool initialized_{false};
};

}  // namespace mobile_base_navigation

#endif  // MOBILE_BASE_NAVIGATION__WAIT_FOR_LOCALIZATION_HEALTHY_NODE_HPP_
