// Copyright 2026 mobile_base contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <iostream>
#include <iomanip>
#include <string>

#include "mobile_base_control/m1_driver.hpp"

using mobile_base_control::ErrorCode;
using mobile_base_control::M1Driver;
using mobile_base_control::error_code_to_string;

int main(int argc, char ** argv)
{
  std::string device = "/dev/ttyUSB0";
  int baud = 230400;

  if (argc > 1) {
    device = argv[1];
  }
  if (argc > 2) {
    baud = std::stoi(argv[2]);
  }

  std::cout << "========================================" << std::endl;
  std::cout << "M1Driver Level 2 Read-Only Hardware Check" << std::endl;
  std::cout << "Target Device: " << device << " @ " << baud << " bps (8N1)" << std::endl;
  std::cout << "Safety Level: Level 2 (Hardware communication / no motion)" << std::endl;
  std::cout << "========================================" << std::endl;

  M1Driver driver;

  // 1. Connect
  std::cout << "\n[Step 1] Connecting to M1 serial bus..." << std::endl;
  auto conn_res = driver.connect(device, baud, 'N', 8, 1, 100);
  if (!conn_res.ok) {
    std::cerr << "FAIL: Connection failed with error: "
              << error_code_to_string(conn_res.error) << std::endl;
    return 1;
  }
  std::cout << "PASS: Connected to " << device << std::endl;

  // 2. Standard Modbus FC03 Single Register Reads
  std::cout << "\n[Step 2] Reading static configuration registers via Standard Modbus FC03..."
            << std::endl;

  // Read 02-14 (0x020D) position format on ID 1 and ID 2
  auto reg_fmt1 = driver.read_register(1, 0x020D);
  auto reg_fmt2 = driver.read_register(2, 0x020D);
  if (!reg_fmt1.ok || !reg_fmt2.ok) {
    std::cerr << "FAIL: Failed to read position format register 02-14."
              << " ID1 err=" << error_code_to_string(reg_fmt1.error)
              << " ID2 err=" << error_code_to_string(reg_fmt2.error) << std::endl;
    driver.disconnect();
    return 2;
  }
  std::cout << "ID 1 (Right): Reg 02-14 (Position Format) = " << reg_fmt1.value << std::endl;
  std::cout << "ID 2 (Left) : Reg 02-14 (Position Format) = " << reg_fmt2.value << std::endl;

  // Read 09-26 (0x0919) Multi-drive 2.0 mapping on ID 1 and ID 2
  auto reg_map1 = driver.read_register(1, 0x0919);
  auto reg_map2 = driver.read_register(2, 0x0919);
  if (!reg_map1.ok || !reg_map2.ok) {
    std::cerr << "FAIL: Failed to read 09-26 mapping."
              << " ID1 err=" << error_code_to_string(reg_map1.error)
              << " ID2 err=" << error_code_to_string(reg_map2.error) << std::endl;
    driver.disconnect();
    return 3;
  }
  std::cout << "ID 1 (Right): Reg 09-26 (MD2 Mapping)     = " << reg_map1.value << std::endl;
  std::cout << "ID 2 (Left) : Reg 09-26 (MD2 Mapping)     = " << reg_map2.value << std::endl;

  // 3. Multi-drive 2.0 FC03 State Read
  std::cout << "\n[Step 3] Executing Multi-drive 2.0 FC03 dual-driver read_state(1, 2)..."
            << std::endl;
  auto state_res = driver.read_state(1, 2);
  if (!state_res.ok) {
    std::cerr << "FAIL: Multi-drive 2.0 read_state failed with error: "
              << error_code_to_string(state_res.error) << std::endl;
    driver.disconnect();
    return 4;
  }

  const auto & states = state_res.value.states;
  for (size_t i = 0; i < 2; ++i) {
    const auto & st = states[i];
    std::cout << "Driver ID " << st.driver_id << ":" << std::endl;
    std::cout << "  Status        : " << st.status << std::endl;
    std::cout << "  Alarm         : " << st.alarm << std::endl;
    std::cout << "  Actual RPM    : " << st.actual_rpm << " RPM" << std::endl;
    std::cout << "  Bus Voltage   : " << std::fixed << std::setprecision(2)
              << (st.bus_voltage_raw / 100.0) << " V" << std::endl;
    std::cout << "  Current       : " << std::fixed << std::setprecision(2)
              << (st.current_raw / 100.0) << " A" << std::endl;
    std::cout << "  Position Steps: " << st.position_steps << " steps" << std::endl;
    std::cout << "  Error Check   : 0x" << std::hex << std::setw(4) << std::setfill('0')
              << st.error_check << std::dec << std::endl;
  }

  // 4. Negative Test: Timeout on non-existent driver ID 99
  std::cout << "\n[Step 4] Negative fault-injection test: read non-existent slave ID 99..."
            << std::endl;
  auto neg_res = driver.read_register(99, 0x020D);
  if (!neg_res.ok && neg_res.error == ErrorCode::TIMEOUT) {
    std::cout << "PASS: Correctly timed out with error "
              << error_code_to_string(neg_res.error) << std::endl;
  } else {
    std::cerr << "UNEXPECTED: Expected TIMEOUT on slave 99, got ok="
              << neg_res.ok << " error=" << error_code_to_string(neg_res.error) << std::endl;
    driver.disconnect();
    return 5;
  }

  // 5. Clean Disconnect
  std::cout << "\n[Step 5] Disconnecting cleanly..." << std::endl;
  driver.disconnect();
  std::cout << "PASS: Disconnected. Driver is_connected = "
            << std::boolalpha << driver.is_connected() << std::endl;

  std::cout << "\n========================================" << std::endl;
  std::cout << "ALL LEVEL 2 READ-ONLY CHECKS PASSED (NO MOTION COMMANDS ISSUED)" << std::endl;
  std::cout << "========================================" << std::endl;
  return 0;
}
