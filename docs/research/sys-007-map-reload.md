# SYS-007 Map Load — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-007 載入地圖**：系統應於 Navigation Mode 啟動期間載入所選定之 Map Package，並提供其中的二維 Occupancy Grid 給地圖定位與導航功能使用；Map Package 無法載入時，系統不得進入 navigation-ready 狀態，並應回報原因。

目前 Map Package 依 SYS-002 邊界，是人工選定之單一場域目錄內的固定檔名：

```text
maps/<site>/map.yaml
maps/<site>/map.pgm
```

本需求只處理 Navigation Mode 啟動時載入所選 Map Package。v0.1 沒有 runtime 換圖或 navigation執行中hot-switch需求。`route_graph.geojson`、`stations.yaml`與Navigation configuration是分離資源，由使用者依MVP操作規則在啟動前人工確認；SYS-010另行覆蓋AMCL標準pose與`map -> odom`，均不得混入本項coverage。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `nav2_bringup/localization_launch.py map:=<selected map.yaml>`，組合 `nav2_map_server` lifecycle `map_server`、`nav2_lifecycle_manager`與`nav2_amcl` |
| Exact Released Version | Navigation2 Jazzy 1.3.12 / Ubuntu binary release 1.3.12-1；target image實際安裝版本仍待確認與固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | launch argument把所選`map.yaml`寫入`map_server.yaml_filename`；map server在configure期間解析YAML/image並建立Occupancy Grid；lifecycle manager僅在map server與AMCL都成功configure後才activate；active map server以latched QoS發布`nav_msgs/msg/OccupancyGrid`，供AMCL與後續Nav2 map consumers使用；載入失敗會記錄原因、使map server configure失敗並中止localization managed-node bringup |
| Custom Behavior Gap | `None`；不需要自製map parser、loader、publisher或AMCL map adapter |
| Configuration / Composition Gap | Navigation Mode啟動前選定per-site `map.yaml`；以完整路徑傳入`map:=...`；固定map topic/frame與transient-local QoS；把localization lifecycle bringup成功及有效`/map`列為navigation-ready必要條件 |
| Missing Evidence | target image installed version；實際非空場域Map Package；正常啟動時map server與localization lifecycle ACTIVE及`/map`內容/QoS；YAML不存在、metadata錯誤、image不存在/損壞時的原因log、lifecycle startup failure，以及navigation-ready維持false |
| MVP Change Candidate | `None` |

`Fully Covered`表示成熟Nav2元件已提供SYS-007所要求的啟動載入、標準Occupancy Grid發布及失敗阻止localization bringup機制。system仍須把這些標準狀態組合成navigation-ready prerequisite；這是configuration/composition contract，不是custom map-loading behavior。

## 3. Standard Navigation Mode Startup Path

建議v0.1直接使用官方localization launch的標準入口：

```bash
ros2 launch nav2_bringup localization_launch.py \
  map:=/absolute/path/to/maps/<site>/map.yaml
```

其啟動關係是：

```text
selected maps/<site>/map.yaml
  -> localization_launch.py map argument
  -> map_server yaml_filename
  -> map_server lifecycle configure: YAML + image -> OccupancyGrid
  -> lifecycle manager activates map_server and AMCL
  -> map_server publishes /map
  -> AMCL and Nav2 map consumers can subscribe
```

Jazzy `localization_launch.py` 明確把 managed nodes 排成 `['map_server', 'amcl']`。當`map` launch argument非空時，不論採separate processes或composition，都把它覆寫到map server的`yaml_filename`。因此場域選擇只需要在啟動前選定一個per-site目錄並傳入其`map.yaml`完整路徑，不需要自製場域registry或resource loader。

## 4. Map Package Parsing and Occupancy Grid Output

`map_server.on_configure()`讀取`yaml_filename`並呼叫MapIO。MapIO以YAML為入口，讀取：

- `image`；
- `resolution`；
- 三元素`origin`；
- `free_thresh`與`occupied_thresh`；
- `negate`；
- 可省略的`mode`，未指定時使用`trinary`。

若`image`是相對路徑，MapIO會相對於`map.yaml`所在目錄解析。因此目前固定layout可直接寫：

```yaml
image: map.pgm
```

