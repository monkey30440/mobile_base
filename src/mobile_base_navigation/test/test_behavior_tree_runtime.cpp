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

#include <atomic>
#include <chrono>
#include <functional>
#include <fstream>
#include <iterator>
#include <utility>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "gtest/gtest.h"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "nav2_msgs/action/compute_route.hpp"
#include "nav2_msgs/action/compute_path_to_pose.hpp"
#include "nav2_msgs/action/follow_path.hpp"
#include "std_srvs/srv/empty.hpp"
#include "tf2_ros/buffer.h"
#include "behaviortree_cpp/bt_factory.h"
#include "nav_msgs/msg/path.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mobile_base_localization/msg/localization_state.hpp"
#include "nav2_route/nav2_route/plugins/graph_file_loaders/geojson_graph_file_loader.hpp"
#include "nav2_route/types.hpp"
#include "nav2_route/route_planner.hpp"
#include "nav2_util/lifecycle_node.hpp"

#ifndef BT_XML_PATH
#define BT_XML_PATH "behavior_trees/route_assisted_nav.xml"
#endif

#ifndef TEST_ROUTE_GRAPH_PATH
#define TEST_ROUTE_GRAPH_PATH "test/test_data/test_route_graph.geojson"
#endif

#ifndef IS_LOCALIZATION_HEALTHY_LIB
#define IS_LOCALIZATION_HEALTHY_LIB "libis_localization_healthy_condition_bt_node.so"
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

template<typename Action>
typename rclcpp_action::Server<Action>::SharedPtr endpoint(
  rclcpp::Node::SharedPtr node, const std::string & name,
  std::function<void(std::shared_ptr<rclcpp_action::ServerGoalHandle<Action>>)> accepted)
{
  return rclcpp_action::create_server<Action>(
    node, name,
    [](const auto &, const auto &) {return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;},
    [](const auto &) {return rclcpp_action::CancelResponse::ACCEPT;}, accepted);
}

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
    "/opt/ros/jazzy/lib/libnav2_rate_controller_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_recovery_node_bt_node.so",
    "/opt/ros/jazzy/lib/libnav2_reinitialize_global_localization_service_bt_node.so",
    IS_LOCALIZATION_HEALTHY_LIB,
    WAIT_FOR_LOCALIZATION_HEALTHY_LIB
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

  auto route = endpoint<nav2_msgs::action::ComputeRoute>(node_, "compute_route", [](auto) {});
  auto planner = endpoint<nav2_msgs::action::ComputePathToPose>(
    node_, "compute_path_to_pose", [](auto) {});
  auto controller = endpoint<nav2_msgs::action::FollowPath>(node_, "follow_path", [](auto) {});
  auto reinit = node_->create_service<std_srvs::srv::Empty>(
    "/reinitialize_global_localization", [](std_srvs::srv::Empty::Request::SharedPtr,
    std_srvs::srv::Empty::Response::SharedPtr) {});
  blackboard->set("wait_for_service_timeout", std::chrono::milliseconds(2000));
  blackboard->set("tf_buffer", std::make_shared<tf2_ros::Buffer>(node_->get_clock()));
  ASSERT_NO_THROW({
    auto tree = factory.createTreeFromFile(BT_XML_PATH, blackboard);
    EXPECT_FALSE(tree.subtrees.empty());
  });
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
  std::this_thread::sleep_for(std::chrono::milliseconds(200));
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
  std::this_thread::sleep_for(std::chrono::milliseconds(200));
  BT::NodeStatus status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::SUCCESS);

  geometry_msgs::msg::PoseStamped start_pose, end_pose;
  ASSERT_TRUE(blackboard->get<geometry_msgs::msg::PoseStamped>("start_pose", start_pose));
  ASSERT_TRUE(blackboard->get<geometry_msgs::msg::PoseStamped>("end_pose", end_pose));

  EXPECT_DOUBLE_EQ(start_pose.pose.position.x, 1.5);
  EXPECT_DOUBLE_EQ(end_pose.pose.position.x, 3.5);
}

TEST_F(BehaviorTreeRuntimeTest, TestFixtureRouteGraphNativeLoader)
{
  nav2_route::GeoJsonGraphFileLoader loader;
  auto lc_node = std::make_shared<nav2_util::LifecycleNode>("test_route_loader_node");
  loader.configure(lc_node);

  nav2_route::Graph graph;
  nav2_route::GraphToIDMap map_ids;

  std::string filepath = TEST_ROUTE_GRAPH_PATH;
  bool success = loader.loadGraphFromFile(graph, map_ids, filepath);
  ASSERT_TRUE(success) << "Failed to load test route graph from " << filepath;

  EXPECT_EQ(graph.size(), 3u);
  size_t total_edges = 0;
  for (const auto & n : graph) {
    total_edges += n.neighbors.size();
  }
  EXPECT_EQ(total_edges, 2u);
}

