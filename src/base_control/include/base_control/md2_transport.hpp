// SUB-001 Base Control — Modbus Transport
//
// 以 libmodbus 實作 RS-485 Multi-drive 2.0 通訊。
//
// 不負責：暫存器語意、單位換算、驅動器狀態機（由 driver_interface 處理）。
//
// 協議參數於 2026-08-07 實機驗證，見
// docs/implementation/SUB-001-base-control-plan.md § 已驗證之通訊協議。

#ifndef BASE_CONTROL__MD2_TRANSPORT_HPP_
#define BASE_CONTROL__MD2_TRANSPORT_HPP_

#include <cstdint>
#include <stdexcept>
#include <string>

struct _modbus;
typedef struct _modbus modbus_t;

namespace base_control
{

// ── Multi-drive 2.0 群組定址 ────────────────────────────────────────────────
// 位址上位元組 [15:12]=0xF、[11:8]=Index；下位元組 bit n = Driver ID (n+1) 被選中。
inline constexpr int kMd2GroupId = 0x65;
inline constexpr int kDriverBitmask = 0x03;  // ID1 + ID2

inline constexpr int kReadIndexBase = 0;
inline constexpr int kReadItemCount = 7;   // Read index 0~6
inline constexpr int kWriteIndexBase = 8;
inline constexpr int kWriteItemCount = 2;  // Write index 8~9

inline constexpr int kReadAddr = 0xF000 | (kReadIndexBase << 8) | kDriverBitmask;   // 0xF003
inline constexpr int kWriteAddr = 0xF000 | (kWriteIndexBase << 8) | kDriverBitmask;  // 0xF803

inline constexpr int kNumDrivers = 2;
inline constexpr int kItemsPerDriver = kReadItemCount + 1;          // +1: Error_Check
inline constexpr int kReadCount = kItemsPerDriver * kNumDrivers;    // 16 words
inline constexpr int kWriteCount = kWriteItemCount * kNumDrivers;   // 4 words

// Read Data Mapping（09-26 = 0）
inline constexpr int kIdxStatus = 0;
inline constexpr int kIdxAlarm = 1;
inline constexpr int kIdxRpm = 2;
inline constexpr int kIdxPosTurns = 5;
inline constexpr int kIdxPosPulse = 6;

class Md2Error : public std::runtime_error
{
public:
  explicit Md2Error(const std::string & what) : std::runtime_error(what) {}
};

/// 單一驅動器之原始回授（未套用方向修正與單位換算）。
struct DriverRaw
{
  uint16_t status = 0;
  uint16_t alarm = 0;
  int16_t rpm = 0;        ///< 馬達端 RPM，signed
  int16_t pos_turns = 0;  ///< 圈數，signed
  uint16_t pos_pulse = 0; ///< 圈內計數
};

/// 一次 FC17h 交易之雙驅動器回授。
struct Md2Feedback
{
  DriverRaw right;
  DriverRaw left;
  double comm_s = 0.0;
};

/// RS-485 Multi-drive 2.0 傳輸層。
class Md2Transport
{
public:
  Md2Transport() = default;
  ~Md2Transport();

  Md2Transport(const Md2Transport &) = delete;
  Md2Transport & operator=(const Md2Transport &) = delete;

  /// 開啟序列埠。重複呼叫前須先 close()。
  void open(
    const std::string & port, int baud, char parity = 'N',
    int data_bits = 8, int stop_bits = 1, double response_timeout_s = 0.1);

  void close();
  bool is_open() const { return ctx_ != nullptr; }

  /// 清空收發緩衝。交易中斷後殘留之回應會使後續請求失去同步，須先排空。
  void drain();

  // ── FC03 / FC06：個別驅動器 ───────────────────────────────────────────────

  uint16_t read_register(int driver_id, int address);
  void write_register(int driver_id, int address, uint16_t value);

  // ── FC17h：雙驅動器讀寫合一 ───────────────────────────────────────────────

  /// 單一封包同時下達雙輪命令並讀回回授。
  /// Write data 為 driver-major：[ID1_cmd][ID1_rpm][ID2_cmd][ID2_rpm]。
  Md2Feedback read_write(
    uint16_t right_cmd, int16_t right_rpm,
    uint16_t left_cmd, int16_t left_rpm);

private:
  void ensure_open() const;

  modbus_t * ctx_ = nullptr;
};

}  // namespace base_control

#endif  // BASE_CONTROL__MD2_TRANSPORT_HPP_
