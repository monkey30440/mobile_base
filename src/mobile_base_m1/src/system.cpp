#include <array>
#include <atomic>
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
 struct Wheel {std::string joint; int id; Scale scale; double max_rpm;};
 std::array<Wheel, 2> wheels_;
 modbus_t *bus_ = nullptr;
 std::unique_ptr<diagnostic_updater::Updater> updater_;
 std::mutex diagnostics_mutex_;
 std::string reason_ = "not configured";
 std::array<uint16_t, 2> status_{};
 std::array<uint16_t, 2> alarm_{};
 bool valid_ = false;
 bool connected_ = false;
 std::string firmware_;
 int address(int index) const {return 0xf000 | (index << 8) | (1 << (wheels_[0].id-1)) | (1 << (wheels_[1].id-1));}
 void context(const std::string &reason, bool valid) {
  std::lock_guard<std::mutex> lock(diagnostics_mutex_); reason_ = reason; valid_ = valid;
 }
 void invalidate() {
  for (const auto &w : wheels_) set_state(w.joint + "/velocity", std::numeric_limits<double>::quiet_NaN());
 }
 bool send(const std::array<int16_t, 2> &rpm) {
  uint16_t data[4];
  const auto first = wheels_[0].id < wheels_[1].id ? 0 : 1;
  data[0]=1; data[1]=static_cast<uint16_t>(rpm[first]);
  data[2]=1; data[3]=static_cast<uint16_t>(rpm[1-first]);
  return connected_ && modbus_write_registers(bus_, address(8), 4, data) == 4;
 }
 hardware_interface::return_type fail(const std::string &reason) {
  invalidate(); context(reason, false);
  // Best effort zero on both drives; communication failure cannot prove a physical stop.
  send({0,0});
  RCLCPP_ERROR(get_logger(), "%s", reason.c_str());
  return hardware_interface::return_type::ERROR;
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
   auto mapping=std::stoi(required("pdo_mapping"));
   if(mapping != 0 && mapping != 1) throw std::invalid_argument("unsupported PDO mapping");
   if(info_.joints.size()!=2) throw std::invalid_argument("exactly two wheel joints required");
   for(size_t i=0;i<2;++i) {
    auto prefix=i==0?std::string("left_"):std::string("right_");
    wheels_[i]={info_.joints[i].name,std::stoi(required(prefix+"drive_id")),
     {std::stod(required(prefix+"gear_ratio")),std::stod(required(prefix+"direction")),std::stod(required(prefix+"feedback_rpm_per_count"))}, std::stod(required(prefix+"max_motor_rpm"))};
    const auto &j=info_.joints[i];
    if(j.command_interfaces.size()!=1 || j.command_interfaces[0].name!="velocity" || j.state_interfaces.size()!=1 || j.state_interfaces[0].name!="velocity") throw std::invalid_argument("only velocity command and feedback supported");
    validate(wheels_[i].scale);
    if(wheels_[i].id<1 || wheels_[i].id>8 || !std::isfinite(wheels_[i].max_rpm) || wheels_[i].max_rpm<60 || wheels_[i].max_rpm>32767) throw std::invalid_argument("invalid drive ID or RPM limit");
   }
   if(wheels_[0].id==wheels_[1].id) throw std::invalid_argument("duplicate drive IDs");
   int baud=std::stoi(required("baud")); auto parity=required("parity"); int stop=std::stoi(required("stop_bits"));
   auto timeout=std::stod(required("response_timeout_seconds"));
   if(baud<=0 || parity.size()!=1 || (parity!="N"&&parity!="E"&&parity!="O") || (stop!=1&&stop!=2) || !std::isfinite(timeout) || timeout<=0 || timeout>1) throw std::invalid_argument("invalid serial configuration/timeout");
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
    d.summary(valid_?diagnostic_msgs::msg::DiagnosticStatus::OK:diagnostic_msgs::msg::DiagnosticStatus::ERROR,reason_);
    d.add("drive_id",wheels_[i].id); d.add("firmware",firmware_); d.add("motor_status",status_[i]); d.add("alarm_code",alarm_[i]); d.add("feedback_valid",valid_);
   });
   return CallbackReturn::SUCCESS;
  } catch(const std::exception &e) {RCLCPP_ERROR(get_logger(),"M1 explicit target configuration: %s",e.what()); return CallbackReturn::ERROR;}
 }
 CallbackReturn on_configure(const rclcpp_lifecycle::State &) override {
  if(modbus_connect(bus_)==-1) {context(std::string("serial connect failed: ")+modbus_strerror(errno),false); return CallbackReturn::ERROR;}
  connected_=true; context("connected; feedback not yet verified",false); return CallbackReturn::SUCCESS;
 }
 CallbackReturn on_activate(const rclcpp_lifecycle::State &) override {
  for(const auto &w:wheels_) set_command(w.joint+"/velocity",0.0);
  if(!send({0,0})) {context("activation zero command failed",false); return CallbackReturn::ERROR;}
  return read(rclcpp::Time(0),rclcpp::Duration(0,0))==hardware_interface::return_type::OK?CallbackReturn::SUCCESS:CallbackReturn::ERROR;
 }
 CallbackReturn on_deactivate(const rclcpp_lifecycle::State &) override {
  const auto stopped=send({0,0}); invalidate(); context(stopped?"deactivated; zero acknowledged, physical stop unverified":"deactivation zero failed; physical stop unverified",false);
  return stopped?CallbackReturn::SUCCESS:CallbackReturn::ERROR;
 }
 CallbackReturn on_error(const rclcpp_lifecycle::State &) override {send({0,0}); invalidate(); {std::lock_guard<std::mutex> lock(diagnostics_mutex_); reason_ += "; hardware error, physical stop unverified"; valid_=false;} return CallbackReturn::SUCCESS;}
 CallbackReturn on_shutdown(const rclcpp_lifecycle::State &) override {const auto zero=send({0,0}); invalidate(); context(zero?"shutdown zero acknowledged; physical stop unverified":"shutdown zero failed; physical stop unverified",false); if(bus_)modbus_close(bus_);connected_=false;return zero?CallbackReturn::SUCCESS:CallbackReturn::ERROR;}
 CallbackReturn on_cleanup(const rclcpp_lifecycle::State &) override {if(bus_)modbus_close(bus_);connected_=false;context("disconnected",false);return CallbackReturn::SUCCESS;}
 hardware_interface::return_type read(const rclcpp::Time &, const rclcpp::Duration &) override {
  uint16_t data[6];
  if(!connected_ || modbus_read_registers(bus_,address(0),6,data)!=6) return fail(std::string("feedback read failed/timeout: ")+modbus_strerror(errno));
  std::array<double,2> velocities;
  try {
   for(size_t i=0;i<2;++i) {
    size_t offset=((wheels_[i].id<wheels_[1-i].id)?0:3);
    {std::lock_guard<std::mutex> lock(diagnostics_mutex_);status_[i]=data[offset];alarm_[i]=data[offset+1];}
    velocities[i]=checked_feedback(data[offset],data[offset+1],data[offset+2],wheels_[i].scale);
    if(std::abs(feedback_velocity(data[offset+2],{1,1,wheels_[i].scale.feedback_rpm_per_count})*60/(2*std::acos(-1)))>wheels_[i].max_rpm) throw std::runtime_error("feedback exceeds configured motor RPM limit");
   }
  }catch(const std::exception &e){return fail(e.what());}
  for(size_t i=0;i<2;++i)set_state(wheels_[i].joint+"/velocity",velocities[i]);
  context("valid feedback",true);return hardware_interface::return_type::OK;
 }
 hardware_interface::return_type write(const rclcpp::Time &,const rclcpp::Duration &) override {
  std::array<int16_t,2> rpm;
  try {for(size_t i=0;i<2;++i) {rpm[i]=command_rpm(get_command(wheels_[i].joint+"/velocity"),wheels_[i].scale);if(std::abs(rpm[i])>wheels_[i].max_rpm)throw std::invalid_argument("command exceeds configured motor RPM limit");}}
  catch(const std::exception &e){return fail(e.what());}
  if(!send(rpm))return fail(std::string("velocity write failed/timeout: ")+modbus_strerror(errno));
  return hardware_interface::return_type::OK;
 }
};
}
PLUGINLIB_EXPORT_CLASS(mobile_base_m1::M1System,hardware_interface::SystemInterface)
