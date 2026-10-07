#include <array>
#include <chrono>
#include <thread>
#include <algorithm>
#include <limits>
#include <mutex>
#include <string>
#include <modbus/modbus.h>
#include <diagnostic_updater/diagnostic_updater.hpp>
#include <hardware_interface/system_interface.hpp>
#include <pluginlib/class_list_macros.hpp>
#include "mobile_base_m1/protocol.hpp"

namespace mobile_base_m1 {
class M1System : public hardware_interface::SystemInterface {
 using CallbackReturn = hardware_interface::CallbackReturn;
 struct Wheel {
  std::string joint; int id; Scale scale; double max_rpm;
  int64_t position_steps; uint16_t encoder_pulses;
  bool position_initialized=false; int64_t last_count=0; double position=0;
  std::chrono::steady_clock::time_point position_time{};
 };
 std::array<Wheel, 2> wheels_;
 modbus_t *bus_ = nullptr;
 std::unique_ptr<diagnostic_updater::Updater> updater_;
 std::mutex diagnostics_mutex_;
 std::string reason_ = "not configured";
 std::array<uint16_t, 2> status_{};
 std::array<uint16_t, 2> alarm_{};
 std::array<uint16_t, 2> error_check_{};
 bool valid_ = false;
 bool connected_ = false;
 bool fault_seen_ = false;
 bool position_fault_ = false;
 std::string position_fault_reason_;
 std::string firmware_;
 std::chrono::microseconds gap_{1750};
 std::chrono::microseconds enable_timeout_{300000};
 std::chrono::microseconds response_timeout_{};
 std::array<uint16_t,2> targets_{};
 std::chrono::steady_clock::time_point last_transaction_end_{};
 void wait_bus_gap() {std::this_thread::sleep_until(last_transaction_end_ + gap_);}
 int address(int index) const {return 0xf000 | (index << 8) | (1 << (wheels_[0].id-1)) | (1 << (wheels_[1].id-1));}
 void context(const std::string &reason, bool valid) {
  std::lock_guard<std::mutex> lock(diagnostics_mutex_); reason_ = reason; valid_ = valid;
 }
 void invalidate() {
  for (const auto &w : wheels_) {
   set_state(w.joint + "/velocity", std::numeric_limits<double>::quiet_NaN());
   set_state(w.joint + "/position", std::numeric_limits<double>::quiet_NaN());
  }
 }
 bool send(const std::array<int16_t, 2> &rpm, MultiDriveCommand command=MultiDriveCommand::Jog) {
  uint16_t data[4];
  const auto first = wheels_[0].id < wheels_[1].id ? 0 : 1;
  data[0]=static_cast<uint16_t>(command); data[1]=static_cast<uint16_t>(rpm[first]);
  data[2]=static_cast<uint16_t>(command); data[3]=static_cast<uint16_t>(rpm[1-first]);
  if(!connected_) return false;
  wait_bus_gap();
  const auto result=modbus_write_registers(bus_, address(8), 4, data);
  last_transaction_end_=std::chrono::steady_clock::now();
  return result==4;
 }
 hardware_interface::return_type fail(const std::string &reason) {
  invalidate(); context(reason, false);
  // Best effort zero on both drives; communication failure cannot prove a physical stop.
  send({0,0},MultiDriveCommand::ImmediateStop);
  RCLCPP_ERROR(get_logger(), "%s", reason.c_str());
  return hardware_interface::return_type::ERROR;
 }
 bool targets_zero() {
  std::array<uint16_t,4> data;
  wait_bus_gap();
  const auto count=modbus_read_registers(bus_,address(12),4,data.data());
  last_transaction_end_=std::chrono::steady_clock::now();
  if(count!=4)throw std::runtime_error("target-speed read failed/timeout");
  validate_error_checks(data,1);
  {std::lock_guard<std::mutex> lock(diagnostics_mutex_);const auto first=wheels_[0].id<wheels_[1].id?0:1;targets_[first]=data[0];targets_[1-first]=data[2];}
  return data[0]==0 && data[2]==0;
 }
 template<typename Words>
 void capture_feedback_snapshot(const Words &data) {
  const auto stride=data.size()/2;
  validate_error_checks(data,stride-1);
  std::lock_guard<std::mutex> lock(diagnostics_mutex_);
  // Capture both drives before conversion/validity checks can throw for either.
  for(size_t i=0;i<2;++i) {
   const auto offset=wheels_[i].id<wheels_[1-i].id?0:stride;
   status_[i]=data[offset];alarm_[i]=data[offset+1];error_check_[i]=data[offset+stride-1];
   if(alarm_[i]!=0 || status_is(status_[i],DriveStatus::Fault))fault_seen_=true;
  }
 }
 bool fresh_alarm_free() {
  std::array<uint16_t,8> data;
  wait_bus_gap();
  const auto count=connected_?modbus_read_registers(bus_,address(0),8,data.data()):-1;
  last_transaction_end_=std::chrono::steady_clock::now();
  if(count!=8)return false;
  try {capture_feedback_snapshot(data);}catch(const std::exception &){return false;}
  std::lock_guard<std::mutex> lock(diagnostics_mutex_);
  return !fault_seen_ && feedback_state_valid(status_[0],alarm_[0]) && feedback_state_valid(status_[1],alarm_[1]);
 }
 struct CleanupResult {bool success; std::string detail;};
 CleanupResult safe_off_cleanup() {
  const auto stop=send({0,0},MultiDriveCommand::ImmediateStop);
  if(!fresh_alarm_free())return {false,"ISTOP requested; SVOFF skipped: fresh no-alarm proof unavailable or fault preserved; deenergization unconfirmed"};
  if(!send({0,0},MultiDriveCommand::ServoOff))return {false,"ISTOP requested; SVOFF failed; deenergization unconfirmed"};
  const auto deadline=std::chrono::steady_clock::now()+enable_timeout_;
  while(std::chrono::steady_clock::now()<deadline) {
   if(!fresh_alarm_free())return {false,"SVOFF acknowledged; fresh state unavailable/fault captured; deenergization unconfirmed"};
   {std::lock_guard<std::mutex> lock(diagnostics_mutex_);if(status_is(status_[0],DriveStatus::Inhibited) && status_is(status_[1],DriveStatus::Inhibited))return {stop,stop?"ISTOP/SVOFF acknowledged; inhibited readback, physical stop unverified":"SVOFF inhibited readback; ISTOP unconfirmed, physical stop unverified"};}
   std::this_thread::sleep_until(std::min(deadline,std::chrono::steady_clock::now()+gap_));
  }
  return {false,"SVOFF acknowledged; inhibited readback timeout, deenergization unconfirmed"};
 }
 CallbackReturn activation_failed(bool servo_attempted) {
  std::string cause; {std::lock_guard<std::mutex> lock(diagnostics_mutex_);cause=reason_;}
  const auto cleanup=servo_attempted?safe_off_cleanup().detail:std::string("servo enable never requested");
  context(cause+"; "+cleanup,false);
  RCLCPP_ERROR(get_logger(),"%s; %s",cause.c_str(),cleanup.c_str());
  return CallbackReturn::ERROR;
 }
 public:
 ~M1System() override {if(bus_) {modbus_close(bus_); modbus_free(bus_);}}
 CallbackReturn on_init(const hardware_interface::HardwareComponentInterfaceParams &params) override {
  if (SystemInterface::on_init(params) != CallbackReturn::SUCCESS) return CallbackReturn::ERROR;
  try {
   const auto &p=info_.hardware_parameters;
   auto required=[&p](const std::string &key) -> std::string { const auto &v=p.at(key); if(v.empty()) throw std::invalid_argument("missing "+key); return v; };
   firmware_=required("firmware");
   if(required("verified_speed_mode")!="true" || required("verified_multidrive2")!="true") throw std::invalid_argument("speed mode and Multi-drive2 must be verified");
   const auto enable_setting=std::stoi(required("drive_enable_setting"));
   if(enable_setting!=1 && enable_setting!=2)throw std::invalid_argument("software servo control requires verified enable setting1/2");
   auto mapping=std::stoi(required("pdo_mapping"));
   if(mapping != 0 && mapping != 1) throw std::invalid_argument("unsupported PDO mapping");
   if(required("position_format")!="0")throw std::invalid_argument("only verified Index/Pos mode0 position feedback supported");
   if(info_.joints.size()!=2) throw std::invalid_argument("exactly two wheel joints required");
   for(size_t i=0;i<2;++i) {
    auto prefix=i==0?std::string("left_"):std::string("right_");
    wheels_[i]={info_.joints[i].name,std::stoi(required(prefix+"drive_id")),
     {std::stod(required(prefix+"gear_ratio")),std::stod(required(prefix+"direction")),std::stod(required(prefix+"feedback_rpm_per_count"))}, std::stod(required(prefix+"max_motor_rpm")),
     std::stoll(required(prefix+"position_steps_per_motor_revolution")),
     static_cast<uint16_t>(std::stoi(required(prefix+"encoder_pulses_per_motor_revolution")))};
    const auto &j=info_.joints[i];
    if(j.command_interfaces.size()!=1 || j.command_interfaces[0].name!="velocity" || j.state_interfaces.size()!=2 || j.state_interfaces[0].name!="velocity" || j.state_interfaces[1].name!="position") throw std::invalid_argument("velocity command and velocity/position feedback required");
    validate(wheels_[i].scale);
    const auto encoder=std::stoi(required(prefix+"encoder_pulses_per_motor_revolution"));
    if(wheels_[i].position_steps<=0 || wheels_[i].position_steps>65536 || encoder<=0 || encoder>65535)throw std::invalid_argument("invalid explicit position/encoder scale");
    if(wheels_[i].id<1 || wheels_[i].id>8 || !std::isfinite(wheels_[i].max_rpm) || wheels_[i].max_rpm<60 || wheels_[i].max_rpm>32767) throw std::invalid_argument("invalid drive ID or RPM limit");
   }
   if(wheels_[0].id==wheels_[1].id) throw std::invalid_argument("duplicate drive IDs");
   int baud=std::stoi(required("baud")); auto parity=required("parity"); int stop=std::stoi(required("stop_bits"));
   auto timeout=std::stod(required("response_timeout_seconds"));
   auto enable_timeout=std::stod(required("enable_timeout_seconds"));
   if(!std::isfinite(enable_timeout) || enable_timeout<=0 || enable_timeout>2)throw std::invalid_argument("invalid bounded enable timeout");
   enable_timeout_=std::chrono::microseconds(static_cast<int64_t>(enable_timeout*1000000));
   if(baud<=0 || parity.size()!=1 || (parity!="N"&&parity!="E"&&parity!="O") || (stop!=1&&stop!=2) || !std::isfinite(timeout) || timeout<=0 || timeout>1) throw std::invalid_argument("invalid serial configuration/timeout");
   response_timeout_=std::chrono::microseconds(static_cast<int64_t>(timeout*1000000));
   const auto bits_per_char=1+8+stop+(parity!="N"?1:0);
   gap_=std::chrono::microseconds(static_cast<int64_t>(std::ceil(std::max(1750.0,3500000.0*bits_per_char/baud))));
   bus_=modbus_new_rtu(required("serial_port").c_str(),baud,parity[0],8,stop);
   if(!bus_) throw std::runtime_error("cannot create Modbus context");
   modbus_set_slave(bus_,0x65);
   auto us=static_cast<uint32_t>(timeout*1000000);
   modbus_set_response_timeout(bus_,us/1000000,us%1000000);
   modbus_set_byte_timeout(bus_,us/1000000,us%1000000);
   updater_=std::make_unique<diagnostic_updater::Updater>(get_node());
   updater_->setHardwareID("M1 firmware="+firmware_);
   for(size_t i=0;i<2;++i) updater_->add(wheels_[i].joint, [this,i](diagnostic_updater::DiagnosticStatusWrapper &d) {
    std::lock_guard<std::mutex> lock(diagnostics_mutex_);
    const auto level=!valid_?diagnostic_msgs::msg::DiagnosticStatus::ERROR:
      (status_is(status_[i],DriveStatus::Inhibited)?diagnostic_msgs::msg::DiagnosticStatus::WARN:diagnostic_msgs::msg::DiagnosticStatus::OK);
    d.summary(level,valid_ && status_is(status_[i],DriveStatus::Inhibited)?"valid feedback; WAIT/INHIBIT (SERVO OFF or power condition), motion unavailable":reason_);
    d.add("position_format",0); d.add("position_steps_per_motor_revolution",wheels_[i].position_steps);
    d.add("drive_id",wheels_[i].id); d.add("firmware",firmware_); d.add("motor_status",status_[i]); d.add("alarm_code",alarm_[i]); d.add("protocol_error_check_raw",error_check_[i]); d.add("feedback_valid",valid_); d.add("motion_available",valid_ && !status_is(status_[i],DriveStatus::Inhibited)); d.add("last_lifecycle_target_speed_raw",targets_[i]);
   });
   return CallbackReturn::SUCCESS;
  } catch(const std::exception &e) {RCLCPP_ERROR(get_logger(),"M1 explicit target configuration: %s",e.what()); return CallbackReturn::ERROR;}
 }
 CallbackReturn on_configure(const rclcpp_lifecycle::State &) override {
  if(modbus_connect(bus_)==-1) {context(std::string("serial connect failed: ")+modbus_strerror(errno),false); return CallbackReturn::ERROR;}
  connected_=true;
  try {
   for(auto &w:wheels_) {
    modbus_set_slave(bus_,w.id);
    for(const auto &entry:std::array<std::pair<int,uint16_t>,2>{{{0x020d,0},{0x0105,w.encoder_pulses}}}) {
     uint16_t value; wait_bus_gap();
     const auto result=modbus_read_registers(bus_,entry.first,1,&value);
     last_transaction_end_=std::chrono::steady_clock::now();
     if(result!=1 || value!=entry.second)throw std::runtime_error("drive "+std::to_string(w.id)+" position format/encoder verification failed at register "+std::to_string(entry.first));
    }
    w.position_initialized=false;
   }
   modbus_set_slave(bus_,0x65);position_fault_=false;position_fault_reason_.clear();invalidate();context("connected; mode0/encoder verified; feedback not yet verified",false);return CallbackReturn::SUCCESS;
  }catch(const std::exception &e) {
   modbus_set_slave(bus_,0x65);invalidate();context(e.what(),false);RCLCPP_ERROR(get_logger(),"%s",e.what());return CallbackReturn::ERROR;
  }
 }
 CallbackReturn on_activate(const rclcpp_lifecycle::State &) override {
  if(position_fault_) {invalidate();context(position_fault_reason_+"; position fault preserved; explicit reconfigure required",false);return CallbackReturn::ERROR;}
  for(const auto &w:wheels_) set_command(w.joint+"/velocity",0.0);
  if(read(rclcpp::Time(0),rclcpp::Duration(0,0))!=hardware_interface::return_type::OK) return CallbackReturn::ERROR;
  bool servo_attempted=false;
  try {
   {std::lock_guard<std::mutex> lock(diagnostics_mutex_);if(fault_seen_)throw std::runtime_error("previous fault preserved; explicit hardware recovery required before enable");}
   if(!targets_zero())context("stale target observed; activation withheld until ISTOP clears it",true);
   if(!send({0,0},MultiDriveCommand::ImmediateStop))throw std::runtime_error("pre-enable ISTOP failed");
   if(!targets_zero())throw std::runtime_error("stale target remains nonzero after ISTOP; servo enable refused");
   servo_attempted=true;
   if(!send({0,0},MultiDriveCommand::ServoOn))throw std::runtime_error("Servo ON command failed");
   const auto deadline=std::chrono::steady_clock::now()+enable_timeout_;
   while(std::chrono::steady_clock::now()<deadline) {
    if(read(rclcpp::Time(0),rclcpp::Duration(0,0))!=hardware_interface::return_type::OK) return activation_failed(servo_attempted);
    if(!targets_zero())throw std::runtime_error("target speed changed during Servo ON; activation refused");
    {std::lock_guard<std::mutex> lock(diagnostics_mutex_);if(!status_is(status_[0],DriveStatus::Inhibited) && !status_is(status_[1],DriveStatus::Inhibited))return CallbackReturn::SUCCESS;}
    std::this_thread::sleep_until(std::min(deadline,std::chrono::steady_clock::now()+gap_));
   }
   throw std::runtime_error("Servo ON readiness timeout; drive remains inhibited");
  }catch(const std::exception &e){fail(e.what());return activation_failed(servo_attempted);}
 }
 CallbackReturn on_deactivate(const rclcpp_lifecycle::State &) override {
  const auto cleanup=safe_off_cleanup(); invalidate(); context("deactivation; "+cleanup.detail,false);
  return cleanup.success?CallbackReturn::SUCCESS:CallbackReturn::ERROR;
 }
 CallbackReturn on_error(const rclcpp_lifecycle::State &) override {send({0,0},MultiDriveCommand::ImmediateStop); invalidate(); {std::lock_guard<std::mutex> lock(diagnostics_mutex_); reason_ += "; hardware error, ISTOP requested, physical stop unverified; no automatic re-enable"; valid_=false;} return CallbackReturn::SUCCESS;}
 CallbackReturn on_shutdown(const rclcpp_lifecycle::State &) override {
  const auto cleanup=safe_off_cleanup(); invalidate(); context("shutdown; "+cleanup.detail,false);
  if(bus_)modbus_close(bus_);connected_=false;
  return cleanup.success?CallbackReturn::SUCCESS:CallbackReturn::ERROR;
 }
 CallbackReturn on_cleanup(const rclcpp_lifecycle::State &) override {if(bus_)modbus_close(bus_);connected_=false;context("disconnected",false);return CallbackReturn::SUCCESS;}
 hardware_interface::return_type read(const rclcpp::Time &, const rclcpp::Duration &) override {
  if(position_fault_)return fail(position_fault_reason_+"; position fault preserved; explicit reconfigure required");
  // One native Multi-drive2 read: status/alarm/RPM/voltage/current/Index/Pos/check.
  std::array<uint16_t,16> data;
  if(!connected_) return fail("feedback bus not connected");
  wait_bus_gap();
  const auto count=modbus_read_registers(bus_,address(0),16,data.data());
  last_transaction_end_=std::chrono::steady_clock::now();
  if(count!=16) return fail(std::string("feedback read failed/timeout: ")+modbus_strerror(errno));
  std::array<double,2> velocities,positions;
  std::array<int64_t,2> counts;
  const auto now=last_transaction_end_;
  try {
   capture_feedback_snapshot(data);
   for(size_t i=0;i<2;++i) {
    const auto &w=wheels_[i];const size_t offset=w.id<wheels_[1-i].id?0:8;
    velocities[i]=checked_feedback(data[offset],data[offset+1],data[offset+2],w.scale);
    if(std::abs(feedback_velocity(data[offset+2],{1,1,w.scale.feedback_rpm_per_count})*60/(2*std::acos(-1)))>w.max_rpm) throw std::runtime_error("feedback exceeds configured motor RPM limit");
    if(data[offset+6]>=w.position_steps) {position_fault_=true;position_fault_reason_="drive "+std::to_string(w.id)+" invalid residual position pulse";throw std::runtime_error(position_fault_reason_);}
    const auto index=data[offset+5]>32767?static_cast<int32_t>(data[offset+5])-65536:data[offset+5];
    counts[i]=index*w.position_steps+data[offset+6];
    int64_t delta=counts[i];
    if(w.position_initialized) {
     delta=counts[i]-w.last_count;const auto wrap=65536*w.position_steps;
     if(delta>wrap/2)delta-=wrap;else if(delta<-wrap/2)delta+=wrap;
     const auto elapsed=std::chrono::duration<double>(now-w.position_time).count();
     const auto uncertainty=2*std::chrono::duration<double>(response_timeout_).count();
     const auto max_delta=w.max_rpm/60*(elapsed+uncertainty)*w.position_steps+2;
     if(std::abs(static_cast<double>(delta))>max_delta) {position_fault_=true;position_fault_reason_="drive "+std::to_string(w.id)+" position jump/reset exceeds configured motor RPM bound";throw std::runtime_error(position_fault_reason_);}
    }
    const auto angle=delta*2*std::acos(-1)/w.position_steps/w.scale.motor_revolutions_per_wheel*w.scale.direction;
    positions[i]=(w.position_initialized?w.position:0)+angle;
   }
  }catch(const std::exception &e){return fail(e.what());}
  for(size_t i=0;i<2;++i) {
   auto &w=wheels_[i];w.last_count=counts[i];w.position=positions[i];w.position_time=now;w.position_initialized=true;
   set_state(w.joint+"/velocity",velocities[i]);set_state(w.joint+"/position",positions[i]);
  }
  context("valid feedback",true);return hardware_interface::return_type::OK;
 }
 hardware_interface::return_type write(const rclcpp::Time &,const rclcpp::Duration &) override {
  if(position_fault_)return fail(position_fault_reason_+"; position fault preserved; explicit reconfigure required");
  std::array<int16_t,2> rpm;
  try {for(size_t i=0;i<2;++i) {rpm[i]=command_rpm(get_command(wheels_[i].joint+"/velocity"),wheels_[i].scale);
   {std::lock_guard<std::mutex> lock(diagnostics_mutex_); if(rpm[i]!=0 && status_is(status_[i],DriveStatus::Inhibited))throw std::invalid_argument("drive "+std::to_string(wheels_[i].id)+" inhibited; nonzero command rejected");}if(std::abs(rpm[i])>wheels_[i].max_rpm)throw std::invalid_argument("command exceeds configured motor RPM limit");}}
  catch(const std::exception &e){return fail(e.what());}
  if(!send(rpm))return fail(std::string("velocity write failed/timeout: ")+modbus_strerror(errno));
  return hardware_interface::return_type::OK;
 }
};
}
PLUGINLIB_EXPORT_CLASS(mobile_base_m1::M1System,hardware_interface::SystemInterface)