TEST_F(BehaviorTreeRuntimeTest, TestFixtureComputeRouteSearch)
{
  nav2_route::GeoJsonGraphFileLoader loader;
  auto lc_node = std::make_shared<nav2_util::LifecycleNode>("test_route_search_node");
  loader.configure(lc_node);

  nav2_route::Graph graph;
  nav2_route::GraphToIDMap map_ids;

  std::string filepath = TEST_ROUTE_GRAPH_PATH;
  ASSERT_TRUE(loader.loadGraphFromFile(graph, map_ids, filepath));

  nav2_route::RoutePlanner planner;
  planner.configure(lc_node, nullptr, nullptr);

  std::vector<unsigned int> blocked_ids;

  nav2_route::RouteRequest request;
  request.start_nodeid = 0;
  request.goal_nodeid = 2;
  request.use_poses = false;
  auto route = planner.findRoute(graph, map_ids[0], map_ids[2], blocked_ids, request);
  ASSERT_EQ(route.edges.size(), 2u);
  EXPECT_EQ(route.edges[0]->edgeid, 3u);
  EXPECT_EQ(route.edges[0]->start->nodeid, 0u);
  EXPECT_EQ(route.edges[0]->end->nodeid, 1u);
  EXPECT_EQ(route.edges[1]->edgeid, 4u);
  EXPECT_EQ(route.edges[1]->start->nodeid, 1u);
  EXPECT_EQ(route.edges[1]->end->nodeid, 2u);
  EXPECT_NEAR(route.route_cost, 4.0f, 1e-3);
}

class MockReinitGlobalLocalization : public BT::SyncActionNode
{
public:
  MockReinitGlobalLocalization(const std::string & name, const BT::NodeConfig & config)
  : BT::SyncActionNode(name, config) {}

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<std::string>("service_name", "AMCL service name")
    };
  }

  BT::NodeStatus tick() override
  {
    call_count++;
    return BT::NodeStatus::SUCCESS;
  }

  static void reset()
  {
    call_count = 0;
  }

  static inline int call_count = 0;
};

class MockFollowPathAction : public BT::SyncActionNode
{
public:
  MockFollowPathAction(const std::string & name, const BT::NodeConfig & config)
  : BT::SyncActionNode(name, config) {}

  static BT::PortsList providedPorts()
  {
    return {
      BT::InputPort<nav_msgs::msg::Path>("path", "Path to follow"),
      BT::InputPort<std::string>("controller_id", "Controller ID"),
      BT::InputPort<std::string>("goal_checker_id", "Goal checker ID"),
      BT::OutputPort<std::string>("error_code_id", "Error code ID"),
    };
  }

  BT::NodeStatus tick() override
  {
    tick_count++;
    return BT::NodeStatus::SUCCESS;
  }

  static void reset()
  {
    tick_count = 0;
  }

  static inline int tick_count = 0;
};

