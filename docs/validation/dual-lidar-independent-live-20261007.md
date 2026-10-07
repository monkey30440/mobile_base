# Independent dual LiDAR live verification — 2026-10-07

Operator requested agent-run LiDAR verification after Description manual confirmation. Source501f0f0, unchanged installed Description/Perception entrypoints, clean build prefix. Two separate launches: geometry-only Description, then Perception dual_picoscan with explicitly selected installed config/lidar.yaml. ROS domain196, ARM64 production-check image SHA256307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46; native SICK3.9.0. Host routes both sensor IPs through enP2p1s0 with source192.168.0.51. No competing drivers/ports were observed before startup; no motor node, USB device mapping or velocity command.

## Observed live data — CONFIRMED for this bounded run

25 seconds of actual sensor traffic, with steady statistics after the first5 seconds:

| Source | IP / serial | Received scans | Steady arrival rate | Native frame | Valid ranges per1200 samples |
|---|---|---|---|---|---|
| FL |192.168.0.52 /25350157|614|25.004Hz|base_lidar_link_FL_1|1099–1101|
| BR |192.168.0.53 /25450354|613|25.003Hz|base_lidar_link_BR_1|1082–1088|

Each topic has one correctly namespaced native publisher with BEST_EFFORT QoS. Each source emitted one stable frame, not interleaved echo frames. Read-only device queries after stopping confirm both FREchoFilter2 (LAST) and DeviceIdent picoScan2.1.0.0R. Other ranges outside reported bounds are not counted as valid obstacle returns; their presence is not by itself a source fault.

Every received scan, including startup, had an available base_footprint→scan transform at its message timestamp. One native RSP publishes fixed model TF; transforms match the recorded model (FL roll pi/yaw+pi/4, BR roll pi/yaw−3pi/4 with identity scan children). No custom transform/scan publisher is added. This confirms the configured model/data relationship, not independent physical extrinsic accuracy.

First timestamps are host epoch, not device uptime. Steady receipt-minus-message age: FL45.7–50.2ms, BR44.9–50.1ms. No duplicate/backward steady timestamps; maximum observed inter-arrival gaps43.7/44.0ms. These are bounded host observations under native elapsed-tick mode1, not absolute acquisition-time calibration, long-run clock acceptance or a no-loss guarantee. Foxglove was not used in this run, so new-session visual/physical environment alignment is not claimed.

## Shutdown — FAILED / UNRESOLVED

After bounded capture, SIGINT requested native shutdown. Both drivers sent ScanDataEnable0 and received acknowledgements. Subsequent independent read-only SOPAS queries confirm both ScanDataEnable0; all native processes were gone and temporary container was removed.

Nevertheless, both native sick_generic_caller child processes exited **−6 (SIGABRT)** during teardown. FL logged a glibc __pthread_tpp_change_priority assertion; BR threw std::system_error with Invalid argument. Parent ros2 launch returned0, which is not successful child-shutdown evidence. Earlier records had native−11; do not conflate this run's−6 symptom with a proven same root cause.

Clean shutdown remains unaccepted. No runtime patch, restart loop or error masking was added. The root cause is not established by these logs; it requires targeted upstream/source diagnosis. The successful live data/TF observation does not close ticket37 or remove dependencies.

[Capture script, per-message observations, last scans, launch/build logs, shutdown errors, direct device readback and source hashes](artifacts/dual-lidar-independent-live-20261007.tar.gz).
