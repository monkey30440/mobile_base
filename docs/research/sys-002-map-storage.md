> [!WARNING]
> **HISTORICAL / NON-AUTHORITATIVE**
>
> This document is retained for historical traceability only. It does not define the current system architecture, requirements, operational procedure, or verification authority. Use `docs/README.md` to locate the current canonical documentation.

# SYS-002 Map Storage — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-002 儲存地圖**：系統應將建圖結果儲存為 Map Package；無法儲存 Map Package 時，系統應回報失敗及原因。

SYS-002 只判定一次 SaveMap step：把 SYS-001 的 Occupancy Grid 寫成 Map Package，並在該步驟失敗時回報失敗與原因。它不要求寫完後重新讀回，也不負責其他 mapping step 的結果。

依 01–03 的資源分類，`Map Package`、`Route Graph` 與 `Station Catalog` 是分離的 Navigation Resources。目前 Map Package 的 repository convention 是每個場域使用一個人工命名的目錄，目錄內固定為：

```text
map.pgm
map.yaml
```

因此 `route_graph.geojson`、`stations.yaml`、Navigation configuration、SYS-024 read-back validation 均不納入 SYS-002。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy `nav2_map_server` 的 `map_saver_cli` 或 lifecycle `map_saver`／`nav2_msgs/srv/SaveMap` |
| Exact Released Version | ROS 2 Jazzy `nav2_map_server` 1.3.12-1；target image 的實際安裝版本仍待確認與固定 |
| Coverage Status | **Fully Covered** |
| Covered Scope | 從指定的 `nav_msgs/msg/OccupancyGrid` topic 取得地圖；依指定 basename、format、mode 與 thresholds 寫出 image 與 YAML；以 boolean／process result 回報成功或失敗，並透過原生 ROS logs 回報失敗原因 |
| Custom Behavior Gap | `None`；目前 requirement 未要求 structured error code、錯誤 taxonomy、原子寫入或自動復原 |
| Configuration / Composition Gap | 選定 authoritative map topic；人工建立／選擇場域目錄；固定 basename `map`；明確指定 PGM/trinary/threshold/timeout；確保 filesystem path 可寫且持久；選定 CLI 或 lifecycle service 操作方式 |
| Missing Evidence | target image installed version；真機 map topic/QoS/freshness；正常寫入；no-map timeout、invalid parameters、目錄／權限／filesystem failure 的 result 與 log；同名 overwrite 與 partial residue handling |
| MVP Change Candidate | `None` |

判為 `Fully Covered` 的關鍵是：SYS-002 要求「失敗及原因」，但沒有要求原因必須放在 service response、使用自訂 enum，或可由上層程式結構化解析。Nav2 的 service response／CLI process result 提供成功或失敗，原生 error logs 說明失敗所在；兩者合起來已滿足目前的最小 observable failure contract。

若未來要求上層程式收到 structured reason code、原子替換或自動清除殘留檔案，才會產生新的 custom gap；不可在本 assessment 預先加入。

## 3. Direct Mature Capability

Jazzy `nav2_map_server` 將地圖功能拆成：

- `map_saver`：訂閱一個 Occupancy Grid，透過一次性 CLI 或 lifecycle `SaveMap` service 儲存；
- `map_io`：將 Occupancy Grid 寫成 image 與 YAML metadata；
- `map_server`：讀取已存地圖，屬 SYS-024 read-back validation，不在本項判定。

目前人工管理方式可直接使用標準參數：

```text
selected directory: maps/<site>/
map_url / basename: maps/<site>/map
image_format: pgm
map_mode: trinary

result:
maps/<site>/map.pgm
maps/<site>/map.yaml
```

不同場域使用不同目錄名稱、目錄內固定同名檔案，是 path selection 與操作規則；它不需要自製 file writer 或 Map Package manager。標準 saver 不建立 Route Graph、Station Catalog 或 parent directory，而 SYS-002 也沒有要求這些行為。

## 4. Failure-and-Reason Contract

### 4.1 Lifecycle `SaveMap`

`nav2_msgs/srv/SaveMap` request 可指定 map topic、map URL/basename、image format、map mode 與 thresholds；response 只有：

```text
bool result
```

`map_saver` 將 `saveMapTopicToFile()` 的 boolean 直接寫入 response。原因由相同 node 的原生日誌提供：

| Failure condition | Result | Native reason evidence |
|---|---|---|
| timeout／沒有收到 map | `false` | `Failed to spin map subscription` |
| threshold 不合法 | `false` | `map_io` 先記錄具體 threshold constraint，接著記錄 `Failed to write map for reason: Incorrect thresholds` |
| image format 不可用 | 視 fallback/write 結果 | 記錄 format 不可用與 fallback；若仍無法寫入則回傳 `false` |
| directory、permission、disk 或 encoder exception | `false` | `map_io` 記錄 `Failed to write map for reason: <exception>`；外層記錄 save failure |
| 其他 caught exception | `false` | `Failed to save the map: <exception>` |