TEST_F(BehaviorTreeRuntimeTest, LocalizationRecoveryBoundedWaitSemantics)
{
  BT::BehaviorTreeFactory factory;
  factory.registerFromPlugin(WAIT_FOR_LOCALIZATION_HEALTHY_LIB);
  factory.registerNodeType<MockReinitGlobalLocalization>("ReinitializeGlobalLocalization");

  const std::string xml =
    "<root BTCPP_format=\"4\" main_tree_to_execute=\"MainTree\">"
    "  <BehaviorTree ID=\"MainTree\">"
    "    <Sequence name=\"LocalizationRecovery\">"
    "      <ReinitializeGlobalLocalization"
    "        service_name=\"/reinitialize_global_localization\"/>"
    "      <Timeout msec=\"200\">"
    "        <WaitForLocalizationHealthy"
    "          topic=\"/bt_test/localization/state\"/>"
    "      </Timeout>"
    "    </Sequence>"
    "  </BehaviorTree>"
    "</root>";

  auto blackboard = BT::Blackboard::create();
  blackboard->set<rclcpp::Node::SharedPtr>("node", node_);

  auto loc_pub = node_->create_publisher<mobile_base_localization::msg::LocalizationState>(
    "/bt_test/localization/state", rclcpp::QoS(1).reliable().transient_local());
  MockReinitGlobalLocalization::reset();

  auto tree = factory.createTreeFromText(xml, blackboard);
  std::this_thread::sleep_for(std::chrono::milliseconds(200));

  // Wait until subscriber is discovered by publisher
  auto disc_start = std::chrono::steady_clock::now();
  while (loc_pub->get_subscription_count() == 0 &&
    (std::chrono::steady_clock::now() - disc_start) < std::chrono::milliseconds(500))
  {
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  // 0. Pre-condition: publish healthy message BEFORE recovery begins
  mobile_base_localization::msg::LocalizationState msg;
  msg.state = mobile_base_localization::msg::LocalizationState::HEALTHY;
  msg.measurement_stamp = node_->now();
  loc_pub->publish(msg);
  std::this_thread::sleep_for(std::chrono::milliseconds(100));

  // 1. Initial tick -> Reinitialize called once, timeout wait returns RUNNING
  // Pre-recovery healthy message MUST NOT satisfy recovery!
  BT::NodeStatus status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::RUNNING);
  EXPECT_EQ(MockReinitGlobalLocalization::call_count, 1);

  // 2. Second tick while still waiting -> Timeout wait remains RUNNING,
  // Reinitialize NOT repeatedly invoked!
  status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::RUNNING);
  EXPECT_EQ(MockReinitGlobalLocalization::call_count, 1);

  // 3. New post-reinitialize healthy evidence published -> recovery subtree returns SUCCESS
  msg.state = mobile_base_localization::msg::LocalizationState::HEALTHY;
  msg.measurement_stamp = node_->now();
  loc_pub->publish(msg);
  std::this_thread::sleep_for(std::chrono::milliseconds(100));

  status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::SUCCESS);
  EXPECT_EQ(MockReinitGlobalLocalization::call_count, 1);

  // 4. Test timeout expiration leading to FAILURE
  tree.haltTree();
  MockReinitGlobalLocalization::reset();

  // Make localization unhealthy
  msg.state = mobile_base_localization::msg::LocalizationState::LOST;
  msg.measurement_stamp = node_->now();
  loc_pub->publish(msg);
  std::this_thread::sleep_for(std::chrono::milliseconds(20));

  status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::RUNNING);
  EXPECT_EQ(MockReinitGlobalLocalization::call_count, 1);

  // Wait for 200ms timeout to expire
  std::this_thread::sleep_for(std::chrono::milliseconds(250));

  // Tick again -> timeout expired -> subtree returns FAILURE
  status = tree.tickOnce();
  EXPECT_EQ(status, BT::NodeStatus::FAILURE);
  EXPECT_EQ(MockReinitGlobalLocalization::call_count, 1);
}

// Exercise the production XML with native control/dataflow nodes. Only ROS action
// endpoints and current-pose lookup are replaced, so failures test actual BT routing.
struct NavigationScenario
{
  std::string failure;
  int route_calls{0};
  int pose_calls{0};
  int planner_calls{0};
  int follow_calls{0};
  int cancellations{0};
  int resets{0};
  double current_x{0.0};
  double followed_start{-1.0};
  bool complete{false};
};

class NavigationEndpoint : public BT::StatefulActionNode
{
public:
  NavigationEndpoint(
    const std::string & name, const BT::NodeConfig & config,
    const std::string & kind, NavigationScenario & scenario)
  : BT::StatefulActionNode(name, config), kind_(kind), scenario_(scenario) {}

