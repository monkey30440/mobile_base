cmake_minimum_required(VERSION 3.8)
project(mobile_base_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(MODBUS REQUIRED libmodbus)

add_library(m1_driver
  src/m1_driver.cpp
  src/m1_control_check_core.cpp
)

target_include_directories(m1_driver PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${MODBUS_INCLUDE_DIRS}
)

target_link_libraries(m1_driver PUBLIC
  ${MODBUS_LIBRARIES}
)

target_compile_features(m1_driver PUBLIC cxx_std_17)

# Level 2 Hardware Read-Only Verification Utility
add_executable(m1_l2_read_check
  src/m1_l2_read_check.cpp
)
target_link_libraries(m1_l2_read_check m1_driver)
target_compile_features(m1_l2_read_check PUBLIC cxx_std_17)

# Level 3/4 Controlled Write Validation Harness
add_executable(m1_control_check
  src/m1_control_check_main.cpp
)
target_link_libraries(m1_control_check m1_driver)
target_compile_features(m1_control_check PUBLIC cxx_std_17)

# Install rules
install(
  TARGETS m1_driver m1_l2_read_check m1_control_check
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY include/
  DESTINATION include
)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  ament_add_gtest(test_m1_driver test/test_m1_driver.cpp)
  target_link_libraries(test_m1_driver m1_driver)

  ament_add_gtest(test_m1_control_check test/test_m1_control_check.cpp)
  target_link_libraries(test_m1_control_check m1_driver)
endif()

ament_export_include_directories(include)
ament_export_libraries(m1_driver)
ament_export_targets(export_${PROJECT_NAME})

ament_package()
