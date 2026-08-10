# RESULTS_REVIEW.md

## What the attached evidence already supports

The existing logs demonstrate the following useful facts:

- Modbus RTU communication is working with two M1 drivers.
- Driver IDs are distinct and the test flow uses ID1 as RIGHT and ID2 as LEFT.
- `01-11 = 0` (Speed), `01-12 = 4` (Multi-drive Lite speed source).
- `02-15 = 3` (100 Hz monitor/RPM refresh).
- `09-18 = 0` (Modbus RTU), `09-26 = 0` (Multi-drive 2.0 mapping 0).
- NET-X7 is mapped to SERVO-EN and software Enable/Disable has been exercised.
- Multi-drive 2.0 FC17 can command one motor while keeping the other stopped.
- RPM feedback and position feedback change consistently during the recorded motor tests.
- The stored gear-ratio logs show approximately 20 motor revolutions were commanded/measured for the gear-ratio checks.
- The original pure-math conversion log passed for the old `02-14=0` representation.

## Important gaps in the attached evidence

1. **No result logs for `07_set_position_format1.py` or `08_verify_position_format1.py`.**
   The folder contains these scripts, but not proof that `02-14=1` has actually been applied and validated.

2. **The saved `config.txt` still records `02-14=0`.**
   After changing to format 1, capture a new configuration snapshot rather than overwriting the old one.

3. **Communication watchdog is still disabled in the saved snapshot.**
   `05-17=0` and `05-18=0`; `05-21=0`.
   Do not choose final watchdog values until FC17 timing/jitter has been measured.

4. **No FC17 transaction timing/jitter evidence.**
   This is needed to choose a defensible ros2_control update rate, serial timeout, and M1 `05-17`.

5. **Mechanical observations are not encoded in the folder.**
   Visual wheel direction, visual ~1 wheel revolution during gear-ratio testing, wheel radius under load,
   and wheel separation measurements should be written into a human-readable result record.

6. **README/CHECKLIST in the original bundle were stale.**
   They referred to the removed/older `04_motor_test.py` and did not include scripts 02b/03b/04-safe/05/06/07/08.

## New v2 validation gates

Before implementing ros2_control:

- [ ] Set and verify `02-14=1` on both drivers.
- [ ] Verify format-1 FC17 position deltas in both positive and negative motor directions.
- [ ] Re-run the pure conversion test using the signed 32-bit model.
- [ ] Run the recommended-configuration audit.
- [ ] Benchmark FC17 zero-RPM transaction timing.
- [ ] Choose `05-17`, `05-18`, and `05-21` deliberately.
- [ ] After watchdog configuration, perform a separate intentional communication-loss test.
- [ ] Record wheel rolling radius and wheel separation measurements.