  BT::NodeStatus onStart() override {return step();}
  BT::NodeStatus onRunning() override {return step();}
  void onHalted() override
  {
    if (kind_ == "FollowPath") {
      ++scenario_.cancellations;
    }
  }

private:
  BT::NodeStatus step()
  {
    if (kind_ == "ReinitializeGlobalLocalization") {
      ++scenario_.resets;
      return BT::NodeStatus::SUCCESS;
    }
    if (kind_ == "GetCurrentPose") {
      ++scenario_.pose_calls;
      geometry_msgs::msg::PoseStamped pose;
      pose.header.frame_id = "map";
      pose.pose.position.x = scenario_.current_x;
      pose.pose.orientation.w = 1.0;
      setOutput("current_pose", pose);
      return BT::NodeStatus::SUCCESS;
    }
    if (kind_ == "ComputeRoute") {
      ++scenario_.route_calls;
    } else if (kind_ == "ComputePathToPose") {
      ++scenario_.planner_calls;
    } else if (kind_ == "FollowPath") {
      ++scenario_.follow_calls;
    }
    if (scenario_.failure == kind_) {
      setOutput<uint16_t>("error_code_id", 317);
      return BT::NodeStatus::FAILURE;
    }
    setOutput<uint16_t>("error_code_id", 0);
    if (kind_ == "FollowPath") {
      nav_msgs::msg::Path path;
      getInput("path", path);
      scenario_.followed_start = path.poses.at(0).pose.position.x;
      return scenario_.complete ? BT::NodeStatus::SUCCESS : BT::NodeStatus::RUNNING;
    }
    nav_msgs::msg::Path path;
    path.header.frame_id = "map";
    geometry_msgs::msg::PoseStamped start, goal;
    start.header.frame_id = goal.header.frame_id = "map";
    start.pose.orientation.w = goal.pose.orientation.w = 1.0;
    if (kind_ == "ComputeRoute") {
      start.pose.position.x = 10.0;
      goal.pose.position.x = 20.0;
    } else {
      bool use_start = false;
      getInput("use_start", use_start);
      if (use_start) {
        getInput("start", start);
      } else {
        start.pose.position.x = scenario_.current_x;
      }
      getInput("goal", goal);
    }
    path.poses = {start, goal};
    setOutput("path", path);
    return BT::NodeStatus::SUCCESS;
  }

  std::string kind_;
  NavigationScenario & scenario_;
};

class NavigationRecoveryRuntimeTest : public BehaviorTreeRuntimeTest
{
protected:
  using State = mobile_base_localization::msg::LocalizationState;

