cmake_minimum_required(VERSION 3.8)
project(mobile_base_mapping)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav2_map_server REQUIRED)

add_executable(validate_map_readback test/validate_map_readback.cpp)
target_include_directories(validate_map_readback PRIVATE ${nav2_map_server_INCLUDE_DIRS})
target_link_libraries(validate_map_readback ${nav2_map_server_LIBRARIES} nav_msgs::nav_msgs__rosidl_typesupport_cpp)

# Install directories
install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  TARGETS validate_map_readback
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_mapping_launch_syntax test/test_mapping_launch_syntax.py)

  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_map_io_readback test/test_map_io_readback.cpp)
  target_include_directories(test_map_io_readback PRIVATE ${nav2_map_server_INCLUDE_DIRS})
  target_link_libraries(test_map_io_readback ${nav2_map_server_LIBRARIES} nav_msgs::nav_msgs__rosidl_typesupport_cpp)

endif()

ament_package()
