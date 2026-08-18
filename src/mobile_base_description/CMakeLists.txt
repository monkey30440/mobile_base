cmake_minimum_required(VERSION 3.8)
project(mobile_base_description)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

# Install directories
install(
  DIRECTORY config launch meshes urdf
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_pytest REQUIRED)
  find_package(launch_testing_ament_cmake REQUIRED)

  ament_add_pytest_test(test_urdf_syntax test/test_urdf_syntax.py
    TIMEOUT 60
  )
  ament_add_pytest_test(test_robot_description_launch test/test_robot_description_launch.py
    TIMEOUT 60
  )
endif()

ament_package()