  void SetUp() override
  {
    BehaviorTreeRuntimeTest::SetUp();
    pub_ = node_->create_publisher<State>(
      "/localization/state", rclcpp::QoS(1).reliable().transient_local());
    for (const auto & lib : {
      "compute_route", "compute_path_to_pose_action", "follow_path_action",
      "get_current_pose_action", "get_pose_from_path_action", "are_poses_near_condition",
      "concatenate_paths_action", "pipeline_sequence", "rate_controller", "recovery_node",
      "reinitialize_global_localization_service"})
    {
      factory_.registerFromPlugin(std::string("/opt/ros/jazzy/lib/libnav2_") + lib + "_bt_node.so");
    }
    factory_.registerFromPlugin(IS_LOCALIZATION_HEALTHY_LIB);
    factory_.registerFromPlugin(WAIT_FOR_LOCALIZATION_HEALTHY_LIB);
    for (const std::string kind : {"ComputeRoute", "ComputePathToPose", "FollowPath",
        "GetCurrentPose", "ReinitializeGlobalLocalization"})
    {
      const auto manifest = factory_.manifests().at(kind);
      factory_.unregisterBuilder(kind);
      factory_.registerBuilder(manifest, [this, kind](const auto & name, const auto & config) {
          return std::make_unique<NavigationEndpoint>(name, config, kind, scenario_);
      });
    }
    bb_ = BT::Blackboard::create();
    bb_->set("node", node_);
    bb_->set("tf_buffer", std::make_shared<tf2_ros::Buffer>(node_->get_clock()));
    geometry_msgs::msg::PoseStamped goal;
    goal.header.frame_id = "map";
    goal.pose.position.x = 30.0;
    goal.pose.orientation.w = 1.0;
    bb_->set("goal", goal);
    std::ifstream stream(BT_XML_PATH);
    std::string xml((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
    // Shorten only the timeout for the test, preserving production control flow.
    xml.replace(xml.find("msec=\"10000\""), 12, "msec=\"180\"");
    tree_ = factory_.createTreeFromText(xml, bb_);
    for (int i = 0; i < 100 && pub_->get_subscription_count() < 2; ++i) {
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    ASSERT_EQ(pub_->get_subscription_count(), 2u);
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }

  void publish(uint8_t state)
  {
    State msg;
    msg.state = state;
    msg.measurement_stamp = node_->now();
    pub_->publish(msg);
    std::this_thread::sleep_for(std::chrono::milliseconds(30));
  }

  NavigationScenario scenario_;
  BT::BehaviorTreeFactory factory_;
  BT::Blackboard::Ptr bb_;
  BT::Tree tree_;
  rclcpp::Publisher<State>::SharedPtr pub_;
};

TEST_F(NavigationRecoveryRuntimeTest, HealthyExecutesNavigation)
{
  publish(State::HEALTHY);
  scenario_.complete = true;
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::SUCCESS);
  EXPECT_EQ(scenario_.route_calls, 1);
  EXPECT_EQ(scenario_.follow_calls, 1);
  EXPECT_EQ(scenario_.resets, 0);
}

TEST_F(NavigationRecoveryRuntimeTest, UnknownCancelsNavigationWithoutRelocalization)
{
  publish(State::HEALTHY);
  ASSERT_EQ(tree_.tickOnce(), BT::NodeStatus::RUNNING);
  publish(State::UNKNOWN);
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_EQ(scenario_.cancellations, 1);
  EXPECT_EQ(scenario_.follow_calls, 1);
  EXPECT_EQ(scenario_.resets, 0);
}

TEST_F(NavigationRecoveryRuntimeTest, ActionFailuresPreserveErrorAndNeverRelocalize)
{
  for (const auto & entry : std::vector<std::pair<std::string, std::string>>{
    {"ComputeRoute", "compute_route_error_code"},
    {"ComputePathToPose", "compute_path_error_code"},
    {"FollowPath", "follow_path_error_code"}})
  {
    tree_.haltTree();
    scenario_ = NavigationScenario{};
    scenario_.failure = entry.first;
    publish(State::HEALTHY);
    EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::FAILURE) << entry.first;
    EXPECT_EQ(scenario_.resets, 0) << entry.first;
    EXPECT_EQ(bb_->get<uint16_t>(entry.second), 317) << entry.first;
  }
}

TEST_F(NavigationRecoveryRuntimeTest, LostCancelsThenRecoversAndReplansFromNewPose)
{
  publish(State::HEALTHY);
  ASSERT_EQ(tree_.tickOnce(), BT::NodeStatus::RUNNING);
  EXPECT_DOUBLE_EQ(scenario_.followed_start, 0.0);
  publish(State::LOST);
  ASSERT_EQ(tree_.tickOnce(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(scenario_.cancellations, 1);
  EXPECT_EQ(scenario_.resets, 1);
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(scenario_.follow_calls, 1);
  scenario_.current_x = 5.0;
  scenario_.complete = true;
  publish(State::HEALTHY);
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::SUCCESS);
  EXPECT_EQ(scenario_.resets, 1);
  EXPECT_EQ(scenario_.route_calls, 2);
  EXPECT_EQ(scenario_.pose_calls, 2);
  EXPECT_EQ(scenario_.planner_calls, 4);
  EXPECT_DOUBLE_EQ(scenario_.followed_start, 5.0);
}

TEST_F(NavigationRecoveryRuntimeTest, LostRecoveryTimeoutFailsNavigation)
{
  publish(State::LOST);
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::RUNNING);
  EXPECT_EQ(scenario_.resets, 1);
  publish(State::UNKNOWN);
  std::this_thread::sleep_for(std::chrono::milliseconds(210));
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_EQ(scenario_.resets, 1);
  EXPECT_EQ(scenario_.follow_calls, 0);
}

TEST_F(BehaviorTreeRuntimeTest, NativeActionFailuresRetainErrorCodesThroughProductionTree)
{
  using Route = nav2_msgs::action::ComputeRoute;
  using Plan = nav2_msgs::action::ComputePathToPose;
  using Follow = nav2_msgs::action::FollowPath;
  using State = mobile_base_localization::msg::LocalizationState;
  auto server_node = std::make_shared<rclcpp::Node>("test_native_navigation_endpoints");
  std::atomic<int> failure{0};
  std::atomic<int> resets{0};
  auto make_path = [](double start_x, double end_x) {
      nav_msgs::msg::Path path;
      path.header.frame_id = "map";
      geometry_msgs::msg::PoseStamped start, end;
      start.header.frame_id = end.header.frame_id = "map";
      start.pose.orientation.w = end.pose.orientation.w = 1.0;
      start.pose.position.x = start_x;
      end.pose.position.x = end_x;
      path.poses = {start, end};
      return path;
    };
  auto route = endpoint<Route>(server_node, "compute_route", [&](auto goal) {
        auto result = std::make_shared<Route::Result>();
        if (failure == 1) {
          result->error_code = 401;
          goal->abort(result);
        } else {
          result->path = make_path(10.0, 20.0);
          goal->succeed(result);
        }
    });
  auto planner = endpoint<Plan>(server_node, "compute_path_to_pose", [&](auto goal) {
        auto result = std::make_shared<Plan::Result>();
        if (failure == 2) {
          result->error_code = 201;
          goal->abort(result);
        } else {
          const auto request = goal->get_goal();
          result->path = make_path(
          request->use_start ? request->start.pose.position.x : 0.0,
          request->goal.pose.position.x);
          goal->succeed(result);
        }
    });
  auto controller = endpoint<Follow>(server_node, "follow_path", [](auto goal) {
        auto result = std::make_shared<Follow::Result>();
        result->error_code = 101;
        goal->abort(result);
    });
  auto reinit = server_node->create_service<std_srvs::srv::Empty>(
    "/reinitialize_global_localization", [&](std_srvs::srv::Empty::Request::SharedPtr,
    std_srvs::srv::Empty::Response::SharedPtr) {++resets;});
  auto pub = server_node->create_publisher<State>(
    "/localization/state", rclcpp::QoS(1).reliable().transient_local());
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(server_node);
  struct SpinThread
  {
    rclcpp::executors::SingleThreadedExecutor & executor;
    std::thread thread;
    explicit SpinThread(rclcpp::executors::SingleThreadedExecutor & exec)
    : executor(exec), thread([&exec]() {exec.spin();}) {}
    ~SpinThread() {executor.cancel(); thread.join();}
  } spinner(executor);

  BT::BehaviorTreeFactory factory;
  for (const auto & lib : {
    "compute_route", "compute_path_to_pose_action", "follow_path_action",
    "get_current_pose_action", "get_pose_from_path_action", "are_poses_near_condition",
    "concatenate_paths_action", "pipeline_sequence", "rate_controller", "recovery_node",
    "reinitialize_global_localization_service"})
  {
    factory.registerFromPlugin(std::string("/opt/ros/jazzy/lib/libnav2_") + lib + "_bt_node.so");
  }
  factory.registerFromPlugin(IS_LOCALIZATION_HEALTHY_LIB);
  factory.registerFromPlugin(WAIT_FOR_LOCALIZATION_HEALTHY_LIB);
  for (int which = 1; which <= 3; ++which) {
    failure = which;
    auto bb = BT::Blackboard::create();
    bb->set("node", node_);
    bb->set("server_timeout", std::chrono::milliseconds(100));
    bb->set("wait_for_service_timeout", std::chrono::milliseconds(2000));
    bb->set("bt_loop_duration", std::chrono::milliseconds(10));
    auto buffer = std::make_shared<tf2_ros::Buffer>(node_->get_clock());
    geometry_msgs::msg::TransformStamped transform;
    transform.header.frame_id = "map";
    transform.child_frame_id = "base_footprint";
    transform.transform.rotation.w = 1.0;
    buffer->setTransform(transform, "test", true);
    bb->set("tf_buffer", buffer);
    bb->set("goal", make_path(0.0, 30.0).poses.back());
    auto tree = factory.createTreeFromFile(BT_XML_PATH, bb);
    State state;
    state.state = State::HEALTHY;
    state.measurement_stamp = node_->now();
    pub->publish(state);
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    auto status = BT::NodeStatus::RUNNING;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (status == BT::NodeStatus::RUNNING && std::chrono::steady_clock::now() < deadline) {
      status = tree.tickOnce();
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    EXPECT_EQ(status, BT::NodeStatus::FAILURE) << which;
    const std::vector<std::string> codes = {
      "compute_route_error_code", "compute_path_error_code", "follow_path_error_code"};
    // Nav2 BtActionServer::populateErrorCode reads these entries as int.
    EXPECT_EQ(bb->get<int>(codes.at(which - 1)), which == 1 ? 401 : (which == 2 ? 201 : 101));
    EXPECT_EQ(resets.load(), 0);
  }
}

TEST_F(NavigationRecoveryRuntimeTest, PublisherSilenceCancelsWithoutGlobalRelocalization)
{
  publish(State::HEALTHY);
  ASSERT_EQ(tree_.tickOnce(), BT::NodeStatus::RUNNING);
  std::this_thread::sleep_for(std::chrono::milliseconds(1100));
  EXPECT_EQ(tree_.tickOnce(), BT::NodeStatus::FAILURE);
  EXPECT_FALSE(bb_->get<bool>("localization_recovery_required"));
  EXPECT_EQ(scenario_.cancellations, 1);
  EXPECT_EQ(scenario_.follow_calls, 1);
  EXPECT_EQ(scenario_.resets, 0);
}
