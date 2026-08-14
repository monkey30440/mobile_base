# SYS-019 On Route Navigation — Reuse Research

## 1. Research Scope

本筆記研究目前定案的 SYS-019：

> 系統應沿選定 Route Graph route 由 route entry 移動至 route exit，並遵守 Route Graph 所定義的 connectivity、direction 與 availability constraints。

相鄰責任邊界保持分離：

- SYS-013：路線優先之總體策略與禁止純自由空間規劃；
- SYS-014：環境障礙物感知與動態避障；
- SYS-015：路徑追蹤（`FollowPath`）；
- SYS-018：First Mile 階段（起點至 Route Entry 連接）；
- SYS-020：Last Mile 階段（Route Exit 至目標點連接）；
- SYS-021：路網阻塞無法重選路線時之降級邊界處理。

本項聚焦於「在路網主線上行駛（On Route Navigation）」：
1. 自選定的 Route Entry 沿著路網節點與邊（Nodes & Edges）行駛至 Route Exit；
2. 嚴格遵守 Route Graph 之圖論連通性（Connectivity）、單/雙向行駛方向（Direction）與可用性約束（Availability）；
3. 抵達 Route Exit 後順暢交接給 Last Mile 階段。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 1.3.12-1 `nav2_route`（Route Server / `ComputeRoute` / `ComputeAndTrackRoute`） + `nav2_controller`（Controller Server / `FollowPath`） + Local Costmap 避障 |
| Exact Version / Platform | ROS 2 Jazzy／Ubuntu 24.04；Navigation2 / `nav2_route` Jazzy release 1.3.12-1；target image installed versions 尚待確認及固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 沿 Route Graph 拓撲產生的路徑序列行駛；依有向圖（Directed Graph）嚴格約束行駛方向與連通性，防止逆向行駛；在路段不可用或受阻時配合 Route Server 重選可用路徑；抵達 Route Exit 時結束 On Route 階段並交接予 Last Mile |
| Known Constraints | Route Graph 檔案必須合法定義連通性與方向性；AMR 在路網上的循跡貼合度由 local controller 參數（如 lookahead distance, path tolerance）決定；抵達 Route Exit 僅代表主線路網行駛結束，不代表整體導航完成 |
| Uncovered Gap | **None**；不需要自訂圖論循跡引擎或專屬車道保持控制器，標準 `nav2_route` 與 Nav2 Controller 即可完整支援 |
| Configuration / Composition Gap | Route Graph 圖資屬性配置（單向/雙向邊、速度限制等）；Route Server 搜尋權重與可用性判定配置；Controller 循跡參數配置；BT XML 中 On Route 完成至 Last Mile 的順暢串接 |
| Missing Evidence | Target image 之 exact installed versions；單向邊、雙向邊、分岔路口與交叉口之循跡與方向約束驗證；中途路網阻塞觸發重新選路或失敗回報驗證；Route Exit 抵達判斷與交接 Last Mile 之平順度測試 |
| MVP Change Candidate | `None` |

成熟方案已原生具備基於圖論路網的路由計算、方向約束保證與路徑追蹤能力，完全滿足 SYS-019 需求。

## 3. On Route Principles and Constraint Enforcement

在 Navigation2 體系下，On Route 行駛之約束保證機制如下：

```text
[Route Entry]
     │
     ▼
[nav2_route::RouteServer] ── (Directed Graph Search)
     │                     ├── Connectivity: 僅沿定義的 Edge 連通走
     │                     ├── Direction: 嚴格依 Directed Edge 方向行駛（禁止逆向）
     │                     └── Availability: 排除被標記為 Disabled / Blocked 之邊
     ▼
[Route Path Generation] ── (由 Route Edges 生成 high-density Path)
     │
     ▼
[nav2_controller::FollowPath] ── (Controller Server 沿路網循跡)
     │
     ▼
[Route Exit Reached] ── (交接予 SYS-020 Last Mile)
```

1. **連通性與方向約束（Connectivity & Direction Constraints）**：
   - `nav2_route` 內部以有向圖資料結構儲存路網。
   - 圖論搜尋演算法（A* / Dijkstra）僅會在具備合法有向 Edge 的節點間建立路徑，因此產生的軌跡天然保證單向行駛與拓撲連通性，不會產生逆向或跨越未連通區域的軌跡。
2. **可用性約束（Availability Constraints）**：
   - Route Server 支援動態可用性（Dynamic Availability）標記與 Cost 權重。
   - 當某路段被停用、或在導航過程中因障礙物長時間阻塞時，Route Server 可重新計算繞道路線；若路網已無其他替代路徑可通往 Route Exit，則終止 On Route 移動並觸發 SYS-021。
