# V1 occupancy map / route graph native data contract research

Research for #33, supporting decision #34 and reopened map #18; 2026-10-02. This is evidence, not an adopted product decision. Ignore former architecture and project runtime. Authority: Nav2 1.3.13, exact commit `f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501`. Method: pinned source / existing tests / examples inspection; no local ROS execution, hardware verification or calibration performed.

## CONFIRMED — format and coordinate semantics

The default parser is `nav2_route::GeoJsonGraphFileLoader`. Its input is GeoJSON features: Point nodes with numeric `properties.id` and `geometry.coordinates[0:2]`; directed LineString / MultiLineString edges with numeric `properties.id`, `startid`, `endid`. Optional frame, costs, operations and metadata follow upstream conventions. Edge geometry selects edge features but is not used to generate additional curved path points: endpoints refer to nodes. README requires unique identifiers; parser does not explicitly reject duplicate node / edge IDs. Node-ID lookup overwrites duplicate entries and edges append. A valid JSON or successful load is therefore not proof of a semantically well-formed route network. No filename is hardcoded and extension is not checked: native GeoJSON content does not imply the required basename `route_graph.geojson`.

Sources: [parser](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/plugins/graph_file_loaders/geojson_graph_file_loader.cpp), [format conventions](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/README.md#graph-formats), [sample](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/graphs/sample_graph.geojson), [types](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/include/nav2_route/types.hpp).

Nodes hold Cartesian x/y, default frame `map`; optional frame is transformed through TF into configured `route_frame` (default `map`). There is no longitude/latitude projection conversion. Graphs for V1 therefore need coordinates consistent with the occupancy map's metric frame, including its origin/resolution/yaw; same frame name alone does not establish same map revision. Map YAML image paths beginning with `/` are absolute; others resolve relative to the YAML file's directory. Map IO reads resolution in metres/cell and origin [x,y,yaw], uses yaw as a Z rotation, flips raster vertically into ROS map indexing. This native YAML→image relationship is separate from graph selection.

Sources: [graph transform](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/graph_loader.cpp), [map IO](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_map_server/src/map_io.cpp).

## CONFIRMED — configure, reload, failure boundaries

The actual native server parameter is **`graph_filepath`**, not `route_graph_filepath`. A bringup launch may choose an argument name, but that is a separate interface decision. Nonempty parameter is parsed/transformed during configure; parser returns false for nonexistent files, JSON parse errors, missing node or edge populations. Missing required JSON properties can throw; dangling start/end references explicitly throw `NoValidGraph`. Configure catches exceptions or false and returns FAILURE. Frame-transform failure also rejects loading. Explicit nonempty graph input and configure-success are usable native acceptance points for these checks.

An empty configure filepath intentionally succeeds with no graph; route actions subsequently reject an empty graph. Thus lifecycle configured alone cannot prove V1 has loaded required route data. Native logs identify path/load errors, and activation publishes graph visualization. There is no explicit successful loaded-node-count log or automatic map/graph pairing status.

Sources: [loader](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/graph_loader.cpp), [server configure/action checks](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/route_server.cpp), [native parser tests](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/test/test_geojson_graph_file_loader.cpp), [native transform and empty-input tests](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/test/test_graph_loader.cpp).

`route_server/set_route_graph` accepts a filepath and returns a success boolean. The server **clears old graph and ID map before attempting replacement**. Failure is not atomic rollback; partially populated state can remain after parser/transform errors. This API does not change the map_server occupancy map. Live coordinated map/graph switching, transactionality or retained last-good dataset must not be credited to native behavior. For an MVP staged bringup, selecting a prepared pair before configure avoids requiring new dataset-switching machinery.

Sources: [SetRouteGraph service](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_msgs/srv/SetRouteGraph.srv), [reload implementation](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/src/route_server.cpp).

## CONFIRMED — pairing gap and manual preparation

The inspected map loader and graph loader independently consume their inputs. Neither establishes occupancy-map identity/revision, dataset manifest, checksum matching, graph/map association, geospatial alignment or AMR clearance. Native parser checks do not guarantee finite sensible coordinates, unique IDs, connected required routes, graph lanes consistent with free space, or actual navigability. Costmap-based runtime scoring concerns current route feasibility, not artifact provenance. Those are distinct responsibilities; native success should not be called full dataset validation.

Pinned README describes predefined graph input and includes real graph examples; upstream graph scripts aid generation, including shapefile export. Official [QGIS tutorial](https://docs.nav2.org/rolling/tutorials/general_tutorials/route_server_tools/route_graph_generation/route_graph_generation/) describes manual annotation on an occupancy raster and coordinate alignment. It is an authoring candidate, not a required product tool. [Pinned exporter](https://github.com/ros-navigation/navigation2/blob/f4108e5b1c2bce804a1aa0c7be6673a8eb4a1501/nav2_route/graphs/scripts/export_shapefiles.py) supports this evidence. Current [rolling tool index](https://docs.nav2.org/rolling/tutorials/general_tutorials/route_server_tools/) also lists RViz/LIF/automatic tools; rolling documentation does not establish their availability or compatibility in the chosen Jazzy release. No additional graph authoring dependency is selected by this research.

## Architecture questions for decision, not inferred requirements

1. Explicitly assign offline graph creation/review and pair selection to Operator / engineering; clarify Mapping does not automatically create graph.
2. Define one **logical Navigation dataset selection** as a particular occupancy-map artifact revision plus a particular graph revision, with enough recorded identity to reproduce the pair. Logical association does not imply a mathematical bijection: several reviewed graph revisions may target the same map.
3. Define map/graph coordinate agreement, intended route topology/direction and AMR clearance as preparation/review responsibility; native checks remain responsible only for their demonstrated parsing/loading/TF scope.
4. Define failed save/load/preparation/pair-confirmation behavior: data not accepted or Navigation not usable, attributable native errors, no silent cross-pair fallback or graphless completion. Distinguish data acceptance from Localization and controller activation.
5. Changing map image/YAML geometry/frame or graph requires reconfirming the selected association and compatibility. Do not introduce online dataset management, automatic versioning or a custom validator without a confirmed requirement.
6. Decide external traceability result, not timestamp directory, fixed filename, launch argument spelling, directory creation, path resolver or manifest implementation. Native diagnostics alone cannot detect semantic mispairing; a manual contract must explicitly own that limit if selected.

## Evidence classifications and limits

- **CONFIRMED:** Native GeoJSON content, graph_filepath configure/load semantics, relative map image paths, native error scope, nontransactional reload, no native occupancy pairing in inspected loaders.
- **UNRESOLVED:** Product association/revision/ownership/failure contract awaits decision #34. Optional authoring-tool compatibility beyond pinned scripts not established; not required to choose architecture now.
- **REQUIRES HARDWARE VALIDATION:** Authored graph corresponds to actual traversable lanes and robot footprint, localization quality, route entry/exit and accepted travel behavior. No source inspection proves these.
- **REQUIRES CALIBRATION:** Actual map/frame geometry and robot footprint/extrinsics/odometry parameters when measurement is needed; no new numerical calibration values proposed.

Research completes native facts needed for decision. It does not adopt a directory layout, custom runtime manager, serializer, automated validator or online dataset switch.

## User steering during research

User subsequently requested Navigation select one directory containing map.pgm, map.yaml and a GeoJSON route graph. This is now an explicit requested Operator contract rather than a consequence of native formats. Native servers still accept independent paths; a directory-to-native-path mapping would be a launch/configuration integration responsibility, not evidence for a custom runtime dataset manager. Exact graph filename awaits the driving decision; timestamp naming is not inferred. This note does not resolve decision #34.
