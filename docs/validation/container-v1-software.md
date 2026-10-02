# V1 container software verification — 2026-10-02

The repository Dockerfile built successfully from its pinned NVIDIA base image at integration commit `d17be633ada60b4280278ac81c0d81fa3bc6abc2`. Verification used a separate tag, `mobile-base-v1-production-check:jazzy`, image ID `sha256:307cf16d1581c1078d21e67c1d8c9aab21eeca61641e1c9a23b90c34d0b83e46`; existing development containers were not replaced.

```bash
docker build --progress=plain --build-arg LOCAL_UID=1000 --build-arg LOCAL_GID=1000 \
  -t mobile-base-v1-production-check:jazzy .
docker run --rm --runtime=runc --user 1000:1000 \
  -v /home/zzz/mobile_base:/workspace mobile-base-v1-production-check:jazzy bash -c \
  'colcon build --packages-select mobile_base_m1 mobile_base_imu mobile_base_lidar mobile_base_bringup && source install/setup.bash && colcon test --packages-select mobile_base_m1 mobile_base_imu mobile_base_lidar mobile_base_bringup && colcon test-result --verbose'
```

All four packages built. Colcon reported **32 tests, 0 errors, 0 failures, 0 skipped**. This count includes CTest suite entries; it is not 32 independent hardware scenarios. No physical serial devices were mapped into this verification container. M1 tests used a pseudo-terminal peer; the checked commit includes the corrected aggregate response integrity and RTU timing, but does not yet include Servo lifecycle changes.

The installed package inventory is retained inside the image at `/opt/mobile-base-packages.tsv`. Host-local build and test logs are `/tmp/mobile-base-v1-production-build.log` and `/tmp/mobile-base-v1-production-tests.log`; those temporary paths are not durable repository artifacts.

This proves the full Dockerfile and the merged software workflows can build and run together on the available arm64 host. It does not establish AGX Orin compatibility, sensor calibration, physical motor control or stopping, production speed limits, or complete V1 acceptance. Those boundaries remain governed by the relevant hardware tickets.
