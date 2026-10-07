# Model TF software preflight — 2026-10-07

This is a temporary software experiment for #38, not its production implementation or acceptance. No devices were mapped into the container; no motor commands were sent.

The geometry source is `reference/FIH_AMR_ROBOT_V2.0_0731/urdf/RWF_V2.0_QA_release.urdf`. The experiment retained its base subtree and removed the upper-body branch owned by another team. It renamed `BASE_FOOTPRINT` to `base_footprint` and reversed the original fixed `base_link → BASE_FOOTPRINT` joint: original z=-0.256 m becomes `base_footprint → base_link` z=+0.256 m. Sensor mounting origins were retained. No synthetic joint states or LiDAR scan-frame rotations were supplied.

In the production-check image (`sha256:307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46`), native `check_urdf` accepted the 25-link/24-joint tree. Native robot_state_publisher 3.3.4 published the fixed transforms. An independent public tf2 observer verified these known translations from `base_footprint`:

| Child | x | y | z (m) |
|---|---:|---:|---:|
| base_link | 0 | 0 | 0.256 |
| base_imu_link | 0.04375 | -0.008 | 0.24141 |
| base_lidar_link_FL | 0.28771 | 0.26721 | 0.19589 |
| base_lidar_link_BR | -0.24671 | -0.26721 | 0.19589 |

All checked rotations were identity, as in the source URDF. The only `/tf_static` publisher was robot_state_publisher; no `odom → base_footprint` transform was fabricated. The isolated run used `--network none`, ROS domain 162, and no physical devices.

The retained experiment model, native parameter file, observer, results and check_urdf log are in `docs/validation/artifacts/model-tf-preflight-20261007.tar.gz`. This does not verify mesh resolution/rendering, dynamic wheel/suspension transforms, installed model packaging, actual mounting/calibrated optical axes, LiDAR scan child transforms, native EKF fusion or estimated accuracy. #38 remains open with its hardware dependencies intact. Production ownership must avoid the existing M1 launch starting a second robot_state_publisher.
