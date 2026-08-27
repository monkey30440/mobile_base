# Copyright 2026 Antigravity Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper utilities for resolving site resources in mobile_base bringup."""

import os
from pathlib import Path
from typing import Optional, Tuple


def find_maps_root() -> Path:
    """Locate the root maps/ directory across standard workspace environments."""
    if 'MOBILE_BASE_MAPS_DIR' in os.environ:
        maps_env = Path(os.environ['MOBILE_BASE_MAPS_DIR']).resolve()
        if maps_env.is_dir():
            return maps_env

    if 'MOBILE_BASE_REPOSITORY_ROOT' in os.environ:
        repo_env = Path(os.environ['MOBILE_BASE_REPOSITORY_ROOT']).resolve() / 'maps'
        if repo_env.is_dir():
            return repo_env

    candidates = [
        Path.cwd() / 'maps',
        Path('/workspaces/mobile_base/maps'),
        Path(__file__).resolve().parent.parent.parent.parent / 'maps',
    ]

    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()

    return (Path.cwd() / 'maps').resolve()


def resolve_site_dir(site_name: str, custom_maps_root: Optional[Path] = None) -> Path:
    """
    Resolve the directory path for a given site name.

    :param site_name: Name of site under maps/ (e.g. 'test_site') or explicit directory path.
    :param custom_maps_root: Optional root directory to search under instead of default.
    :return: Resolved Path to the site directory.
    :raises ValueError: If site_name is empty.
    :raises FileNotFoundError: If site directory cannot be found.
    """
    cleaned = site_name.strip()
    if not cleaned:
        raise ValueError('Site name cannot be empty.')

    explicit_path = Path(cleaned)
    if explicit_path.is_dir():
        return explicit_path.resolve()

    maps_root = custom_maps_root.resolve() if custom_maps_root else find_maps_root()
    candidate = (maps_root / cleaned).resolve()
    if candidate.is_dir():
        return candidate

    raise FileNotFoundError(
        f"Site '{cleaned}' directory not found at '{candidate}' "
        f"(searched in maps root: '{maps_root}')."
    )


def resolve_navigation_resources(
    site_name: str = '',
    map_override: str = '',
    route_graph_override: str = '',
    custom_maps_root: Optional[Path] = None,
) -> Tuple[str, str]:
    """
    Resolve map and route_graph paths following explicit override > site resolution.

    :param site_name: Site identifier under maps/ (e.g. 'test_site').
    :param map_override: Explicit CLI override for map yaml file.
    :param route_graph_override: Explicit CLI override for route graph GeoJSON file.
    :param custom_maps_root: Optional custom maps root for testing.
    :return: Tuple of (resolved_map_path, resolved_route_graph_path).
    :raises ValueError: If neither valid site nor map override is provided.
    :raises FileNotFoundError: If a specified or resolved file does not exist.
    """
    map_override_clean = map_override.strip()
    route_override_clean = route_graph_override.strip()
    site_name_clean = site_name.strip()

    # 1. Resolve map file
    if map_override_clean:
        map_path = Path(map_override_clean).resolve()
        if not map_path.is_file():
            raise FileNotFoundError(
                f"Explicit map file not found: '{map_override_clean}' (resolved: '{map_path}')."
            )
        resolved_map = str(map_path)
    elif site_name_clean:
        site_dir = resolve_site_dir(site_name_clean, custom_maps_root=custom_maps_root)
        map_path = site_dir / 'map.yaml'
        if not map_path.is_file():
            raise FileNotFoundError(
                f"Site '{site_name_clean}' is missing required map file: '{map_path}'."
            )
        resolved_map = str(map_path)
    else:
        raise ValueError(
            "Navigation mode requires either 'site:=<site_name>' "
            "or explicit 'map:=<path_to_map.yaml>'."
        )

    # 2. Resolve route_graph file
    if route_override_clean:
        route_path = Path(route_override_clean).resolve()
        if not route_path.is_file():
            raise FileNotFoundError(
                f"Explicit route_graph file not found: '{route_override_clean}' "
                f"(resolved: '{route_path}')."
            )
        resolved_route = str(route_path)
    elif site_name_clean:
        site_dir = resolve_site_dir(site_name_clean, custom_maps_root=custom_maps_root)
        route_path = site_dir / 'route_graph.geojson'
        resolved_route = str(route_path) if route_path.is_file() else ''
    else:
        resolved_route = ''

    return resolved_map, resolved_route