原生日誌有些原因是技術層級描述，例如 timeout 分支寫成 map subscription 未完成，而不是專案自訂的中文 taxonomy。但目前 SYS-002 只要求可回報原因，沒有要求格式或分類；因此不需以此為由增加 adapter。

### 4.2 `map_saver_cli`

CLI 使用同一個 `MapSaver::saveMapTopicToFile()` 能力與相同 ROS logs。其命令列參數 parser 會針對無效 arguments 輸出錯誤／usage；儲存失敗則由 saver 回傳失敗結果並留下上述原因日誌。部署時應把 CLI process completion/result 與 stderr/stdout logs 一併保留，不能只看檔案是否碰巧存在。

若系統需要由另一個 ROS node 程式化取得結果，應使用 lifecycle `SaveMap` service；若 v0.1 是人工由終端存圖，CLI 已是足夠的標準操作介面。兩者都不需要自製 storage behavior。

## 5. File and Partial-write Semantics

Nav2 1.3.12 `map_io` 的寫入順序是：

1. 寫 `<basename>.<format>` image；
2. 再寫 `<basename>.yaml` metadata。

YAML 會包含 image filename、mode、resolution、origin、negate、occupied/free thresholds。相同 basename 會直接寫向相同路徑，原生實作沒有「已存在即拒絕」或 transactional／atomic directory commit。

這代表第二步失敗時，目錄可能保留新 image 與舊 YAML，或其他 partial residue。這不改變 SYS-002 的 coverage，因為 saver 已回傳 failure 並記錄原因，而 requirement 沒有要求 atomic persistence。部署仍必須遵守：

- `false` 或非成功 process result 時，不得宣告 Map Package 已成功儲存；
- 同名覆寫是否允許須成為明確操作規則；
- failure 後的殘留檔案不得被當成有效 package；
- read-back validation 留給 SYS-024，而不是在 SYS-002 增加自製 transaction layer。

如果未來 normative 要求「舊 package 在新 save 失敗後仍必須完整可用」或「兩檔必須原子切換」，應先新增／修正 requirement，再評估 staging directory、rename 或其他最小 adapter。

## 6. `slam_toolbox` Persistence Boundary

`slam_toolbox` 2.8.5 的兩種 persistence 不應混淆：

| Interface | 保存內容 | 與 SYS-002 的關係 |
|---|---|---|
| `/slam_toolbox/save_map` | pose graph rasterized 後的 navigation image map；官方稱為 map-server/map-saver wrapper | 可保存基本 image map，但介面較窄 |
| `/slam_toolbox/serialize_map` | pose graph、scan data 與 metadata | 供繼續建圖、slam_toolbox localization 或離線 graph 操作；不是目前 `map.pgm` + `map.yaml` Map Package |

直接 reuse candidate 建議仍採 `nav2_map_server`，因其 SaveMap 明確接收任意 authoritative Occupancy Grid topic，且可設定完整輸出格式；這使 storage capability 不依附特定 SLAM implementation。`.posegraph`／`.data` 不應在沒有 multi-session mapping requirement 時加入 Map Package。

## 7. Evidence Required Before Acceptance

- 在 target image 記錄並固定 `nav2_map_server` 實際安裝版本；
- 證明 saver 可取得 selected authoritative Occupancy Grid，並確認 topic、QoS、freshness 與非空尺寸；
- 在非 template 場域目錄產生非空 `map.pgm` 與 `map.yaml`，且 YAML 的 `image: map.pgm`、resolution、origin、mode、thresholds 正確；
- 證明 container 中的目標 directory／bind mount／volume 可寫且可持久保存；
- 分別注入 no-map timeout、invalid thresholds、目錄不存在、permission denied／filesystem exception，確認 result 為失敗且 operator 可看到原因；
- 測試同名 overwrite 與 image 寫完、YAML 失敗的 partial residue policy；
- 若採 CLI，驗證 automation／operator 不會忽略失敗 process result 或 error logs；若採 service，驗證 caller 不會把 `result=false` 當成成功；
- 由 SYS-024 另行完成 read-back validation。

目前 `maps/template/map.pgm` 與 `map.yaml` 都是 0-byte placeholder，只證明預期 layout，不是 SYS-002 PASS evidence。現有 `docs/m1_bringup_validation` 聚焦 M1 drive bringup，也沒有 map-storage runtime evidence。

## 8. Primary-source Evidence

### 8.1 Official Jazzy package contract

