"""Native installed model/RSP public workflow; no physical devices or joint synthesis."""
import os
import signal
import subprocess
import time
from pathlib import Path
import pytest

def test_installed_model_preserves_geometry_and_publishes_scan_transforms():
    import rclpy
    from rclpy.duration import Duration
    from rclpy.time import Time
    from tf2_ros import Buffer, TransformListener
    from ament_index_python.packages import get_package_share_directory
    from std_msgs.msg import String
    from rclpy.qos import QoSProfile, DurabilityPolicy
    share = Path(get_package_share_directory('mobile_base_description'))
    model = subprocess.run(['xacro', str(share/'urdf/mobile_base.urdf.xacro'),
                            'fl_scan_yaw:=0.7853981633974483',
                            'br_scan_yaw:=2.356194490192345'], check=True,
                           text=True, capture_output=True).stdout
    import xml.etree.ElementTree as ET
    robot = ET.fromstring(model)
    assert robot.find("link[@name='L_TORSO_J1']") is None
    assert robot.find("joint[@name='left_wheel_joint']").attrib['type'] == 'continuous'
    assert robot.find("joint[@name='driving_slide_joint_L']").attrib['type'] == 'prismatic'
    for mesh in robot.findall('.//mesh'):
        prefix='package://mobile_base_description/'
        assert mesh.attrib['filename'].startswith(prefix)
        assert (share/mesh.attrib['filename'][len(prefix):]).is_file()
    process = subprocess.Popen(['ros2','launch','mobile_base_description','description.launch.py',
        'fl_scan_yaw:=0.7853981633974483','br_scan_yaw:=2.356194490192345'],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
    rclpy.init(); node=rclpy.create_node('model_tf_acceptance');buffer=Buffer();listener=TransformListener(buffer,node)
    descriptions=[]
    sub=node.create_subscription(String,'/robot_description',lambda m:descriptions.append(m.data),
        QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    expected={
        'base_imu_link':(.04375,-.008,.24141,0.,1.),
        'base_lidar_link_FL_1':(.28771,.26721,.19589,.382683432365,.923879532511),
        'base_lidar_link_BR_1':(-.24671,-.26721,.19589,.923879532511,.382683432365),
    }
    try:
        end=time.monotonic()+10
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.1)
            if descriptions and all(buffer.can_transform('base_footprint',f,Time()) for f in expected):break
        assert descriptions
        for frame,(x,y,z,qz,qw) in expected.items():
            t=buffer.lookup_transform('base_footprint',frame,Time(),timeout=Duration(seconds=1)).transform
            assert (t.translation.x,t.translation.y,t.translation.z)==pytest.approx((x,y,z),abs=1e-9)
            assert (t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w)==pytest.approx((0,0,qz,qw),abs=1e-9)
        assert len(node.get_publishers_info_by_topic('/tf_static'))==1
        assert not buffer.can_transform('odom','base_footprint',Time())
    finally:
        node.destroy_node();rclpy.shutdown();os.killpg(process.pid,signal.SIGINT)
        process.communicate(timeout=10)
