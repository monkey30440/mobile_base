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
#include "mobile_base_navigation/is_localization_healthy_condition.hpp"

using State = mobile_base_localization::msg::LocalizationState;

class IsLocalizationHealthyTest : public ::testing::Test
{
protected:
  void SetUp() override
  {
    rclcpp::init(0, nullptr);
    node = std::make_shared<rclcpp::Node>("test_localization_adapter");
    pub = node->create_publisher<State>(
      "/localization/state", rclcpp::QoS(1).reliable().transient_local());
    factory.registerNodeType<mobile_base_navigation::IsLocalizationHealthyCondition>(
      "IsLocalizationHealthy");
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
        <IsLocalizationHealthy recovery_required="{lost}"/>
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

TEST_F(IsLocalizationHealthyTest, ExplicitStatesAndFailureCause)
{
  auto bt = tree();
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_FALSE(bb->get<bool>("lost"));
  for (uint8_t state : {State::HEALTHY, State::UNKNOWN, State::LOST, uint8_t(255)}) {
    publish(state, node->now());
    EXPECT_EQ(bt.tickOnce(), state == State::HEALTHY ?
      BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE);
    EXPECT_EQ(bb->get<bool>("lost"), state == State::LOST);
  }
}

TEST_F(IsLocalizationHealthyTest, StateAuthorityRemainsInLocalization)
{
  auto bt = tree();
  publish(State::HEALTHY, rclcpp::Time(1, 0, RCL_ROS_TIME));
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::SUCCESS);
  publish(State::UNKNOWN, node->now());
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_FALSE(bb->get<bool>("lost"));
}

TEST_F(IsLocalizationHealthyTest, PublisherSilenceFailsWithoutRecoveryAuthorization)
{
  auto bt = tree();
  publish(State::HEALTHY, rclcpp::Time(1, 0, RCL_ROS_TIME));
  ASSERT_EQ(bt.tickOnce(), BT::NodeStatus::SUCCESS);
  std::this_thread::sleep_for(std::chrono::milliseconds(1100));
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_FALSE(bb->get<bool>("lost"));
  publish(State::HEALTHY, rclcpp::Time(1, 0, RCL_ROS_TIME));
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::SUCCESS);
  publish(State::LOST, node->now());
  ASSERT_EQ(bt.tickOnce(), BT::NodeStatus::FAILURE);
  ASSERT_TRUE(bb->get<bool>("lost"));
  std::this_thread::sleep_for(std::chrono::milliseconds(1100));
  EXPECT_EQ(bt.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_FALSE(bb->get<bool>("lost"));
}
