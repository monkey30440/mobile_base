cmake_minimum_required(VERSION 3.8)
project(mobile_base_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE
  PATTERN "*.pyc" EXCLUDE
)

install(
  PROGRAMS scripts/save_map.sh
  DESTINATION lib/${PROJECT_NAME}
)

install(
  FILES
    MAPPING.md
    NAVIGATION.md
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_mapping_bringup test/test_mapping_bringup.py)
  ament_add_pytest_test(test_navigation_bringup test/test_navigation_bringup.py)
  ament_add_pytest_test(test_kinematic_icp_bringup test/test_kinematic_icp_bringup.py)
  ament_add_pytest_test(test_feedback_odometry_chain test/test_feedback_odometry_chain.py)
  ament_add_pytest_test(test_perception_dataflow test/test_perception_dataflow.py)
  ament_add_pytest_test(test_tf_authority test/test_tf_authority.py)
  ament_add_pytest_test(test_save_map test/test_save_map.py)
endif()

ament_package()