成功時，MapIO把image與metadata轉為`nav_msgs/msg/OccupancyGrid`，包含width、height、resolution、origin及cell data。map server在activate後以configured frame（預設`map`）與topic（預設`map`）發布，並使用Nav2 latched publisher QoS：reliable、transient local、history depth 1。AMCL使用相容的reliable/transient-local map subscription，因此即使AMCL在map server發布後開始訂閱，也能收到最後一張地圖。

這已完整提供「給地圖定位與導航功能使用」所需要的標準資料介面。它只代表consumer可取得已載入地圖，不代表AMCL已取得initial pose或定位已有效；後者由SYS-010判定。

## 5. Startup Failure Propagation

### 5.1 Map server reports the load cause

MapIO將啟動載入失敗保留為具體log：

- YAML路徑為空或檔案不存在；
- YAML syntax、必要欄位、欄位型別、origin長度或mode無效；
- image檔案不存在、無法解碼或資料無效。

`map_server.on_configure()`在MapIO失敗時拋出「Failed to load map yaml file」錯誤，使lifecycle configure不成功。啟動路徑不是`LoadMap` service，因此沒有service result code；本需求的「回報原因」由map_io/map_server的標準錯誤log提供。若未來要求結構化錯誤碼API，必須另立requirement，不能從目前文字推導。

### 5.2 Lifecycle manager prevents successful localization bringup

`localization_launch.py`的lifecycle manager依序configure `map_server`、`amcl`。Jazzy lifecycle manager只會在所有managed nodes configure成功後繼續activate；任一節點transition失敗時會：

1. 記錄failed node；
2. 中止其餘startup；
3. 將managed-node state設為`UNKNOWN`；
4. 不宣告「Managed nodes are active」。

因此Map Package載入失敗時，標準localization stack不會成功進入ACTIVE組合狀態，也不會由active map server發布可用`/map`。

### 5.3 Navigation-ready remains a system gate

Nav2沒有一個只靠`localization_launch.py`就代表整個AMR navigation-ready的單一boolean。SYS-007所需的最小system contract是：

```text
navigation-ready requires
  localization managed nodes ACTIVE
  AND selected map OccupancyGrid available on authoritative /map
```

任一條件不成立，就不得把navigation-ready設為true。這是利用標準lifecycle state與map interface建立的composition gate，不需要custom map loader。

此gate只界定Map Package startup load：

- approximate initial pose與AMCL標準定位輸出由SYS-010處理；
- Route Graph 與 Station Catalog 由使用者在啟動前人工選擇與確認。

所以map load成功只是navigation-ready的必要條件，不是充分條件；反過來，map load失敗則足以阻止navigation-ready。

## 6. Out of Scope

`nav2_map_server`另有active-state `nav2_msgs/srv/LoadMap`介面，但目前SYS-007沒有runtime換圖需求，因此本項不把下列內容列入covered scope、configuration或acceptance evidence：

- Navigation Mode運行期間切換場域；
- hot-switch transaction；
- AMCL接收第二張地圖；
- 取消active navigation後換圖；
- 換圖後重新initial pose或重新定位。

這些能力即使upstream存在，也不應成為v0.1義務。若未來新增runtime map switching use case，再另行做requirement與reuse assessment。

## 7. Evidence Required Before Acceptance

至少應在target image完成：

1. 固定並記錄`nav2_bringup`、`nav2_map_server`、`nav2_lifecycle_manager`與`nav2_amcl`實際安裝版本；
2. 以實際非空`maps/<site>/map.yaml`及`map.pgm`執行official localization launch；
3. 確認`map_server`與`amcl`managed lifecycle nodes成功ACTIVE；
4. 驗證authoritative `/map`為非空Occupancy Grid，且frame、width、height、resolution、origin、timestamp與QoS正確；
5. 驗證AMCL可透過標準subscription取得該地圖，但不在此項判定定位品質；
6. 分別測試不存在的YAML、無效metadata、不存在或損壞image；
7. 每一失敗案例都必須看到可診斷的map_io/map_server原因、localization startup未成功ACTIVE，且navigation-ready維持false；
8. 另由SYS-010完成AMCL pose／TF整合證據；其他Navigation Resources採使用者人工確認，不建立system admission gate。

repository目前只有`maps/template/map.yaml`與`map.pgm`的0-byte placeholders，不能作為SYS-007 PASS evidence；現有`docs/m1_bringup_validation`也沒有map-loading runtime evidence。

