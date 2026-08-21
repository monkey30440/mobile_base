cmake_minimum_required(VERSION 3.8)
project(mobile_base_navigation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
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

# Install libraries and headers
install(
  TARGETS target_admission_lib
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
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

  find_package(behaviortree_cpp REQUIRED)
  find_package(nav_msgs REQUIRED)
  ament_add_gtest(test_behavior_tree_runtime
    test/test_behavior_tree_runtime.cpp
  )
  target_compile_definitions(test_behavior_tree_runtime PRIVATE
    BT_XML_PATH="${CMAKE_CURRENT_SOURCE_DIR}/behavior_trees/route_assisted_nav.xml"
  )
  ament_target_dependencies(test_behavior_tree_runtime
    rclcpp
    behaviortree_cpp
    nav_msgs
    geometry_msgs
  )

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_navigation_launch
    test/test_navigation_launch.py
  )
endif()

ament_export_include_directories(include)
ament_export_libraries(target_admission_lib)
ament_export_targets(export_${PROJECT_NAME})
ament_export_dependencies(rclcpp geometry_msgs)

ament_package()
