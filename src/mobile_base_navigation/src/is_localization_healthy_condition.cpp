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

#include "mobile_base_navigation/is_localization_healthy_condition.hpp"

#include <chrono>
#include "behaviortree_cpp/bt_factory.h"

namespace mobile_base_navigation
{

IsLocalizationHealthyCondition::IsLocalizationHealthyCondition(
  const std::string & condition_name,
  const BT::NodeConfig & conf)
: BT::ConditionNode(condition_name, conf)
{
  rclcpp::Node::SharedPtr node;
  if (config().blackboard && config().blackboard->get<rclcpp::Node::SharedPtr>("node", node)) {
    initialize();
  }
}

IsLocalizationHealthyCondition::~IsLocalizationHealthyCondition()
{
  if (initialized_ && callback_group_) {
    callback_group_executor_.remove_callback_group(callback_group_);
  }
}

void IsLocalizationHealthyCondition::initialize()
{
  if (initialized_) {
    return;
  }

  if (!config().blackboard ||
    !config().blackboard->get<rclcpp::Node::SharedPtr>("node", node_) ||
    !node_)
  {
    throw BT::RuntimeError("IsLocalizationHealthyCondition: 'node' not found in blackboard");
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
    std::bind(&IsLocalizationHealthyCondition::onMessage, this, std::placeholders::_1),
    sub_options);

  initialized_ = true;
}

void IsLocalizationHealthyCondition::onMessage(const std_msgs::msg::Bool::SharedPtr msg)
{
  std::lock_guard<std::mutex> lock(mutex_);
  last_msg_time_ = node_->now();
  last_lost_ = msg->data;
  has_msg_ = true;
}

BT::NodeStatus IsLocalizationHealthyCondition::tick()
{
  if (!initialized_) {
    initialize();
  }

  callback_group_executor_.spin_some();

  getInput("freshness_timeout_s", freshness_timeout_s_);

  std::lock_guard<std::mutex> lock(mutex_);
  if (!has_msg_) {
    return BT::NodeStatus::FAILURE;
  }

  const rclcpp::Time now = node_->now();
  if (now < last_msg_time_ || (now - last_msg_time_).seconds() > freshness_timeout_s_) {
    return BT::NodeStatus::FAILURE;
  }

  if (last_lost_) {
    return BT::NodeStatus::FAILURE;
  }

  return BT::NodeStatus::SUCCESS;
}

}  // namespace mobile_base_navigation

BT_REGISTER_NODES(factory)
{
  factory.registerNodeType<mobile_base_navigation::IsLocalizationHealthyCondition>(
    "IsLocalizationHealthy");
}