## 8. Primary-source Evidence

### 8.1 Official Jazzy localization composition

- **Evidence Type:** Navigation2 first-party launch source
- **Source:** [`nav2_bringup/launch/localization_launch.py`](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_bringup/launch/localization_launch.py)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** `map` launch argument、`yaml_filename` override、`map_server`與`amcl`node composition，以及ordered lifecycle node list。
- **Limitations:** launch file不定義完整AMR navigation-ready或其他Navigation Resources相容性。
- **Access Date:** 2026-08-14

### 8.2 Map server lifecycle load and publication

- **Evidence Type:** official Jazzy package documentation and upstream API/source
- **Sources:** [`nav2_map_server` Jazzy 1.3.12 documentation](https://docs.ros.org/en/jazzy/p/nav2_map_server/)；[Map Server configuration](https://docs.nav2.org/configuration/packages/map_server/configuring-map-server.html)；[`MapServer` Jazzy API](https://docs.ros.org/en/jazzy/p/nav2_map_server/generated/classnav2__map__server_1_1MapServer.html)；[`map_server.cpp` Jazzy source](https://api.nav2.org/nav2-jazzy/html/map__server_8cpp_source.html)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12 / binary release 1.3.12-1
- **Observed Scope:** configure-time`yaml_filename`載入、load failure使configure失敗、activate-time latched Occupancy Grid publication。
- **Limitations:** active map publication不表示AMCL已收斂或整個navigation stack ready。
- **Access Date:** 2026-08-14

### 8.3 MapIO format and diagnostic failure causes

- **Evidence Type:** upstream Jazzy source
- **Source:** [`map_io.cpp` Jazzy source](https://api.nav2.org/nav2-jazzy/html/map__io_8cpp_source.html)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12
- **Observed Scope:** relative image path、required metadata、default trinary mode、Occupancy Grid conversion，以及YAML/image exception diagnostics。
- **Limitations:** parser success不驗證地圖品質或AMCL實機定位表現；其他Navigation Resources採人工確認。
- **Access Date:** 2026-08-14

### 8.4 Lifecycle startup failure propagation

- **Evidence Type:** official Jazzy configuration and upstream source
- **Sources:** [Lifecycle Manager configuration](https://docs.nav2.org/configuration/packages/configuring-lifecycle.html)；[`lifecycle_manager.cpp` Jazzy source](https://api.nav2.org/nav2-jazzy/html/lifecycle__manager_8cpp_source.html)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12
- **Observed Scope:** ordered configure/activate；任一managed-node transition失敗即abort startup且不進入ACTIVE managed state。
- **Limitations:** lifecycle manager不提供完整AMR navigation-ready decision；system composition仍須把其成功狀態與authoritative map availability列為必要條件。
- **Access Date:** 2026-08-14

### 8.5 AMCL standard map input

- **Evidence Type:** official Jazzy configuration and upstream source
- **Sources:** [AMCL configuration](https://docs.nav2.org/configuration/packages/configuring-amcl.html)；[`amcl_node.cpp` Jazzy source](https://api.nav2.org/nav2-jazzy/html/amcl__node_8cpp_source.html)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12
- **Observed Scope:** standard`nav_msgs/msg/OccupancyGrid`map input與reliable/transient-local subscription。
- **Limitations:**收到map不等同AMCL已產生新的pose／TF或定位品質已由實機證據確認。
- **Access Date:** 2026-08-14

## 9. Recommended 04 Record

```text
SYS-007 Map Load
Candidate Mature Solution: ROS 2 Jazzy nav2_bringup localization_launch.py with nav2_map_server, nav2_lifecycle_manager, and nav2_amcl
Coverage Status: Fully Covered
Custom Behavior Gap: None
Configuration / Composition Gap: pre-start per-site map.yaml selection; map:= absolute path; map topic/frame/QoS; localization lifecycle ACTIVE and authoritative Occupancy Grid availability are required for navigation-ready
Evidence Gap: pinned target versions; real non-empty Map Package; successful lifecycle/map publication; YAML/metadata/image failure diagnostics; failure keeps localization bringup non-ACTIVE and navigation-ready false
MVP Change Candidate: None
```

建議完成SYS-007 coverage record後才進入SYS-024；不要把runtime換圖、AMCL定位品質或人工Navigation Resource確認加入本項。
