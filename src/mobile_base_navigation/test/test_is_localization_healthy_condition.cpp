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
#include <string>
#include <thread>

#include "gtest/gtest.h"
#include "rclcpp/rclcpp.hpp"
#include "behaviortree_cpp/bt_factory.h"
#include "std_msgs/msg/bool.hpp"
#include "rosgraph_msgs/msg/clock.hpp"
#include "mobile_base_navigation/is_localization_healthy_condition.hpp"

class IsLocalizationHealthyTest : public ::testing::Test
{
protected:
  static void SetUpTestSuite()
  {
    if (!rclcpp::ok()) {
      rclcpp::init(0, nullptr);
    }
  }

  static void TearDownTestSuite()
  {
    if (rclcpp::ok()) {
      rclcpp::shutdown();
    }
  }

  void SetUp() override
  {
    node_ = std::make_shared<rclcpp::Node>("test_is_localization_healthy_node");
    pub_ = node_->create_publisher<std_msgs::msg::Bool>("/localization/lost", 10);
    factory_.registerNodeType<mobile_base_navigation::IsLocalizationHealthyCondition>(
      "IsLocalizationHealthy");
  }

  void publishLost(bool lost)
  {
    std_msgs::msg::Bool msg;
    msg.data = lost;
    pub_->publish(msg);
  }

  bool waitForStatus(BT::Tree & tree, BT::NodeStatus expected, int timeout_ms = 500)
  {
    auto start = std::chrono::steady_clock::now();
    while ((std::chrono::steady_clock::now() - start) < std::chrono::milliseconds(timeout_ms)) {
      if (tree.tickOnce() == expected) {
        return true;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    return false;
  }

  BT::BehaviorTreeFactory factory_;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr pub_;
};

TEST_F(IsLocalizationHealthyTest, NoMessageReceivedIsFailure)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::FAILURE);
}

TEST_F(IsLocalizationHealthyTest, FreshLostFalseIsSuccess)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  publishLost(false);

  EXPECT_TRUE(waitForStatus(tree, BT::NodeStatus::SUCCESS, 500));
}

TEST_F(IsLocalizationHealthyTest, FreshLostTrueIsFailure)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  publishLost(true);

  EXPECT_TRUE(waitForStatus(tree, BT::NodeStatus::FAILURE, 500));
}

TEST_F(IsLocalizationHealthyTest, StaleLostFalseIsFailure)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"0.1\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  publishLost(false);

  // Fresh lost=false should succeed
  EXPECT_TRUE(waitForStatus(tree, BT::NodeStatus::SUCCESS, 500));

  // Sleep longer than freshness_timeout_s (100ms)
  std::this_thread::sleep_for(std::chrono::milliseconds(150));

  // Stale message must result in FAILURE
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::FAILURE);
}

TEST_F(IsLocalizationHealthyTest, StaleLostTrueIsFailure)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"0.1\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  publishLost(true);

  EXPECT_TRUE(waitForStatus(tree, BT::NodeStatus::FAILURE, 500));

  std::this_thread::sleep_for(std::chrono::milliseconds(150));

  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::FAILURE);
}

TEST_F(IsLocalizationHealthyTest, FreshHealthyAfterStaleOrLost)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"0.1\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // 1. Initially lost=true
  publishLost(true);
  EXPECT_TRUE(waitForStatus(tree, BT::NodeStatus::FAILURE, 500));

  // 2. Allow it to become stale
  std::this_thread::sleep_for(std::chrono::milliseconds(150));
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::FAILURE);

  // 3. New fresh lost=false arrives
  publishLost(false);
  EXPECT_TRUE(waitForStatus(tree, BT::NodeStatus::SUCCESS, 500));
}

TEST_F(IsLocalizationHealthyTest, UseSimTimeRosClockBehavior)
{
  rclcpp::NodeOptions options;
  options.parameter_overrides({{"use_sim_time", true}});
  auto sim_node = std::make_shared<rclcpp::Node>("test_sim_loc_node", options);

  auto clock_pub = sim_node->create_publisher<rosgraph_msgs::msg::Clock>("/clock", 10);
  auto loc_pub = sim_node->create_publisher<std_msgs::msg::Bool>("/sim/localization/lost", 10);

  auto setClock = [&](int64_t sec, uint32_t nanosec) {
      rosgraph_msgs::msg::Clock clock_msg;
      clock_msg.clock.sec = sec;
      clock_msg.clock.nanosec = nanosec;
      clock_pub->publish(clock_msg);
      rclcpp::spin_some(sim_node);
    };

  // Set initial sim time: 1000.0s
  for (int i = 0; i < 5; ++i) {
    setClock(1000, 0);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <IsLocalizationHealthy topic=\"/sim/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", sim_node);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // 1. Initial tick before message -> FAILURE
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::FAILURE);

  // Wait until subscriber is discovered
  auto start = std::chrono::steady_clock::now();
  while (loc_pub->get_subscription_count() == 0 &&
    (std::chrono::steady_clock::now() - start) < std::chrono::milliseconds(500))
  {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  // 2. Publish healthy message at sim time 1000.0s
  std_msgs::msg::Bool lost_msg;
  lost_msg.data = false;
  loc_pub->publish(lost_msg);

  auto waitForSimStatus = [&](BT::NodeStatus expected, int timeout_ms = 500) {
      auto loop_start = std::chrono::steady_clock::now();
      while ((std::chrono::steady_clock::now() - loop_start) <
        std::chrono::milliseconds(timeout_ms))
      {
        if (tree.tickOnce() == expected) {
          return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
      }
      return false;
    };

  EXPECT_TRUE(waitForSimStatus(BT::NodeStatus::SUCCESS, 500));

  // 3. Advance sim time by 2.0s to 1002.0s without wall time elapsed
  setClock(1002, 0);
  std::this_thread::sleep_for(std::chrono::milliseconds(10));

  // Should now be considered stale because sim time advanced 2.0s > 1.0s timeout
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::FAILURE);

  // 4. Publish new healthy message at sim time 1002.0s
  loc_pub->publish(lost_msg);

  EXPECT_TRUE(waitForSimStatus(BT::NodeStatus::SUCCESS, 500));
}
