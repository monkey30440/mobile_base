cmake_minimum_required(VERSION 3.8)
project(mobile_base_localization)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(nav2_amcl REQUIRED)
find_package(nav2_map_server REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(OpenCV REQUIRED)

add_library(localization_monitor_lib
  src/localization_monitor.cpp
)
target_include_directories(localization_monitor_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${OpenCV_INCLUDE_DIRS}
)
ament_target_dependencies(localization_monitor_lib
  rclcpp
  nav_msgs
  sensor_msgs
  geometry_msgs
  std_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
)
target_link_libraries(localization_monitor_lib
  ${OpenCV_LIBRARIES}
)

add_executable(localization_monitor
  src/localization_monitor_main.cpp
)
target_link_libraries(localization_monitor
  localization_monitor_lib
)

# Install directories and targets
install(
  TARGETS localization_monitor localization_monitor_lib
  DESTINATION lib/${PROJECT_NAME}
)
install(
  DIRECTORY include/
  DESTINATION include/${PROJECT_NAME}
)
install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_localization_monitor test/test_localization_monitor.cpp)
  target_link_libraries(test_localization_monitor
    localization_monitor_lib
  )

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_localization_launch test/test_localization_launch.py)
endif()

ament_package()
