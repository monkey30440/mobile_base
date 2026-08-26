cmake_minimum_required(VERSION 3.8)
project(mobile_base_state_estimation)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)

# Install directories
install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_ekf_launch_syntax test/test_ekf_launch_syntax.py)
  ament_add_pytest_test(
    test_kinematic_icp_runtime
    test/test_kinematic_icp_runtime.py
    TIMEOUT 120
  )
endif()

ament_package()
