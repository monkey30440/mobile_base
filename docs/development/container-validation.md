# #47 container validation

2026-10-02；對應 [#47](https://github.com/monkey30440/mobile_base/issues/47)。實作前基準 `a42ae248fec549be67e90bee0fed720721edcca3`。

## CONFIRMED — 本機 ARM64 軟體驗證

Host 為 NVIDIA Jetson AGX Thor Developer Kit、Ubuntu24.04.5、L4T39.2.1。以下結果只適用本機軟體環境；V1 target 仍是 AGX Orin。

- 指定 base 為 `nvcr.io/nvidia/isaac/ros:isaac_ros_740c8500df2685ab1f4a4e53852601df-arm64-jetpack`，固定 registry digest `sha256:e5a7ecfaea177c602a43937c932672dd354ed8bf3acc11e29ca7c5ebc6a891d6`。
- 實際 base run：Ubuntu24.04.3、linux/arm64、Jazzy，已有 g++／colcon。Base Jetson HTTP apt endpoint 回傳401；相同HTTPS endpoint回傳200。Dockerfile僅將該endpoint改HTTPS，保留r38.4與Isaac release-4.2來源及套件驗證。
- `bash -n docker/entrypoint.sh docker/ros-environment.sh`、`docker compose config --quiet`、`git diff --check` 通過。此 shell/YAML 工作無額外型別檢查器。
- `docker compose build dev` 成功。觀測產物 image ID `sha256:3e6aa2e48ecc82e2e1ca81bdd787e153e1b697107e2841bfddd0326f76b71166`；此為本次產物，不保證未來apt解析相同。完整套件清單在image的 `/opt/mobile-base-packages.tsv`。
- 以隔離 Compose project `mobile-base-ticket47` 執行 up、exec、down；runtime=runc、network=host、privileged=false、UID:GID=1000:1000。沒有 DISPLAY、USB device 或 NVIDIA runtime 仍可啟動及編譯測試。
- 互動 `bash -ic` 與非互動 `bash -c` 可使用ROS CLI。robot_state_publisher、robot_localization、slam_toolbox、nav2_route／AMCL／MPPI、diagnostic_updater／aggregator、RViz與rqt套件可發現；`ros2 pkg executables nav2_route` 顯示 `route_server`。
- `colcon list --base-paths /workspace` 當下為空；reference IMU未被誤納入。這個空結果不當作build/test通過。
- 在容器 `/tmp` 建立真正的臨時ament_cmake package，以g++編譯、連結rclcpp，建立ROS node並透過CTest驗證；`colcon build`、`colcon test` 與 `colcon test-result --verbose` 通過：1 test、0 errors、0 failures。另加入受控失敗JUnit結果，確認test-result回傳nonzero；移除負向probe後重新確認1 test通過。Overlay source後 `ros2 run ticket47_probe probe` 成功。另以該真實package的install overlay暫時接入 `/workspace/install`，新非互動及互動bash均自動發現 `/workspace/install/ticket47_probe`，非互動shell可直接run；兩者均通過。Scratch package、workspace symlink及測試結果已移除，未留production package或測試framework。
- 容器透過bind mount寫入host workspace，觀測檔案ownership為1000:1000；probe已刪除。
- 兩個native demo_nodes_cpp程序以ROS_DOMAIN_ID=217通訊；listener收到多筆 `I heard: [Hello World: ...]`。timeout停止node回傳124為預期；無以timeout本身判定通訊通過。
- `docker compose -p mobile-base-ticket47 down` 成功；該project的 `ps --all` 為空。其他既有容器未被停止或刪除。

本輪scratch驗證命令與logs位於 `/tmp/ticket47-smoke.sh`、`/tmp/ticket47-smoke.log`、`/tmp/ticket47-overlay-smoke.log`、`/tmp/ticket47-listener.log`、`/tmp/mobile-base-ticket47-build.log`；這些是本機暫存證據，非永久交付。日常重現入口見 [操作文件](container.md)。

## REQUIRES HARDWARE VALIDATION

- AGX Orin上的selected image/BSP/driver相容性；本機Thor成功不證明Orin相容。
- USB motor／IMU stable paths、permissions、hotplug與通訊（#35／#36）。
- picoScan NIC、IP、封包、跨機ROS discovery（#37）。
- 真正Operator display、RViz/rqt可見畫面、OpenGL及是否需要NVIDIA graphics runtime。軟體OpenGL與可選NVIDIA override僅提供設定入口，本轮未驗證GUI／GPU。

普通host帳號Docker socket permission denied仍存在；本輪使用經授權的daemon操作，沒有更動host groups／socket／daemon配置。容器就緒不表示robot Bringup ready；這些驗證不能關閉後續硬體功能tickets。