- **Evidence Type:** ROS 2 Jazzy generated package documentation
- **Source:** [`nav2_map_server` Jazzy 1.3.12 documentation](https://docs.ros.org/en/jazzy/p/nav2_map_server/)
- **Exact Version / Revision:** `nav2_map_server` 1.3.12
- **Observed Scope:** documents `map_saver_cli`, lifecycle `map_saver`, SaveMap service, OccupancyGrid support and MapIO save/load separation; includes a SaveMap example with map topic, basename, PGM, trinary and thresholds.
- **Limitations:** does not prove this project's target image installation, filesystem or failure-path behavior.
- **Access Date:** 2026-08-14

### 8.2 Exact saver result and reason behavior

- **Evidence Type:** upstream Jazzy API/source
- **Sources:** [`nav2_msgs/srv/SaveMap`](https://docs.ros.org/en/ros2_packages/jazzy/api/nav2_msgs/srv/SaveMap.html)；[`Nav2 Jazzy map_saver.cpp`](https://api.nav2.org/nav2-jazzy/html/map__saver_8cpp_source.html)；[`MapSaver` Jazzy API](https://docs.ros.org/en/jazzy/p/nav2_map_server/generated/classnav2__map__server_1_1MapSaver.html)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12
- **Observed Scope:** service callback directly returns the saver boolean; map subscription failure returns false and logs an error; map write false logs failure; caught exceptions return false and include `e.what()` in the log.
- **Limitations:** response does not carry structured reason text or reason code; current SYS-002 does not require either.
- **Access Date:** 2026-08-14

### 8.3 Exact MapIO format and exception behavior

- **Evidence Type:** upstream source code
- **Source:** [`navigation2` 1.3.12 `map_io.cpp`](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_map_server/src/map_io.cpp)
- **Exact Version / Revision:** upstream tag `1.3.12`
- **Observed Scope:** validates thresholds/format, writes image before YAML, emits YAML metadata, catches write exceptions, logs the exception reason and returns false.
- **Limitations:** writes are sequential rather than transactional; overwrite and residue policy remain deployment obligations unless a stronger requirement is added.
- **Access Date:** 2026-08-14

### 8.4 CLI interface

- **Evidence Type:** upstream source and official README
- **Sources:** [`Navigation2` 1.3.12 `main_cli.cpp`](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_map_server/src/map_saver/main_cli.cpp)；[`nav2_map_server` README](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_map_server/README.md)
- **Exact Version / Revision:** upstream tag `1.3.12`
- **Observed Scope:** defines `map_saver_cli` arguments for topic, basename, thresholds, format and mode, and uses the same map saver capability for one-shot storage.
- **Limitations:** deployment must verify and preserve the actual process result/log behavior in its target environment.
- **Access Date:** 2026-08-14

### 8.5 `slam_toolbox` persistence distinction

- **Evidence Type:** upstream official README and service definition
- **Sources:** [`slam_toolbox` 2.8.5 README](https://github.com/SteveMacenski/slam_toolbox/tree/2.8.5)；[`SerializePoseGraph.srv`](https://github.com/SteveMacenski/slam_toolbox/blob/2.8.5/srv/SerializePoseGraph.srv)
- **Exact Version / Revision:** upstream tag `2.8.5`
- **Observed Scope:** distinguishes the image-map `save_map` wrapper from serialized pose-graph data for continued mapping/localization/offline operations.
- **Limitations:** neither interface supplies Route Graph, Station Catalog or project directory policy.
- **Access Date:** 2026-08-14

### 8.6 Jazzy release metadata

- **Evidence Type:** ROS build-farm status
- **Source:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `nav2_map_server` 1.3.12-1 for Ubuntu Noble/Jazzy
- **Observed Scope:** confirms the assessed package version exists in the Jazzy binary release line.
- **Limitations:** availability does not identify the version installed in the target image.
- **Access Date:** 2026-08-14

## 9. Recommended 04 Record

```text
SYS-002 Map Storage
Candidate Mature Solution: ROS 2 Jazzy nav2_map_server map_saver_cli or lifecycle SaveMap service
Coverage Status: Fully Covered
Custom Behavior Gap: None; current requirement does not require structured reason codes or atomic persistence
Configuration / Composition Gap: authoritative OccupancyGrid topic; manually selected per-site directory; fixed basename map; explicit PGM/trinary/threshold/timeout; persistent writable filesystem; CLI or lifecycle integration; failure result and log observability
Evidence Gap: pinned target version; successful map.pgm/map.yaml; QoS/freshness; no-map/invalid-parameter/filesystem failure reports; overwrite and partial-residue handling; read-back deferred to SYS-024
MVP Change Candidate: None
```

建議完成 SYS-002 coverage record 後才進入 SYS-006；不要在本項提前核准 read-back validation，或 Route Graph／Station Catalog 的建立與管理。
