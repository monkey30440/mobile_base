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
#include "mobile_base_navigation/wait_for_localization_healthy_node.hpp"

class WaitForLocalizationHealthyTest : public ::testing::Test
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
    node_ = std::make_shared<rclcpp::Node>("test_wait_for_localization_healthy_node");
    pub_ = node_->create_publisher<std_msgs::msg::Bool>("/localization/lost", 10);
    factory_.registerNodeType<mobile_base_navigation::WaitForLocalizationHealthyNode>(
      "WaitForLocalizationHealthy");
  }

  void publishLost(bool lost)
  {
    std_msgs::msg::Bool msg;
    msg.data = lost;
    pub_->publish(msg);
    rclcpp::spin_some(node_);
  }

  BT::BehaviorTreeFactory factory_;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr pub_;
};

// Reproduces the race explicitly:
// A. publish healthy lost=false BEFORE recovery wait starts
// B. start recovery
// C. verify recovery remains RUNNING; the old/pre-start healthy evidence must NOT succeed
// D. publish a NEW lost=false after recovery starts
// E. verify SUCCESS
TEST_F(WaitForLocalizationHealthyTest, RecoveryIgnoresPreStartEvidenceAndSucceedsOnNewEvidence)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <WaitForLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // Wait for subscription discovery
  auto start = std::chrono::steady_clock::now();
  while (pub_->get_subscription_count() == 0 &&
    (std::chrono::steady_clock::now() - start) < std::chrono::milliseconds(500))
  {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  // Step A: Publish healthy lost=false BEFORE recovery wait starts
  publishLost(false);
  std::this_thread::sleep_for(std::chrono::milliseconds(100));

  // Step B & C: Start recovery and verify recovery remains RUNNING
  // (pre-start healthy evidence must NOT satisfy recovery!)
  BT::NodeStatus status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::RUNNING);

  // Still running on subsequent ticks while waiting
  status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::RUNNING);

  // Step D: Publish a NEW lost=false after recovery started
  publishLost(false);
  std::this_thread::sleep_for(std::chrono::milliseconds(100));

  // Step E: Verify SUCCESS
  status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::SUCCESS);
}

TEST_F(WaitForLocalizationHealthyTest, NoEvidenceReturnsRunning)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <WaitForLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // No messages published -> returns RUNNING
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);
}

TEST_F(WaitForLocalizationHealthyTest, NewLostTrueReturnsRunning)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <WaitForLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // Start recovery
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);

  // Publish new lost=true after start
  publishLost(true);
  std::this_thread::sleep_for(std::chrono::milliseconds(30));

  // Must continue returning RUNNING
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);
}

TEST_F(WaitForLocalizationHealthyTest, NewEvidenceStaleReturnsRunning)
{
  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <WaitForLocalizationHealthy topic=\"/localization/lost\" freshness_timeout_s=\"0.1\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // Start recovery
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);

  // Publish new lost=true and tick to process it into last_msg_time_
  publishLost(true);
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);

  // Sleep longer than 100ms freshness timeout so message becomes stale
  std::this_thread::sleep_for(std::chrono::milliseconds(150));

  // Stale message must result in RUNNING (continue waiting), not SUCCESS
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);
}

TEST_F(WaitForLocalizationHealthyTest, UseSimTimeClockBehavior)
{
  rclcpp::NodeOptions options;
  options.parameter_overrides({{"use_sim_time", true}});
  auto sim_node = std::make_shared<rclcpp::Node>("test_sim_wait_loc_node", options);

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
    "    <WaitForLocalizationHealthy topic=\"/sim/localization/lost\" freshness_timeout_s=\"1.0\"/>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", sim_node);

  auto tree = factory_.createTreeFromText(xml, blackboard);

  // Wait for subscriber discovery
  auto start = std::chrono::steady_clock::now();
  while (loc_pub->get_subscription_count() == 0 &&
    (std::chrono::steady_clock::now() - start) < std::chrono::milliseconds(500))
  {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  // Publish message before start at 1000.0s
  std_msgs::msg::Bool msg;
  msg.data = false;
  loc_pub->publish(msg);
  std::this_thread::sleep_for(std::chrono::milliseconds(20));

  // Start recovery at 1000.0s -> RUNNING (pre-start message ignored)
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);

  // Publish new healthy message at 1001.0s
  setClock(1001, 0);
  std::this_thread::sleep_for(std::chrono::milliseconds(10));
  loc_pub->publish(msg);
  std::this_thread::sleep_for(std::chrono::milliseconds(20));

  // Should succeed
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::SUCCESS);
}
