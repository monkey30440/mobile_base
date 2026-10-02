"""Select the required dataset files; native nodes own parsing and lifecycle."""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def selected_dataset(context):
    directory = Path(LaunchConfiguration('dataset').perform(context)).expanduser().resolve()
    paths = {name: directory / name for name in ('map.pgm', 'map.yaml', 'route_graph.geojson')}
    for path in paths.values():
        if not path.is_file():
            raise RuntimeError(f'Dataset {directory}: required file missing: {path}')
    return [
        LogInfo(msg=f'Selected dataset {directory}; inputs: {list(map(str, paths.values()))}'),
        Node(package='nav2_map_server', executable='map_server', name='map_server',
             output='screen', parameters=[{'yaml_filename': str(paths['map.yaml'])}]),
        Node(package='nav2_route', executable='route_server', name='route_server',
             output='screen', parameters=[{'graph_filepath': str(paths['route_graph.geojson']),
                                          'route_frame': 'map'}]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('dataset', description='Directory containing map.pgm, map.yaml and route_graph.geojson'),
        OpaqueFunction(function=selected_dataset),
    ])
