cmake_minimum_required(VERSION 3.8)
project(mobile_base_navigation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(yaml_cpp_vendor REQUIRED)
find_package(yaml-cpp REQUIRED)

# Target admission library
add_library(target_admission_lib
  src/target_admission.cpp
)
target_include_directories(target_admission_lib PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
ament_target_dependencies(target_admission_lib
  rclcpp
  geometry_msgs
)
target_link_libraries(target_admission_lib
  yaml-cpp
)

# One-shot Station ID navigation application
add_library(navigate_to_station_app_lib
  src/navigate_to_station_app.cpp
)
target_include_directories(navigate_to_station_app_lib PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
)
target_link_libraries(navigate_to_station_app_lib
  target_admission_lib
)
ament_target_dependencies(navigate_to_station_app_lib
  rclcpp
  rclcpp_action
  geometry_msgs
  nav2_msgs
)

add_executable(navigate_to_station
  src/navigate_to_station_main.cpp
)
target_include_directories(navigate_to_station PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
)
target_link_libraries(navigate_to_station
  navigate_to_station_app_lib
)
ament_target_dependencies(navigate_to_station
  rclcpp
)

# Install libraries and headers
install(
  TARGETS target_admission_lib
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(
  TARGETS navigate_to_station
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY include/
  DESTINATION include
)

# Install launch, config, and behavior_trees
install(
  DIRECTORY config behavior_trees launch
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_target_admission
    test/test_target_admission.cpp
  )
  target_compile_definitions(test_target_admission PRIVATE
    TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test/test_data"
  )
  target_link_libraries(test_target_admission
    target_admission_lib
    yaml-cpp
  )
  ament_target_dependencies(test_target_admission
    rclcpp
    geometry_msgs
  )

  ament_add_gtest(test_navigate_to_station
    test/test_navigate_to_station.cpp
  )
  target_include_directories(test_navigate_to_station PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
  )
  target_compile_definitions(test_navigate_to_station PRIVATE
    NAVIGATE_TO_STATION_EXECUTABLE="$<TARGET_FILE:navigate_to_station>"
  )
  target_link_libraries(test_navigate_to_station
    navigate_to_station_app_lib
    target_admission_lib
  )
  ament_target_dependencies(test_navigate_to_station
    rclcpp
    rclcpp_action
    geometry_msgs
    nav2_msgs
  )

  find_package(behaviortree_cpp REQUIRED)
  find_package(nav_msgs REQUIRED)
  find_package(nav2_route REQUIRED)
  find_package(nav2_util REQUIRED)
  ament_add_gtest(test_behavior_tree_runtime
    test/test_behavior_tree_runtime.cpp
  )
  target_include_directories(test_behavior_tree_runtime PRIVATE
    /opt/ros/jazzy/include/nav2_route
  )
  target_compile_definitions(test_behavior_tree_runtime PRIVATE
    BT_XML_PATH="${CMAKE_CURRENT_SOURCE_DIR}/behavior_trees/route_assisted_nav.xml"
    REAL_ROUTE_GRAPH_PATH="${CMAKE_CURRENT_SOURCE_DIR}/../../maps/test_site/route_graph.geojson"
  )
  ament_target_dependencies(test_behavior_tree_runtime
    rclcpp
    behaviortree_cpp
    nav_msgs
    geometry_msgs
    nav2_route
    nav2_util
  )

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_navigation_launch
    test/test_navigation_launch.py
  )
  ament_add_pytest_test(test_apriltag_docking_integration
    test/test_apriltag_docking_integration.py
    TIMEOUT 60
  )
endif()

ament_export_include_directories(include)
ament_export_libraries(target_admission_lib)
ament_export_targets(export_${PROJECT_NAME})
ament_export_dependencies(rclcpp geometry_msgs)

ament_package()
