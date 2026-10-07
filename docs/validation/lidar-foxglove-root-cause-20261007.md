# BR LaserScan flicker: root-cause verification

Date: 2026-10-07. Stationary raised AMR; no motor commands. Native driver
`sick_scan_xd` 3.9.0, Foxglove desktop 3.3.0, Bridge 3.5.0, observation domain 176.

## Finding

BR ALL echoes are published as separate LaserScan messages on the same topic.
The installed Foxglove renderer keys its LaserScan renderable and batch filter
by topic/schema/comparison slot, **not frame_id or echo**. At zero decay it keeps
only the last message per render batch and replaces the same geometry on every
update. Dense echo0, sparse echo1 and empty echo2 therefore replace one another.
This causes intermittent points or no points, depending on render-batch timing.
FL LAST produces one echo stream, so there is no competing empty echo update.
Identity TF among echoes does not change this selection/replacement behavior.

This is a consumer/output contract mismatch, not evidence of BR hardware failure
or incorrectly calibrated mounting yaw. The empty echo is received data: native
3.9.0 publishes a scan when `ranges.size()>0`, without requiring valid returns.
An all-zero third echo has 1200 ranges but zero in-range points; this version
also derives range_max from actual ranges, yielding 0.001 m against range_min
0.05 m. Changing range_max alone cannot recover nonexistent returns.
See [native publish loop](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp#L524-L542)
and [conversion](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/driver/src/sick_scansegment_xd/ros_msgpack_publisher.cpp#L864-L930).

## Boundary evidence

A simultaneous ROS/WebSocket capture matched 490 messages by topic, optical
frame and sensor timestamp. All matched ranges/range_min/range_max were exactly
equal. The Bridge did not manufacture empty scans or corrupt those payloads.
Two separate WebSocket captures contained all echoes. In the second capture:

| Native stream | Messages | Valid points per scan |
|---|---:|---:|
| FL LAST | 129 | 1098–1102 |
| BR echo0 | 130 | 1099–1102 |
| BR echo1 | 129 | 54–59 |
| BR echo2 | 129 | 0 |

A separate controlled native Bridge at port 8766 varied only queue-depth limits:

| Forced min/max depth | FL | BR echo0 | BR echo1 | BR echo2 |
|---|---:|---:|---:|---:|
| 1/1 | 128 | 0 | 0 | 129 |
| 10/10 | 128 | 128 | 128 | 127 |

Depth1 reproduces the earlier all-empty forwarding symptom; depth10 preserves
all three echoes in this bounded test. This is a separate transport sensitivity,
not the cause of the remaining flicker after all echoes reached the client.
It does not prove the historical subscription's exact queue depth, identify an
internal DDS drop counter, or establish production no-loss guarantees.

## Actual installed renderer replay

The diagnostic extracts code from the installed application archive; it does
not substitute source from a different release. Bundle filename and SHA256 are
retained. The exact native batch filter, geometry-update method and native
history-retention implementation were executed with real captured scans.
Three.js geometry/material and TF services are lightweight stubs; this is a
logic/geometry replay, **not a GPU framebuffer or end-to-end GUI test**.

At 16.67 ms arrival windows with decay0, the real batch filter selected:

| Capture | FL empty updates | BR empty updates |
|---|---:|---:|
| First | 0 / 126 | 65 / 133 |
| Second | 0 / 95 | 94 / 130 |

These counts depend on arrival/render timing; the failure reproduced in both
captures. Separately, replaying every first-capture message through the actual
geometry updater and native history management produced:

| Display decay | FL updates without any visible valid points | BR |
|---|---:|---:|
| 0 | 0 / 129 | 128 / 385 |
| 0.2 seconds | 0 / 129 | 0 / 385 |

The zero-decay no-empty assertion is intentionally RED. The 0.2-second history
assertion is GREEN. TF is held valid in this isolated replay, proving that
latest-message replacement alone suffices to produce the observed failure;
it does not establish the operator's previous saved decay setting.

## Resolution and scope

The current stationary observation source `/lidar/br/view_echo0` selects only
first echo using **native** custom PointCloud2 configuration. Operator confirmed
its actual Foxglove display is stable. BR device ALL remains enabled and original
LaserScan topics are unchanged. This resolves the direction-observation workflow.

For original ALL-echo scan visualization, native decay0.2 with valid identity
echo TFs passes the renderer replay; it has not been verified in the actual GUI.
Do not claim original `/lidar/br/scan` was repaired. Accumulation retains older
points and is a visualization choice, not a sensor or navigation fix.

A production LaserScan consumer must explicitly account for multiplexed echoes
or receive a suitable native single-echo output. This diagnosis does not silently
change the confirmed BR ALL policy, select a navigation echo policy, introduce a
custom filter/republisher, or establish Nav2 consumer behavior. Those decisions
remain separate. Exact extrinsic calibration and native driver shutdown fault
are unchanged.

## Reproduction and cleanup

Artifact: `artifacts/lidar-foxglove-root-cause-20261007.tar.gz`, directory
`lidar-root-cause` when unpacked under `/tmp`. Vendor application/source code is
not redistributed. The extractor reads locally installed Foxglove 3.3.0 and
writes transient runtime sections under `/tmp`.

```bash
python3 /tmp/lidar-root-cause/extract_installed.py
node /tmp/lidar-root-cause/replay.cjs /tmp/lidar-root-cause/ws-scans.json 0
# Expected nonzero: BR displayed latest scan becomes empty (RED).
node /tmp/lidar-root-cause/render_update.cjs 0
# Expected zero: confirms empty geometry reproduction.
node /tmp/lidar-root-cause/render_update.cjs 0.2
# Expected zero: no empty accumulated geometry (GREEN).
```

Temporary port8766 probes exited. Capture scripts were removed from the viewer
container; no motor, production launch or runtime source changed. Current
port8765 depth10 viewer and operator-confirmed echo0 observation remain available.
