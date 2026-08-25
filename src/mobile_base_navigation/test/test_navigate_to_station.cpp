// Copyright 2026 mobile_base developer
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

#include <sys/wait.h>
#include <unistd.h>

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <future>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "navigate_to_station_app.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

using namespace std::chrono_literals;

namespace mobile_base_navigation
{
namespace
{

class TemporaryCatalog
{
public:
  explicit TemporaryCatalog(const std::string & content)
  {
    char path[] = "/tmp/mobile_base_station_catalog_XXXXXX";
    const int descriptor = mkstemp(path);
    if (descriptor < 0) {
      throw std::runtime_error("Unable to create temporary station catalog");
    }
    close(descriptor);
    path_ = path;
    std::ofstream stream(path_);
    stream << content;
  }

  ~TemporaryCatalog()
  {
    std::remove(path_.c_str());
  }

  const std::string & path() const {return path_;}

private:
  std::string path_;
};

const char kValidCatalog[] =
  "frame_id: map\n"
  "stations:\n"
  "  - id: station_A\n"
  "    x: 2.5\n"
  "    y: -1.25\n"
  "    yaw_rad: 1.5707963267948966\n";

enum class ServerMode {SUCCEED, REJECT, ABORT, FEEDBACK_SUCCEED, WAIT_FOR_CANCEL, DELAY_ACCEPT};

class FakeNavigateToPoseServer
{
public:
  using Action = nav2_msgs::action::NavigateToPose;
  using GoalHandle = rclcpp_action::ServerGoalHandle<Action>;

  explicit FakeNavigateToPoseServer(ServerMode mode)
  : mode_(mode), node_(std::make_shared<rclcpp::Node>("fake_navigate_to_pose_server"))
  {
    server_ = rclcpp_action::create_server<Action>(
      node_, "navigate_to_pose",
      [this](const rclcpp_action::GoalUUID &, std::shared_ptr<const Action::Goal> goal) {
        ++goal_count_;
        captured_goal_ = *goal;
        if (mode_ == ServerMode::DELAY_ACCEPT) {
          std::this_thread::sleep_for(250ms);
        }
        return mode_ == ServerMode::REJECT ?
               rclcpp_action::GoalResponse::REJECT :
               rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
      },
      [this](const std::shared_ptr<GoalHandle>) {
        cancel_received_.store(true);
        return rclcpp_action::CancelResponse::ACCEPT;
      },
      [this](const std::shared_ptr<GoalHandle> goal_handle) {
        accepted_.store(true);
        worker_ = std::thread([this, goal_handle]() {execute(goal_handle);});
      });
    executor_.add_node(node_);
    spin_thread_ = std::thread([this]() {executor_.spin();});
  }

  ~FakeNavigateToPoseServer()
  {
    executor_.cancel();
    if (spin_thread_.joinable()) {
      spin_thread_.join();
    }
    if (worker_.joinable()) {
      worker_.join();
    }
  }

  int goal_count() const {return goal_count_.load();}
  bool accepted() const {return accepted_.load();}
  bool cancel_received() const {return cancel_received_.load();}
  Action::Goal captured_goal() const {return captured_goal_;}

private:
  void execute(const std::shared_ptr<GoalHandle> goal_handle)
  {
    if (mode_ == ServerMode::FEEDBACK_SUCCEED) {
      std::this_thread::sleep_for(30ms);
      auto feedback = std::make_shared<Action::Feedback>();
      feedback->distance_remaining = 3.25;
      feedback->number_of_recoveries = 2;
      goal_handle->publish_feedback(feedback);
      std::this_thread::sleep_for(30ms);
    }
    if (mode_ == ServerMode::WAIT_FOR_CANCEL || mode_ == ServerMode::DELAY_ACCEPT) {
      const auto deadline = std::chrono::steady_clock::now() + 2s;
      while (!goal_handle->is_canceling() && std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(10ms);
      }
      if (goal_handle->is_canceling()) {
        auto result = std::make_shared<Action::Result>();
        result->error_code = 0;
        result->error_msg = "canceled by test";
        goal_handle->canceled(result);
      }
      return;
    }
    std::this_thread::sleep_for(30ms);
    auto result = std::make_shared<Action::Result>();
    if (mode_ == ServerMode::ABORT) {
      result->error_code = 42;
      result->error_msg = "planner test failure";
      goal_handle->abort(result);
    } else {
      result->error_code = 0;
      goal_handle->succeed(result);
    }
  }

