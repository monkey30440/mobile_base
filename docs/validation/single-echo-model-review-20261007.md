# Single-echo/model independent review

User-approved fixed point f591f4e; pinned target a589477. Command:
`git diff f591f4e...a589477`. New a589477 changes and interactions were reviewed
by separate agents. Earlier covariance/EKF work already has its independent report.

## Standards

Hard violations/concrete bugs: **0**. AGENTS/domain rules respected. Installed
model extraction, explicit yaw, native CLI boolean correction and single-RSP
sensor composition have no identified correctness defect for the supplied URDF.
Its footprint source transform is exactly zero rotation and z=-0.256 m; the
implemented reversed z=+0.256 m is correct.

Nonblocking P3 heuristic: **1**, possible duplicated geometry. `prepare_model.py`
assigns `xyz='0 0 0.256'`, duplicating a value owned by the source URDF. A future
platform revision could diverge; minimal future improvement is deriving inverse
translation and rejecting unsupported rotation. This is not a current geometry
error. Current platform and native TF test agree; no general transform framework
or unrelated refactor is introduced in this change.

## Spec

Actionable deviations/scope-creep defects: **0**. Revised #32/#37 and latest user
instructions specify native LAST and both `_1` scan frames, which match SOPAS and
real scan evidence. No decoder/merger/header rewrite. Source base subtree,
normalized footprint, optical children and native RSP meet the stationary scope.

Intentionally pending: final operator Foxglove stability/physical alignment;
dynamic wheel/caster/suspension TF from real feedback; real odometry/IMU fusion,
precise calibration and full model/control bringup ownership. Native shutdown,
reconnect/power-cycle, long-duration behavior and Orin acceptance remain partial.
No #37/#38 closure or calibrated/full-V1 claim is justified by this stage.

Summary: Standards 0 bugs + 1 nonblocking heuristic; Spec 0 actionable findings.
