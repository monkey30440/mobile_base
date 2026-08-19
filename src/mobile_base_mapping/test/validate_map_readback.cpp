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

#include <iostream>
#include <string>

#include <nav2_map_server/map_io.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>

int main(int argc, char ** argv)
{
  if (argc < 2) {
    std::cerr << "Usage: validate_map_readback <path_to_map_yaml>\n";
    return 1;
  }

  std::string yaml_path = argv[1];
  nav_msgs::msg::OccupancyGrid map_msg;
  auto status = nav2_map_server::loadMapFromYaml(yaml_path, map_msg);

  if (status == nav2_map_server::LOAD_MAP_STATUS::LOAD_MAP_SUCCESS) {
    std::cout << "STATUS: LOAD_MAP_SUCCESS\n";
    std::cout << "RESOLUTION: " << map_msg.info.resolution << "\n";
    std::cout << "WIDTH: " << map_msg.info.width << "\n";
    std::cout << "HEIGHT: " << map_msg.info.height << "\n";
    std::cout << "DATA_SIZE: " << map_msg.data.size() << "\n";
    std::cout << "ORIGIN_X: " << map_msg.info.origin.position.x << "\n";
    std::cout << "ORIGIN_Y: " << map_msg.info.origin.position.y << "\n";
    return 0;
  } else {
    std::cerr << "STATUS_CODE: " << static_cast<int>(status) << "\n";
    return 2;
  }
}
