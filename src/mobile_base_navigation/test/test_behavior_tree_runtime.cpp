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
#include <vector>

#include "gtest/gtest.h"
#include "rclcpp/rclcpp.hpp"
#include "behaviortree_cpp/bt_factory.h"
#include "nav_msgs/msg/path.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav2_route/nav2_route/plugins/graph_file_loaders/geojson_graph_file_loader.hpp"
#include "nav2_route/types.hpp"
#include "nav2_util/lifecycle_node.hpp"

#ifndef BT_XML_PATH
#define BT_XML_PATH "behavior_trees/route_assisted_nav.xml"
#endif

#ifndef REAL_ROUTE_GRAPH_PATH
#define REAL_ROUTE_GRAPH_PATH "../../maps/test_site/route_graph.geojson"
#endif

class BehaviorTreeRuntimeTest : public ::testing::Test
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
    node_ = std::make_shared<rclcpp::Node>("test_bt_runtime_node");
  }

  rclcpp::Node::SharedPtr node_;
};

TEST_F(BehaviorTreeRuntimeTest, FactoryPluginRegistrationAndTreeInstantiate)
{
  BT::BehaviorTreeFactory factory;

  // Register all required Nav2 BT plugins
  const std::vector<std::string> plugin_libs = {
    "/opt/ros/jazzy/lib/libnav2_compute_route_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_compute_path_to_pose_action_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_follow_path_action_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_get_current_pose_action_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_get_pose_from_path_action_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_are_poses_near_condition_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_concatenate_paths_action_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_pipeline_sequence_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_rate_controller_bt_node.so"
  };

  for (const auto & lib : plugin_libs) {
    ASSERT_NO_THROW(factory.registerFromPlugin(lib))
      << "Failed to register plugin from " << lib;
  }

  // Create blackboard with required ROS node pointer and parameters
  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);
  blackboard->set<std::chrono::milliseconds>(
    "server_timeout", std::chrono::milliseconds(10));
  blackboard->set<std::chrono::milliseconds>(
    "wait_for_service_timeout", std::chrono::milliseconds(50));
  blackboard->set<std::chrono::milliseconds>(
    "bt_loop_duration", std::chrono::milliseconds(10));

  // Instantiating tree from route_assisted_nav.xml
  std::string xml_file = BT_XML_PATH;
  try {
    auto tree = factory.createTreeFromFile(xml_file, blackboard);
    EXPECT_FALSE(tree.subtrees.empty());
  } catch (const BT::RuntimeError & e) {
    FAIL() << "BT XML schema/port resolution failed with BT::RuntimeError: " << e.what();
  } catch (const BT::LogicError & e) {
    FAIL() << "BT XML logic error: " << e.what();
  } catch (const std::runtime_error & e) {
    std::string msg = e.what();
    EXPECT_TRUE(
      msg.find("Action server") != std::string::npos ||
      msg.find("not available") != std::string::npos)
      << "Unexpected runtime exception: " << msg;
  }
}

