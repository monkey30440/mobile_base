cmake_minimum_required(VERSION 3.8)
project(mobile_base_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(controller_interface REQUIRED)
find_package(controller_manager REQUIRED)
find_package(diff_drive_controller REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(MODBUS REQUIRED libmodbus)

# m1_driver library (transport layer)
add_library(m1_driver SHARED
  src/m1_driver.cpp
  src/m1_control_check_core.cpp
)
set_target_properties(m1_driver PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(m1_driver PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
  ${MODBUS_INCLUDE_DIRS}
)
target_link_libraries(m1_driver PUBLIC
  ${MODBUS_LIBRARIES}
)
target_compile_features(m1_driver PUBLIC cxx_std_17)

# m1_hardware library (ros2_control SystemInterface plugin)
add_library(m1_hardware SHARED
  src/m1_hardware.cpp
)
target_include_directories(m1_hardware PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_link_libraries(m1_hardware PUBLIC
  m1_driver
  hardware_interface::hardware_interface
  pluginlib::pluginlib
  rclcpp::rclcpp
  rclcpp_lifecycle::rclcpp_lifecycle
)
target_compile_features(m1_hardware PUBLIC cxx_std_17)
pluginlib_export_plugin_description_file(hardware_interface m1_hardware_plugins.xml)

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

# Level 2 Read-Only Latency Measurement Tool
add_executable(m1_latency_check
  src/m1_latency_check_main.cpp
)
target_link_libraries(m1_latency_check m1_driver)
target_compile_features(m1_latency_check PUBLIC cxx_std_17)

# Level 3 FC17 Zero-Speed Latency Measurement Harness
add_executable(m1_fc17_latency_check
  src/m1_fc17_latency_check_main.cpp
  src/m1_fc17_latency_check_core.cpp
  src/m1_timing_syscall_interpose.cpp
)
target_link_libraries(m1_fc17_latency_check m1_driver)
target_compile_features(m1_fc17_latency_check PUBLIC cxx_std_17)

# Level 3 Full ros2_control Loop Timing Validation Harness
add_executable(m1_full_loop_timing_check
  src/m1_full_loop_timing_check_main.cpp
  src/m1_full_loop_timing_check_core.cpp
)
target_link_libraries(m1_full_loop_timing_check
  m1_hardware
  m1_driver
  diff_drive_controller::diff_drive_controller
  controller_manager::controller_manager
  controller_interface::controller_interface
  hardware_interface::hardware_interface
  rclcpp::rclcpp
)
target_compile_features(m1_full_loop_timing_check PUBLIC cxx_std_17)

# Level 4 Stage D1 Left Wheel Dynamic Feedback Validation Harness
add_executable(m1_dynamic_stage_d1_check
  src/m1_dynamic_stage_d1_check_main.cpp
  src/m1_dynamic_stage_d1_check_core.cpp
)
target_link_libraries(m1_dynamic_stage_d1_check
  m1_hardware
  m1_driver
  controller_manager::controller_manager
  hardware_interface::hardware_interface
  rclcpp::rclcpp
)
target_compile_features(m1_dynamic_stage_d1_check PUBLIC cxx_std_17)

# Level 4 Stage D2 Right Wheel Dynamic Feedback Validation Harness
add_executable(m1_dynamic_stage_d2_check
  src/m1_dynamic_stage_d2_check_main.cpp
  src/m1_dynamic_stage_d2_check_core.cpp
)
target_link_libraries(m1_dynamic_stage_d2_check
  m1_hardware
  m1_driver
  controller_manager::controller_manager
  hardware_interface::hardware_interface
  rclcpp::rclcpp
)
target_compile_features(m1_dynamic_stage_d2_check PUBLIC cxx_std_17)

# Install rules
install(
  TARGETS
    m1_driver
    m1_hardware
    m1_l2_read_check
    m1_control_check
    m1_latency_check
    m1_fc17_latency_check
    m1_full_loop_timing_check
    m1_dynamic_stage_d1_check
    m1_dynamic_stage_d2_check
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY include/
  DESTINATION include
)

install(
  DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
)

install(
  DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

install(
  FILES m1_hardware_plugins.xml
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  ament_add_gtest(test_m1_driver
    test/test_m1_driver.cpp
    src/m1_timing_syscall_interpose.cpp
  )
  target_link_libraries(test_m1_driver m1_driver)

  ament_add_gtest(test_m1_control_check
    test/test_m1_control_check.cpp
  )
  target_link_libraries(test_m1_control_check m1_driver)

  ament_add_gtest(test_m1_latency_stats
    test/test_m1_latency_stats.cpp
  )
  target_link_libraries(test_m1_latency_stats m1_driver)

  ament_add_gtest(test_m1_fc17_latency_check
    test/test_m1_fc17_latency_check.cpp
    src/m1_fc17_latency_check_core.cpp
  )
  target_link_libraries(test_m1_fc17_latency_check m1_driver)

  ament_add_gtest(test_m1_full_loop_timing_check
    test/test_m1_full_loop_timing_check.cpp
    src/m1_full_loop_timing_check_core.cpp
  )
  target_link_libraries(test_m1_full_loop_timing_check
    m1_hardware
    m1_driver
    diff_drive_controller::diff_drive_controller
    controller_manager::controller_manager
    controller_interface::controller_interface
    hardware_interface::hardware_interface
    rclcpp::rclcpp
  )

  ament_add_gtest(test_m1_dynamic_stage_d1_check
    test/test_m1_dynamic_stage_d1_check.cpp
    src/m1_dynamic_stage_d1_check_core.cpp
  )
  target_link_libraries(test_m1_dynamic_stage_d1_check
    m1_hardware
    m1_driver
    controller_manager::controller_manager
    hardware_interface::hardware_interface
    rclcpp::rclcpp
  )

  ament_add_gtest(test_m1_dynamic_stage_d2_check
    test/test_m1_dynamic_stage_d2_check.cpp
    src/m1_dynamic_stage_d2_check_core.cpp
  )
  target_link_libraries(test_m1_dynamic_stage_d2_check
    m1_hardware
    m1_driver
    controller_manager::controller_manager
    hardware_interface::hardware_interface
    rclcpp::rclcpp
  )

  ament_add_gtest(test_m1_hardware
    test/test_m1_hardware.cpp
  )
  target_link_libraries(test_m1_hardware
    m1_hardware
    m1_driver
    hardware_interface::hardware_interface
    pluginlib::pluginlib
    rclcpp::rclcpp
    rclcpp_lifecycle::rclcpp_lifecycle
    controller_manager::controller_manager
    diff_drive_controller::diff_drive_controller
    geometry_msgs::geometry_msgs__rosidl_generator_cpp
  )
endif()

ament_export_include_directories(include)
ament_export_libraries(m1_driver m1_hardware)
ament_export_targets(export_${PROJECT_NAME})
ament_export_dependencies(
  controller_interface
  controller_manager
  diff_drive_controller
  geometry_msgs
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
)
ament_package()
