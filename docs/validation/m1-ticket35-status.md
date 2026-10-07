# Ticket35 acceptance reconciliation — 2026-10-07

This checkpoint reconciles existing evidence against [ticket35](https://github.com/monkey30440/mobile_base/issues/35); it does not add acceptance requirements or close the ticket.

| Acceptance responsibility | Evidence and status | Next work |
| --- | --- | --- |
| Reproducible target entry, compatible versions and device facts | Software versions and container device/group access recorded. Transport, IDs, nominal geometry and polarity confirmed. AGX Orin target-platform compatibility has not been accepted. Actual firmware unknown; production profile deliberately incomplete. | Obtain actual firmware identity; retain AGX Orin target-platform verification and applicable operating settings as open evidence gates. |
| Minimal M1 command/feedback adapter; native kinematics, odometry, limits and timeout | Software public-seam suite passes; live commissioning commands/feedback and lifecycle evidence retained. No duplicate runtime owner added. | Preserve native ownership in subsequent integration. |
| Direction, scales, invalid feedback/link loss, timeout and diagnostics | Forward/reverse and raised0.03m/s motion observed. Native command-timeout trace passes. Fault/invalid feedback/silent peer covered in software. Effective displacement scales, real failure behavior and independent physical timeout timing remain unverified. | Plan bounded hardware failure checks and ground/calibration checks separately; do not unplug an enabled drive as an improvised test. |
| Teleop ending and troubleshooting; separate physical stopping evidence | Operator procedure documented; explicit-zero/deactivation trials have observed stopping and final inhibited/zero readbacks. Timeout is not session completion. The documented Teleop-ending/troubleshooting workflow is not yet fully accepted. | Validate actual workflow under its hardware conditions. |

The historical low-speed no-visible-motion symptom was not reproduced; its cause is unknown. No runtime fix is inferred. Native timeout receipt was observed at0.319s and fresh near-zero wheel feedback at0.471s, before cleanup at3.106s; these are observed commissioning latencies, not production guarantees. Operator saw stopping but could not identify its cause.

References: [software/target provenance](m1-software.md), [reverse](m1-native-reverse-20261007.md), [low-speed/timeout](m1-low-speed-timeout-20261007.md). Existing native dependency35→38 remains; neither ticket is complete. Effective calibration and production limits are not inferred from raised trials. No motor command was issued for this reconciliation.
