"""Build-time extraction of the authoritative base subtree; no runtime publisher."""
import copy
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

source, output = map(Path, sys.argv[1:])
original = ET.parse(source).getroot()
robot = ET.Element('robot', name='mobile_base', attrib={'xmlns:xacro':'http://www.ros.org/wiki/xacro'})
for side in ('fl','br'):
    for axis in ('roll', 'pitch', 'yaw'):
        ET.SubElement(robot,'xacro:arg',name=side+'_scan_'+axis,default='UNSET')
links = {'base_link'}
joints = []
while True:
    found = [j for j in original.findall('joint') if j not in joints
             and j.find('parent').attrib['link'] in links and j.attrib['name'] != 'J_L_TORSO_J1']
    if not found:break
    joints.extend(found)
    links.update(j.find('child').attrib['link'] for j in found)
for link in original.findall('link'):
    if link.attrib['name'] not in links:continue
    link=copy.deepcopy(link)
    if link.attrib['name'] in ('base_lidar_link_FL', 'base_lidar_link_BR'):
        link.attrib['name'] = link.attrib['name'].replace('base_lidar_link_', 'base_lidar_cad_link_')
    if link.attrib['name']=='BASE_FOOTPRINT':link.attrib['name']='base_footprint'
    for mesh in link.findall('.//mesh'):
        mesh.attrib['filename']='package://mobile_base_description/meshes/'+Path(mesh.attrib['filename']).name
    robot.append(link)
for joint in joints:
    joint=copy.deepcopy(joint)
    for endpoint in ('parent', 'child'):
        node = joint.find(endpoint)
        if node.attrib['link'] in ('base_lidar_link_FL', 'base_lidar_link_BR'):
            node.attrib['link'] = node.attrib['link'].replace('base_lidar_link_', 'base_lidar_cad_link_')
    if joint.attrib['name']=='J_BASE_FOOTPRINT':
        joint.find('parent').attrib['link']='base_footprint'
        joint.find('child').attrib['link']='base_link'
        joint.find('origin').attrib['xyz']='0 0 0.256'
    for side,short in [('L','left'),('R','right')]:
        if joint.attrib['name']=='driving_wheel_joint_'+side:joint.attrib['name']=short+'_wheel_joint'
    robot.append(joint)
for side in ('FL','BR'):
    mounting = 'base_lidar_link_' + side
    ET.SubElement(robot, 'link', name=mounting)
    joint = ET.SubElement(robot, 'joint', name='lidar_mount_joint_' + side, type='fixed')
    ET.SubElement(joint, 'parent', link='base_lidar_cad_link_' + side)
    ET.SubElement(joint, 'child', link=mounting)
    ET.SubElement(joint, 'origin', xyz='0 0 0',
                  rpy=' '.join('$(arg ' + side.lower() + '_scan_' + axis + ')'
                               for axis in ('roll', 'pitch', 'yaw')))
    scan=mounting+'_1'
    ET.SubElement(robot,'link',name=scan)
    joint=ET.SubElement(robot,'joint',name='lidar_scan_joint_'+side,type='fixed')
    ET.SubElement(joint,'parent',link='base_lidar_link_'+side)
    ET.SubElement(joint,'child',link=scan)
    ET.SubElement(joint,'origin',xyz='0 0 0',rpy='0 0 0')
ET.indent(robot)
output.parent.mkdir(parents=True,exist_ok=True)
ET.ElementTree(robot).write(output,encoding='unicode',xml_declaration=True)
