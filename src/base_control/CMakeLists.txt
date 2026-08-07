cmake_minimum_required(VERSION 3.16)
project(base_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(diagnostic_msgs REQUIRED)

find_package(PkgConfig REQUIRED)
pkg_check_modules(MODBUS REQUIRED IMPORTED_TARGET libmodbus)

add_library(base_control SHARED
  src/md2_transport.cpp
  src/driver_interface.cpp
  src/base_control_hardware.cpp
)

target_compile_features(base_control PUBLIC cxx_std_17)

target_include_directories(base_control PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

target_link_libraries(base_control PUBLIC PkgConfig::MODBUS)

ament_target_dependencies(base_control PUBLIC
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
  diagnostic_msgs
)

pluginlib_export_plugin_description_file(hardware_interface base_control_plugin.xml)

install(
  DIRECTORY include/
  DESTINATION include
)
install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)
install(
  TARGETS base_control
  EXPORT export_base_control
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

ament_export_targets(export_base_control HAS_LIBRARY_TARGET)
ament_export_dependencies(
  hardware_interface pluginlib rclcpp rclcpp_lifecycle diagnostic_msgs)

ament_package()