3. **階段交接（Stage Handover）**：
   - AMR 沿路徑追蹤至 Route Exit 點時，On Route 階段宣告成功完成；
   - 行為樹自動將控制權移交至 Last Mile 階段（SYS-020），負責後續抵達最終目標點。

## 4. Responsibility and Requirement Boundary

| 需求項目 | 責任範圍 | 與 On Route (SYS-019) 的邊界 |
|---|---|---|
| **SYS-013** | **Strategy**：路線優先總體策略 | 引導導航採用路網行駛，並協調階段 |
| **SYS-018** | **First Mile**：起點至 Route Entry 銜接 | 將 AMR 帶至 Entry 點後，由 SYS-019 接手 |
| **SYS-019** | **On Route**：路網主線移動與約束遵守 | 負責 Entry 到 Exit 之間沿路網的移動與方向保證 |
| **SYS-020** | **Last Mile**：Route Exit 至目標點銜接 | 在 AMR 抵達 Exit 點後，自 SYS-019 接手完成最後移動 |
| **SYS-021** | **Fallback**：無可用路線之降級處理 | 當路網中途受阻且無可用替代路網時接手處理 |

## 5. Configuration and Evidence Requirements

### Configuration / composition

- 配置 Route Graph 之圖資檔案（包含正確的單/雙向 Edge 定義與節點座標）；
- 配置 Controller Server 參數（如 DWB 或 Regulated Pure Pursuit 的 path distance bias 與 lookahead distance），使 AMR 精準貼合路網軌跡；
- 設計 BT XML 中 On Route 節點（`FollowPath` 或 `ComputeAndTrackRoute`）並串接至 Last Mile 子樹；
- 配置路網中途受阻時的重規劃與失敗傳遞邏輯。

### Integration and real-hardware evidence

- 記錄 target image 之 exact versions（ROS 2 Jazzy、`nav2_route` 1.3.12-1、`nav2_controller` 1.3.12-1）；
- **方向性驗證**：在單行道測試路段下發順向與逆向導航目標，驗證 AMR 絕不逆向穿行，必繞行合法路網；
- **連通性驗證**：在包含直線、轉彎、分岔與十字路口的路網拓撲上進行長距離循跡，驗證車體平穩貼合路網；
- **阻塞重選與失敗驗證**：在路網主線上放置障礙物，驗證系統能自動重新選路；在完全封死時回報失敗並由 SYS-021 處理；
- **Exit 抵達與交接測試**：量測抵達 Route Exit 後順暢交接給 Last Mile 的時序與車體姿態平順度。

## 6. Primary-source Evidence

### 6.1 `nav2_route` Route Server and Graph Search

- **Evidence Type:** official upstream source and interfaces
- **Sources:** [`nav2_route` package](https://github.com/ros-navigation/navigation2/tree/1.3.12/nav2_route)；[`route_server.cpp` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_route/src/route_server.cpp)；[`ComputeRoute.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/ComputeRoute.action)
- **Exact Version / Revision:** Navigation2 / `nav2_route` 1.3.12 / Jazzy release 1.3.12-1
- **Observed Scope:** Graph-based path generation, directed edge traversal, and route constraint handling.
- **Access Date:** 2026-08-15

### 6.2 Controller Server Path Tracking along Route

- **Evidence Type:** official upstream source
- **Sources:** [`controller_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_controller/src/controller_server.cpp)；[`FollowPath.action` at 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_msgs/action/FollowPath.action)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** Path tracking, obstacle avoidance on local costmap, and goal progression.
- **Access Date:** 2026-08-15

## 7. Recommended 04 Record

```text
SYS-019 On Route Navigation
Candidate Mature Solution: ROS 2 Jazzy Navigation2 1.3.12-1 nav2_route (Route Server / ComputeRoute) + nav2_controller (Controller Server / FollowPath) + Local Costmap avoidance
Coverage Status: Fully Covered
Covered Scope: executing movement along selected Route Graph edges from Route Entry to Route Exit; strictly enforcing directed graph connectivity and direction constraints; handling edge availability and obstacle rerouting; handing off to Last Mile stage upon reaching Exit
Custom Behavior Gap: None
Configuration / Composition Gap: Route Graph graph topology and one-way/bi-directional attributes; Route Server search and availability scoring; controller path-tracking tuning; BT XML stage handoff to Last Mile
Evidence Gap: installed versions; directional constraint verification on one-way lanes; multi-segment topological traversal; mid-route obstacle rerouting/failure; smooth stage handoff to Last Mile
MVP Change Candidate: None
```
