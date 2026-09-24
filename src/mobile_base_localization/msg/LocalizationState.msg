# Localization owns state and measurement freshness. No evidence means UNKNOWN.
uint8 UNKNOWN=0
uint8 HEALTHY=1
uint8 LOST=2
uint8 state
# Timestamp of the latest valid scan used for this decision (zero without a valid measurement).
# Heartbeat publication must not advance this timestamp.
builtin_interfaces/Time measurement_stamp
