# Default LiDAR source configuration — 2026-10-07

Operator requested bare dual_picoscan.launch.py with source settings edited at /home/zzz/mobile_base/src/mobile_base_perception/config/lidar.yaml. Spec32/ticket37 were revised before implementation, superseding explicit-only LiDAR selection. IMU unchanged.

Launch now defaults lidar_config to the native package-share config/lidar.yaml. The development container was rebuilt with colcon --symlink-install; readlink resolves the installed config to /workspace/src/mobile_base_perception/config/lidar.yaml, the same bind-mounted host file. Source/installed hash both72c3794bc002511b76ba730264b1b250c1239a79547e6ce7c1f43f74ec404911. Source edits therefore apply at next launch without rebuild; there is no runtime reload or hardcoded host-path resolution. Ordinary installation is still a copied deployment snapshot. Explicit alternate config and CLI overrides remain supported; selected missing files still fail without fallback.

## Verification

No actual sensor startup or real configuration edits in this turn. Software tests ran in a network-none ARM64 production-check container without USB mappings, using a copied Perception package. The default-source case builds another fixture-owned symlink overlay, edits only its private source YAML after build, then launches native passive-loopback drivers and reads the changed echo selector through public ROS parameter services. It works independently of the outer installation mode and cannot modify Operator configuration.

Deterministic CLI inspection failed before the default existed, then passed after the minimal declaration change. Initial native pre-change trial also failed publisher discovery; its root cause is not established and that failure is not claimed as proof of the default-setting gap.

First full suite exposed unsupported empty CLI values: native ros2 launch rejects lidar_config:= before launch evaluation. Tests/docs/spec now use a selected YAML containing{} for fully CLI-provided settings; no empty-CLI support is claimed. Final full Perception suite: **21tests,0errors,0failures,0skipped**. Syntax and diff checks passed. Main dev overlay rebuilt successfully; only --show-args/readlink/hash checks were run there, never the active bare launch.

Standards review identified two test issues (mutation cleanup and installation-mode assumption); replacing mutation with fixture-owned symlink build resolved both.0 remaining Standards findings; Spec0 actionable findings. Retained approved basisf591f4e, scoped againstfc797e9.

[Raw TDD/first/final suite evidence, published contract and source hashes](artifacts/lidar-default-source-config-20261007.tar.gz). Prior real-device teardown failure remains unresolved; this convenience change is not hardware/shutdown/calibration acceptance and does not close ticket37.
