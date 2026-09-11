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

#include "mobile_base_navigation/wait_for_localization_healthy_node.hpp"

#include <chrono>
#include <string>

#include "behaviortree_cpp/bt_factory.h"

namespace mobile_base_navigation
{

WaitForLocalizationHealthyNode::WaitForLocalizationHealthyNode(
  const std::string & action_name,
  const BT::NodeConfig & conf)
: BT::StatefulActionNode(action_name, conf)
{
  rclcpp::Node::SharedPtr node;
  if (config().blackboard && config().blackboard->get<rclcpp::Node::SharedPtr>("node", node)) {
    initialize();
  }
}

WaitForLocalizationHealthyNode::~WaitForLocalizationHealthyNode()
{
  if (initialized_ && callback_group_) {
    callback_group_executor_.remove_callback_group(callback_group_);
  }
}

void WaitForLocalizationHealthyNode::initialize()
{
  if (initialized_) {
    return;
  }

  if (!config().blackboard ||
    !config().blackboard->get<rclcpp::Node::SharedPtr>("node", node_) ||
    !node_)
  {
    throw BT::RuntimeError("WaitForLocalizationHealthyNode: 'node' not found in blackboard");
  }

  if (!getInput("topic", topic_)) {
    topic_ = "/localization/lost";
  }
  getInput("freshness_timeout_s", freshness_timeout_s_);

  last_msg_time_ = rclcpp::Time(0, 0, node_->get_clock()->get_clock_type());

  callback_group_ = node_->create_callback_group(
    rclcpp::CallbackGroupType::MutuallyExclusive, false);
  callback_group_executor_.add_callback_group(
    callback_group_, node_->get_node_base_interface());

  rclcpp::SubscriptionOptions sub_options;
  sub_options.callback_group = callback_group_;

  sub_ = node_->create_subscription<std_msgs::msg::Bool>(
    topic_,
    rclcpp::QoS(10),
    std::bind(&WaitForLocalizationHealthyNode::onMessage, this, std::placeholders::_1),
    sub_options);
  callback_group_executor_.spin_some();

  initialized_ = true;
}

void WaitForLocalizationHealthyNode::onMessage(const std_msgs::msg::Bool::SharedPtr msg)
{
  std::lock_guard<std::mutex> lock(mutex_);
  last_msg_time_ = node_->now();
  last_lost_ = msg->data;
  msg_count_++;
}

BT::NodeStatus WaitForLocalizationHealthyNode::onStart()
{
  if (!initialized_) {
    initialize();
  }

  // Drain any messages that arrived before this recovery epoch began
  callback_group_executor_.spin_some();

  getInput("freshness_timeout_s", freshness_timeout_s_);

  {
    std::lock_guard<std::mutex> lock(mutex_);
    start_msg_count_ = msg_count_;
  }

  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus WaitForLocalizationHealthyNode::onRunning()
{
  callback_group_executor_.spin_some();

  getInput("freshness_timeout_s", freshness_timeout_s_);

  std::lock_guard<std::mutex> lock(mutex_);

  // Evidence that predates the current recovery attempt MUST NOT satisfy recovery
  if (msg_count_ <= start_msg_count_) {
    return BT::NodeStatus::RUNNING;
  }

  const rclcpp::Time now = node_->now();
  if (now < last_msg_time_ || (now - last_msg_time_).seconds() > freshness_timeout_s_) {
    return BT::NodeStatus::RUNNING;
  }

  if (last_lost_) {
    return BT::NodeStatus::RUNNING;
  }

  return BT::NodeStatus::SUCCESS;
}

void WaitForLocalizationHealthyNode::onHalted()
{
  std::lock_guard<std::mutex> lock(mutex_);
  start_msg_count_ = msg_count_;
}

}  // namespace mobile_base_navigation

BT_REGISTER_NODES(factory)
{
  factory.registerNodeType<mobile_base_navigation::WaitForLocalizationHealthyNode>(
    "WaitForLocalizationHealthy");
}
