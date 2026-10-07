# Real IMU / EKF static preflight — 2026-10-07

Source3dccd4e; tickets36/38 remain partial. Operator declined additional precise
rotation-angle measurement and asked to continue static wheel/IMU/EKF integration.
That does not establish calibrated uncertainty or waive evidence boundaries.

## Completed passive observation

A separate network-none container mapped only `/dev/ttyACM0` to the confirmed
`/dev/fihRobotBaseIMU` with the actual device group20. Exclusive115200 serial
capture sent no serial payload commands; no motor device was mapped. The current
adapter packet decoder checked AA55/59-byte/XOR and finite values, with guide
conversion9.81m/s² per g and pi/180rad/s per deg/s, identity device-to-published
axes. Latest model mounting remains base_imu_link yaw+pi/2; identity adapter axes
are not a claim that the mounting transform is identity.

30.036s received5175 valid packets, zero invalid candidates. This is receipt rate,
not a calibrated acquisition frequency or latency. Published-axis gyro statistics:

| Axis | Mean rad/s | Unbiased sample variance (rad/s)² |
| --- | ---: | ---: |
| X | +0.000662291 | 1.898588809e-8 |
| Y | −0.000259199 | 2.345200041e-8 |
| Z | −0.000506874 | 1.692948010e-8 |

Mean acceleration was approximately[-0.002434,0.019973,9.770385]m/s². Two15s
subwindows are retained. These observations do not validate wire axis dynamics,
scale, timing, thermal stability or bias calibration. Nonzero stationary gyro mean
must not be hidden by labelling centered noise variance as the entire uncertainty.
Observed second moments about zero are also recorded, without adding bias correction
or claiming that they account for unmeasured operating errors.

## Native configuration gap, not a new runtime responsibility

The installed diff_drive_controller4.42.1 generated parameter header confirms
pose/twist covariance defaults are all zeros. Its native parameter descriptors
recommend initial diagonals[0.001,0.001,0.001,0.001,0.001,0.01], explicitly requiring
robot-specific tuning. Current M1 launch does not configure these fields. The
existing native EKF research requires usable positive measurement uncertainty;
previous synthetic test values cannot become deployment facts.

A proposed bounded commissioning configuration uses native wheel initial values
and explicitly identified stationary IMU statistics, with their bias limitations.
Operator adoption is pending. No EKF, hardware activation, positive-covariance IMU
node or motor command has been started by this checkpoint. Real filtered output
and specific odom-edge ownership are therefore NOT yet verified. The proposal is
not an accepted production profile, calibrated noise model or accuracy result.

[Raw evidence](artifacts/imu-ekf-static-preflight-20261007.tar.gz) retains the exact
passive script, raw chunks/converted samples, full/subwindow statistics, proposed
but unapplied uncertainty note and the installed native parameter header. No
runtime source changes or drive parameters are introduced. Later integration must
retain native RSP model ownership and EKF-only odom→base_footprint ownership.

Subsequent checkpoint: Operator adopted the bounded commissioning proposal. Actual
static integration and its remaining wheel-position/TF gap are recorded in
[real static estimation](real-static-estimation-20261007.md). The pending/unapplied
statements above describe this historical preflight, not the current status.
