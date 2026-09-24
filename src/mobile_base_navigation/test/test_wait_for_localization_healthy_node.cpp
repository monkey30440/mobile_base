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

#include <chrono>
#include <memory>
#include <thread>

#include "gtest/gtest.h"
#include "behaviortree_cpp/bt_factory.h"
#include "mobile_base_navigation/wait_for_localization_healthy_node.hpp"

using State = mobile_base_localization::msg::LocalizationState;

class WaitForLocalizationHealthyTest : public ::testing::Test
{
protected:
  void SetUp() override
  {
    rclcpp::init(0, nullptr);
    node = std::make_shared<rclcpp::Node>("test_localization_adapter");
    pub = node->create_publisher<State>(
      "/localization/state", rclcpp::QoS(1).reliable().transient_local());
    factory.registerNodeType<mobile_base_navigation::WaitForLocalizationHealthyNode>(
      "WaitForLocalizationHealthy");
    bb = BT::Blackboard::create();
    bb->set("node", node);
  }

  void TearDown() override
  {
    pub.reset();
    node.reset();
    rclcpp::shutdown();
  }

  void publish(uint8_t state, rclcpp::Time stamp)
  {
    State msg;
    msg.state = state;
    msg.measurement_stamp = stamp;
    pub->publish(msg);
    std::this_thread::sleep_for(std::chrono::milliseconds(40));
  }

  BT::Tree tree()
  {
    auto result = factory.createTreeFromText(
      R"(<root BTCPP_format="4"><BehaviorTree ID="Main">
        <WaitForLocalizationHealthy />
      </BehaviorTree></root>)",
      bb);
    for (int i = 0; i < 100 && pub->get_subscription_count() == 0; ++i) {
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    return result;
  }

  rclcpp::Node::SharedPtr node;
  rclcpp::Publisher<State>::SharedPtr pub;
  BT::BehaviorTreeFactory factory;
  BT::Blackboard::Ptr bb;
};

TEST_F(WaitForLocalizationHealthyTest, RequiresNewHealthyMeasurementNotNewDelivery)
{
  auto bt = tree();
  const auto old_stamp = node->now();
  publish(State::HEALTHY, old_stamp);
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::RUNNING);
  publish(State::HEALTHY, old_stamp);
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::RUNNING);
  publish(State::UNKNOWN, node->now());
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::RUNNING);
  publish(State::LOST, node->now());
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::RUNNING);
  publish(State::HEALTHY, node->now());
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::SUCCESS);
  bt.haltTree();
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::RUNNING);
  publish(State::HEALTHY, old_stamp);
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::RUNNING);
}