  ServerMode mode_;
  rclcpp::Node::SharedPtr node_;
  rclcpp_action::Server<Action>::SharedPtr server_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  std::thread spin_thread_;
  std::thread worker_;
  std::atomic<int> goal_count_{0};
  std::atomic<bool> accepted_{false};
  std::atomic<bool> cancel_received_{false};
  Action::Goal captured_goal_;
};

class NavigateToStationTest : public ::testing::Test
{
protected:
  static void SetUpTestSuite()
  {
    rclcpp::init(0, nullptr, rclcpp::InitOptions(), rclcpp::SignalHandlerOptions::None);
  }

  static void TearDownTestSuite()
  {
    rclcpp::shutdown();
  }

  ApplicationConfig fast_config() const
  {
    ApplicationConfig config;
    config.server_wait_timeout = 500ms;
    config.cancellation_timeout = 1s;
    config.feedback_period = 1ms;
    return config;
  }

  int run(
    const std::string & catalog, std::atomic_bool & cancel,
    std::ostream & output, std::ostream & error,
    const ApplicationConfig & config = ApplicationConfig{})
  {
    CliOptions options;
    options.station_id = "station_A";
    options.catalog_path = catalog;
    return run_navigate_to_station(
      options, [&cancel]() {return cancel.load();}, output, error, config);
  }
};

TEST(NavigateToStationCli, ParsesRequiredArgumentsAndRejectsInvalidForms)
{
  const auto valid = parse_cli_arguments(
    {"navigate_to_station", "--station", "station_A", "--catalog", "/tmp/stations.yaml"});
  ASSERT_TRUE(valid.valid);
  EXPECT_EQ(valid.options.station_id, "station_A");
  EXPECT_EQ(valid.options.catalog_path, "/tmp/stations.yaml");

  for (const auto & args : std::vector<std::vector<std::string>>{
        {"navigate_to_station", "station_A"},
        {"navigate_to_station", "--unknown"},
        {"navigate_to_station", "--station"},
        {"navigate_to_station", "--station", "station_A", "--station", "station_B",
          "--catalog", "/tmp/a"},
        {"navigate_to_station", "--station", "station_A", "--catalog", "/tmp/a",
          "--catalog", "/tmp/b"},
        {"navigate_to_station", "--station", "", "--catalog", "/tmp/a"}})
  {
    EXPECT_FALSE(parse_cli_arguments(args).valid);
  }
  const auto help = parse_cli_arguments({"navigate_to_station", "--help"});
  EXPECT_TRUE(help.valid);
  EXPECT_TRUE(help.options.help);
}

TEST(NavigateToStationCli, ExecutableAcceptsValidRosArguments)
{
  const std::string command =
    std::string(NAVIGATE_TO_STATION_EXECUTABLE) + " --help --ros-args --log-level warn";
  const int status = std::system(command.c_str());
  ASSERT_TRUE(WIFEXITED(status));
  EXPECT_EQ(WEXITSTATUS(status), 0);
}

TEST(NavigateToStationCli, ExecutableMapsInvalidCliToExitTwo)
{
  const std::string command =
    std::string(NAVIGATE_TO_STATION_EXECUTABLE) + " --unknown >/dev/null 2>&1";
  const int status = std::system(command.c_str());
  ASSERT_TRUE(WIFEXITED(status));
  EXPECT_EQ(WEXITSTATUS(status), 2);
}

TEST_F(NavigateToStationTest, SendsExactlyOneCanonicalNativeGoalAndSucceeds)
{
  TemporaryCatalog catalog(kValidCatalog);
  FakeNavigateToPoseServer server(ServerMode::SUCCEED);
  std::atomic_bool cancel{false};
  std::ostringstream output;
  std::ostringstream error;

  const auto before_submission = rclcpp::Clock().now();
  EXPECT_EQ(run(catalog.path(), cancel, output, error, fast_config()), 0);
  const auto after_result = rclcpp::Clock().now();
  ASSERT_EQ(server.goal_count(), 1);
  const auto goal = server.captured_goal();
  EXPECT_EQ(goal.pose.header.frame_id, "map");
  EXPECT_NE(goal.pose.header.stamp.sec, 0);
  EXPECT_GE(rclcpp::Time(goal.pose.header.stamp).nanoseconds(), before_submission.nanoseconds());
  EXPECT_LE(rclcpp::Time(goal.pose.header.stamp).nanoseconds(), after_result.nanoseconds());
  EXPECT_DOUBLE_EQ(goal.pose.pose.position.x, 2.5);
  EXPECT_DOUBLE_EQ(goal.pose.pose.position.y, -1.25);
  EXPECT_NEAR(goal.pose.pose.orientation.z, std::sqrt(0.5), 1e-12);
  EXPECT_NEAR(goal.pose.pose.orientation.w, std::sqrt(0.5), 1e-12);
  EXPECT_NEAR(
    std::hypot(goal.pose.pose.orientation.z, goal.pose.pose.orientation.w), 1.0, 1e-12);
  EXPECT_TRUE(goal.behavior_tree.empty());
  EXPECT_NE(output.str().find("NAV_SUCCEEDED"), std::string::npos);
  EXPECT_TRUE(error.str().empty());
}

TEST_F(NavigateToStationTest, UnknownStationAndMalformedCatalogSendNoGoal)
{
  FakeNavigateToPoseServer server(ServerMode::SUCCEED);
  TemporaryCatalog valid_catalog(kValidCatalog);
  TemporaryCatalog malformed_catalog("frame_id: map\nstations: [\n");
  std::atomic_bool cancel{false};
  std::ostringstream output;
  std::ostringstream error;
  CliOptions unknown{"unknown", valid_catalog.path(), false};

  EXPECT_EQ(
    run_navigate_to_station(
      unknown, [&cancel]() {return cancel.load();}, output, error, fast_config()), 3);
  EXPECT_EQ(run(malformed_catalog.path(), cancel, output, error, fast_config()), 3);
  EXPECT_EQ(server.goal_count(), 0);
  EXPECT_NE(error.str().find("RESOLUTION_FAILED"), std::string::npos);
}

TEST_F(NavigateToStationTest, ReturnsUnavailableAndRejectedExitCodes)
{
  TemporaryCatalog catalog(kValidCatalog);
  std::atomic_bool cancel{false};
  std::ostringstream output;
  std::ostringstream error;
  auto unavailable = fast_config();
  unavailable.server_wait_timeout = 100ms;
  EXPECT_EQ(run(catalog.path(), cancel, output, error, unavailable), 4);
  EXPECT_NE(error.str().find("NAV2_UNAVAILABLE"), std::string::npos);

  output.str("");
  error.str("");
  FakeNavigateToPoseServer server(ServerMode::REJECT);
  EXPECT_EQ(run(catalog.path(), cancel, output, error, fast_config()), 4);
  EXPECT_EQ(server.goal_count(), 1);
  EXPECT_NE(error.str().find("GOAL_REJECTED"), std::string::npos);
}

TEST_F(NavigateToStationTest, PreservesNativeAbortAndPrintsFeedback)
{
  TemporaryCatalog catalog(kValidCatalog);
  std::atomic_bool cancel{false};
  std::ostringstream output;
  std::ostringstream error;
  {
    FakeNavigateToPoseServer server(ServerMode::ABORT);
    EXPECT_EQ(run(catalog.path(), cancel, output, error, fast_config()), 5);
  }
  EXPECT_NE(error.str().find("error_code=42"), std::string::npos);
  EXPECT_NE(error.str().find("planner test failure"), std::string::npos);

  output.str("");
  error.str("");
  {
    FakeNavigateToPoseServer server(ServerMode::FEEDBACK_SUCCEED);
    EXPECT_EQ(run(catalog.path(), cancel, output, error, fast_config()), 0);
  }
  EXPECT_NE(output.str().find("NAV_FEEDBACK"), std::string::npos);
  EXPECT_NE(output.str().find("distance_remaining=3.25"), std::string::npos);
}

TEST_F(NavigateToStationTest, CancelsOnlyAcceptedOwnedGoal)
{
  TemporaryCatalog catalog(kValidCatalog);
  FakeNavigateToPoseServer server(ServerMode::WAIT_FOR_CANCEL);
  std::atomic_bool cancel{false};
  std::thread interrupter([&server, &cancel]() {
      while (!server.accepted()) {
        std::this_thread::sleep_for(5ms);
      }
      cancel.store(true);
    });
  std::ostringstream output;
  std::ostringstream error;
  EXPECT_EQ(run(catalog.path(), cancel, output, error, fast_config()), 130);
  interrupter.join();
  EXPECT_EQ(server.goal_count(), 1);
  EXPECT_TRUE(server.cancel_received());
  EXPECT_NE(output.str().find("NAV_CANCELED"), std::string::npos);
}

TEST_F(NavigateToStationTest, CancelsGoalAfterDelayedAcceptanceWithoutHanging)
{
  TemporaryCatalog catalog(kValidCatalog);
  FakeNavigateToPoseServer server(ServerMode::DELAY_ACCEPT);
  std::atomic_bool cancel{false};
  std::thread interrupter([&cancel]() {
      std::this_thread::sleep_for(50ms);
      cancel.store(true);
    });
  std::ostringstream output;
  std::ostringstream error;
  const auto start = std::chrono::steady_clock::now();
  EXPECT_EQ(run(catalog.path(), cancel, output, error, fast_config()), 130);
  EXPECT_LT(std::chrono::steady_clock::now() - start, 2s);
  interrupter.join();
  EXPECT_EQ(server.goal_count(), 1);
  EXPECT_TRUE(server.cancel_received());
}

}  // namespace
}  // namespace mobile_base_navigation
