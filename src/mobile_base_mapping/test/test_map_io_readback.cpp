// Copyright 2026 Antigravity Team.
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

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include <nav2_map_server/map_io.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>

namespace fs = std::filesystem;

class MapIOReadbackTest : public ::testing::Test
{
protected:
  void SetUp() override
  {
    temp_dir_ = fs::temp_directory_path() / "test_map_io_readback_dir";
    fs::create_directories(temp_dir_);

    // 1. Create a valid 10x10 PGM (P5 format)
    valid_pgm_path_ = temp_dir_ / "test_map.pgm";
    std::ofstream pgm_out(valid_pgm_path_, std::ios::binary);
    std::string pgm_header = "P5\n10 10\n255\n";
    pgm_out.write(pgm_header.data(), pgm_header.size());
    // 254 = free space
    std::vector<uint8_t> pixels(100, 254);
    pgm_out.write(reinterpret_cast<const char *>(pixels.data()), pixels.size());
    pgm_out.close();

    // 2. Create matching valid map.yaml (SYS-001 / SYS-024 contract: 0.05m resolution)
    valid_yaml_path_ = temp_dir_ / "test_map.yaml";
    std::ofstream yaml_out(valid_yaml_path_);
    yaml_out << "image: test_map.pgm\n";
    yaml_out << "mode: trinary\n";
    yaml_out << "resolution: 0.05\n";
    yaml_out << "origin: [0.0, 0.0, 0.0]\n";
    yaml_out << "negate: 0\n";
    yaml_out << "occupied_thresh: 0.65\n";
    yaml_out << "free_thresh: 0.25\n";
    yaml_out.close();

    // 3. Create YAML referencing a missing image file
    invalid_img_yaml_path_ = temp_dir_ / "missing_img.yaml";
    std::ofstream missing_img_yaml_out(invalid_img_yaml_path_);
    missing_img_yaml_out << "image: non_existent_image.pgm\n";
    missing_img_yaml_out << "mode: trinary\n";
    missing_img_yaml_out << "resolution: 0.05\n";
    missing_img_yaml_out << "origin: [0.0, 0.0, 0.0]\n";
    missing_img_yaml_out << "negate: 0\n";
    missing_img_yaml_out << "occupied_thresh: 0.65\n";
    missing_img_yaml_out << "free_thresh: 0.25\n";
    missing_img_yaml_out.close();
  }

  void TearDown() override
  {
    if (fs::exists(temp_dir_)) {
      fs::remove_all(temp_dir_);
    }
  }

  fs::path temp_dir_;
  fs::path valid_pgm_path_;
  fs::path valid_yaml_path_;
  fs::path invalid_img_yaml_path_;
};

TEST_F(MapIOReadbackTest, ValidMapPackageReadback)
{
  nav_msgs::msg::OccupancyGrid map_msg;
  auto status = nav2_map_server::loadMapFromYaml(valid_yaml_path_.string(), map_msg);

  EXPECT_EQ(status, nav2_map_server::LOAD_MAP_STATUS::LOAD_MAP_SUCCESS);
  EXPECT_FLOAT_EQ(map_msg.info.resolution, 0.05f);
  EXPECT_EQ(map_msg.info.width, 10u);
  EXPECT_EQ(map_msg.info.height, 10u);
  EXPECT_EQ(map_msg.data.size(), 100u);
}

TEST_F(MapIOReadbackTest, EmptyPathFailure)
{
  nav_msgs::msg::OccupancyGrid map_msg;
  auto status = nav2_map_server::loadMapFromYaml("", map_msg);

  EXPECT_EQ(status, nav2_map_server::LOAD_MAP_STATUS::MAP_DOES_NOT_EXIST);
}

TEST_F(MapIOReadbackTest, NonExistentYamlFailure)
{
  nav_msgs::msg::OccupancyGrid map_msg;
  auto status = nav2_map_server::loadMapFromYaml("/non/existent/path/map.yaml", map_msg);

  EXPECT_EQ(status, nav2_map_server::LOAD_MAP_STATUS::INVALID_MAP_METADATA);
}

TEST_F(MapIOReadbackTest, MissingReferencedImageFailure)
{
  nav_msgs::msg::OccupancyGrid map_msg;
  auto status = nav2_map_server::loadMapFromYaml(invalid_img_yaml_path_.string(), map_msg);

  EXPECT_EQ(status, nav2_map_server::LOAD_MAP_STATUS::INVALID_MAP_DATA);
}