TEST_F(BehaviorTreeRuntimeTest, PathConcatenationDataflow)
{
  BT::BehaviorTreeFactory factory;
  factory.registerFromPlugin(
    "/opt/ros/jazzy/lib/libnav2_concatenate_paths_action_bt_node.so");

  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <ConcatenatePaths input_path1=\"{p1}\" input_path2=\"{p2}\" output_path=\"{p_out}\" />"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  // Prepare input path 1 (2 poses: x=0.0, x=1.0)
  nav_msgs::msg::Path path1;
  path1.header.frame_id = "map";
  geometry_msgs::msg::PoseStamped pose1, pose2;
  pose1.pose.position.x = 0.0;
  pose2.pose.position.x = 1.0;
  path1.poses.push_back(pose1);
  path1.poses.push_back(pose2);

  // Prepare input path 2 (2 poses: x=2.0, x=3.0)
  nav_msgs::msg::Path path2;
  path2.header.frame_id = "map";
  geometry_msgs::msg::PoseStamped pose3, pose4;
  pose3.pose.position.x = 2.0;
  pose4.pose.position.x = 3.0;
  path2.poses.push_back(pose3);
  path2.poses.push_back(pose4);

  blackboard->set<nav_msgs::msg::Path>("p1", path1);
  blackboard->set<nav_msgs::msg::Path>("p2", path2);

  auto tree = factory.createTreeFromText(xml, blackboard);
  BT::NodeStatus status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::SUCCESS);

  // Verify output path is concatenated in correct sequential order (4 poses: 0, 1, 2, 3)
  nav_msgs::msg::Path out_path;
  ASSERT_TRUE(blackboard->get<nav_msgs::msg::Path>("p_out", out_path));
  ASSERT_EQ(out_path.poses.size(), 4u);
  EXPECT_DOUBLE_EQ(out_path.poses[0].pose.position.x, 0.0);
  EXPECT_DOUBLE_EQ(out_path.poses[1].pose.position.x, 1.0);
  EXPECT_DOUBLE_EQ(out_path.poses[2].pose.position.x, 2.0);
  EXPECT_DOUBLE_EQ(out_path.poses[3].pose.position.x, 3.0);
}

TEST_F(BehaviorTreeRuntimeTest, GetPoseFromPathDataflow)
{
  BT::BehaviorTreeFactory factory;
  factory.registerFromPlugin(
    "/opt/ros/jazzy/lib/libnav2_get_pose_from_path_action_bt_node.so");

  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <Sequence>"
    "      <GetPoseFromPath path=\"{p_in}\" index=\"0\" pose=\"{start_pose}\" />"
    "      <GetPoseFromPath path=\"{p_in}\" index=\"-1\" pose=\"{end_pose}\" />"
    "    </Sequence>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  // Prepare input path (3 poses: x=1.5, x=2.5, x=3.5)
  nav_msgs::msg::Path path;
  path.header.frame_id = "map";
  geometry_msgs::msg::PoseStamped p1, p2, p3;
  p1.pose.position.x = 1.5;
  p2.pose.position.x = 2.5;
  p3.pose.position.x = 3.5;
  path.poses.push_back(p1);
  path.poses.push_back(p2);
  path.poses.push_back(p3);

  blackboard->set<nav_msgs::msg::Path>("p_in", path);

  auto tree = factory.createTreeFromText(xml, blackboard);
  BT::NodeStatus status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::SUCCESS);

  geometry_msgs::msg::PoseStamped start_pose, end_pose;
  ASSERT_TRUE(blackboard->get<geometry_msgs::msg::PoseStamped>("start_pose", start_pose));
  ASSERT_TRUE(blackboard->get<geometry_msgs::msg::PoseStamped>("end_pose", end_pose));

  EXPECT_DOUBLE_EQ(start_pose.pose.position.x, 1.5);
  EXPECT_DOUBLE_EQ(end_pose.pose.position.x, 3.5);
}

TEST_F(BehaviorTreeRuntimeTest, RealSiteRouteGraphNativeLoader)
{
  nav2_route::GeoJsonGraphFileLoader loader;
  auto lc_node = std::make_shared<nav2_util::LifecycleNode>("test_route_loader_node");
  loader.configure(lc_node);

  nav2_route::Graph graph;
  nav2_route::GraphToIDMap map_ids;

  std::string filepath = REAL_ROUTE_GRAPH_PATH;
  bool success = loader.loadGraphFromFile(graph, map_ids, filepath);
  ASSERT_TRUE(success) << "Failed to load real-site route graph from " << filepath;

  EXPECT_EQ(graph.size(), 2u);
  size_t total_edges = 0;
  for (const auto & n : graph) {
    total_edges += n.neighbors.size();
  }
  EXPECT_EQ(total_edges, 1u);
}
