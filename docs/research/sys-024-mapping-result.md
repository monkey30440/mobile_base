# SYS-024 Map Package Read-back — Reuse Research

## 1. Research Scope

本筆記只研究 `03_requirements.md` 的目前定案需求：

> **SYS-024 Map Package Read-back**：系統應於 Map Package 儲存後，確認其中的地圖可重新解析為二維 Occupancy Grid；無法解析時，系統應依標準解析結果回報失敗及原因。

本項只判定儲存後的標準read-back：

```text
stored map.yaml + referenced image
  -> standard parser
  -> LOAD_MAP_STATUS
  -> nav_msgs/msg/OccupancyGrid on success
```

解析成功或失敗完全依成熟套件的標準結果判定，不增加額外的grid內容、品質或可用性acceptance rules。

## 2. Assessment Conclusion

| Field | Assessment |
|---|---|
| Candidate Mature Solution | ROS 2 Jazzy Navigation2 `nav2_map_server` 1.3.12-1 public MapIO `loadMapFromYaml()` |
| Coverage Status | **Fully Covered** |
| Covered Scope | 讀取YAML與其image reference；解析metadata與image；轉換為`nav_msgs/msg/OccupancyGrid`；以public `LOAD_MAP_STATUS`判定success/failure；以原生logs回報YAML／image exception原因 |
| Custom Behavior Gap | `None`；不需要自製parser、額外validation layer、error taxonomy或map server |
| Configuration / Composition Gap | 傳入剛儲存之authoritative `map.yaml` path；確保讀取同一Map Package與persistent filesystem；保留標準status與native logs供operator觀察；read-back流程不activate／publish `/map` |
| Missing Evidence | target installed version；真實package成功解析；各標準failure status與log；同一儲存結果的path identity；read-back沒有`/map` side effect |
| MVP Change Candidate | `None` |

直接呼叫public MapIO function並判讀其return status是一般integration／composition，不是custom behavior。現行requirement已明確採標準解析結果作為判定基準，因此MapIO `LOAD_MAP_SUCCESS`就是SYS-024 success；其他標準status加上native logs就是failure與reason。

## 3. Public MapIO Capability

`nav2_map_server/map_io.hpp` 公開：

```cpp
LOAD_MAP_STATUS loadMapFromYaml(
  const std::string & yaml_file,
  nav_msgs::msg::OccupancyGrid & map);
```

官方README將MapIO描述為object-independent library，可由外部code直接呼叫。`loadMapFromYaml()`依序：

1. 讀取並解析`map.yaml`；
2. 取得`image` path；relative path以YAML所在目錄為基準；
3. 讀取image dimensions與pixels；
4. 依resolution、origin、negate、mode與thresholds轉成Occupancy Grid；
5. 設定map frame、load time與message data；
6. 成功時將結果寫入caller提供的`nav_msgs/msg/OccupancyGrid`並回傳`LOAD_MAP_SUCCESS`。

這已完整提供Map Package到二維Occupancy Grid的read-back。專案不應另寫YAML parser、image decoder或occupancy conversion。

## 4. Standard Parse Results and Native Reasons

MapIO 1.3.12的public `LOAD_MAP_STATUS`為：

| Status | Standard meaning in source | Native log／reason evidence |
|---|---|---|
| `LOAD_MAP_SUCCESS` | YAML與referenced image解析及Occupancy Grid conversion完成 | info log包含image path、width、height與resolution |
| `MAP_DOES_NOT_EXIST` | 傳入的YAML filename為空 | error：YAML filename is empty |
| `INVALID_MAP_METADATA` | YAML讀取、syntax、required key、value type、origin length、mode等解析失敗 | error包含YAML path、line／column（可得時）與`e.what()`；不存在的YAML file在目前實作亦進入metadata exception path |
| `INVALID_MAP_DATA` | referenced image不存在、損壞、無法解碼或image conversion丟出exception | error包含image path與`e.what()` |

標準判定方式為：

```text
LOAD_MAP_SUCCESS       -> read-back success
MAP_DOES_NOT_EXIST     -> read-back failure + standard status/native log
INVALID_MAP_METADATA   -> read-back failure + standard status/native log
INVALID_MAP_DATA       -> read-back failure + standard status/native log
```

requirement未要求另外定義machine-readable reason schema。caller保留enum與同次呼叫的ROS logs即可符合「依標準解析結果回報失敗及原因」。把enum帶到terminal output或operation result是正常interface integration，不形成custom gap。

## 5. Direct MapIO Read-back Without `/map` Side Effects

建議直接呼叫`loadMapFromYaml()`：

- 直接取得完整`LOAD_MAP_STATUS`；
- 成功時直接取得記憶體中的Occupancy Grid；
- 不需要建立MapServer node；
- 不需要進行lifecycle configure／activate；
- 不建立publisher或service；
- 不發布、替換或污染active `/map`。

最小composition為：

```text
input: just-stored map.yaml path
  -> nav2_map_server::loadMapFromYaml()
  -> preserve returned LOAD_MAP_STATUS
  -> preserve native log reason on failure
```

這裡只有標準library call與result forwarding，沒有新增判定邏輯。具體由哪一個後續component呼叫、結果顯示在terminal或其他既有operation interface，屬後續設計，不在reuse assessment指定。

## 6. Why Configure-only MapServer Is Unnecessary

`MapServer::on_configure()`也能以`yaml_filename`觸發MapIO load；失敗時configure丟出exception，底層logs保留原因。未activate時不會發布`/map`。

但configure-only相較direct MapIO call多建立node、parameters、services與publisher，而且`loadMapResponseFromYaml()`是protected。SYS-024只需要read-back，不需要MapServer runtime，因此direct public MapIO API是較小且較直接的成熟reuse seam。

這不是說configure-only無法解析，而是它沒有為本項提供額外必要能力。若後續runtime已有完全隔離的MapServer instance，可使用相同標準load semantics；04不需為read-back引入該node。

## 7. Verification Limitation: Parseable Is Not High-quality

目前normative刻意以標準parser結果為準。因此下列情況可能通過`LOAD_MAP_SUCCESS`，但仍需在其他verification活動被發現：

- 地圖範圍太小或沒有涵蓋完整場域；
- 牆面重影、破碎或幾何扭曲；
- resolution、origin或threshold雖格式合法，但不適合實際部署；
- image內容格式正確，但導航價值低。

這些是map quality／deployment fitness limitation，不是SYS-024 parse failure。04不可自行把quality judgement加入read-back success條件，也不可因標準parser不評估品質而把coverage降為Partial。

## 8. Evidence Required Before Acceptance

- 固定並記錄target image實際安裝的`nav2_map_server` version；
- 對剛儲存的真實`map.yaml`執行direct MapIO read-back，確認`LOAD_MAP_SUCCESS`並得到Occupancy Grid message；
- 以empty YAML path驗證`MAP_DOES_NOT_EXIST`與native reason；
- 分別注入YAML file不存在、syntax錯誤、required metadata缺失／type錯誤、origin length錯誤與invalid mode，確認`INVALID_MAP_METADATA`及reason；
- 分別注入image不存在、損壞與無法解碼，確認`INVALID_MAP_DATA`及reason；
- 證明read-back使用的path指向剛儲存的同一Map Package，而非template、舊場域或其他basename；
- 證明read-back過程沒有啟動MapServer publisher、沒有發布或替換active `/map`；
- 另行記錄可解析但品質不佳的測試限制，且不誤報為parser failure。

目前`maps/template/map.pgm`與`map.yaml`都是0-byte placeholder，預期會回傳標準metadata或data failure，不是read-back PASS evidence。

## 9. Primary-source Evidence

### 9.1 Public MapIO API and status enum

- **Evidence Type:** upstream Jazzy API/source
- **Sources:** [`map_io.hpp` Jazzy source](https://api.nav2.org/nav2-jazzy/html/map__io_8hpp_source.html)；[`nav2_map_server` Jazzy documentation](https://docs.ros.org/en/jazzy/p/nav2_map_server/)
- **Exact Version / Revision:** Navigation2 Jazzy 1.3.12 / Ubuntu binary release 1.3.12-1
- **Observed Scope:** exposes object-independent `loadMapFromYaml(yaml, OccupancyGrid&)` and standard `LOAD_MAP_SUCCESS`、`MAP_DOES_NOT_EXIST`、`INVALID_MAP_METADATA`、`INVALID_MAP_DATA` statuses.
- **Limitations:** release/API evidence does not prove target installation or this project's stored files.
- **Access Date:** 2026-08-14

### 9.2 YAML/image conversion and diagnostics

- **Evidence Type:** upstream Jazzy source
- **Source:** [`map_io.cpp` Jazzy source](https://api.nav2.org/nav2-jazzy/html/map__io_8cpp_source.html)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** resolves relative image path, parses metadata, loads image pixels, converts them into Occupancy Grid data, catches YAML/image exceptions, logs exception details and returns categorized status.
- **Limitations:** standard parse success does not evaluate map geometry, coverage or deployment fitness.
- **Access Date:** 2026-08-14

### 9.3 MapServer lifecycle comparison

- **Evidence Type:** upstream Jazzy API/source
- **Sources:** [`MapServer` Jazzy class API](https://docs.ros.org/en/jazzy/p/nav2_map_server/generated/classnav2__map__server_1_1MapServer.html)；[`map_server.cpp` at Navigation2 1.3.12](https://github.com/ros-navigation/navigation2/blob/1.3.12/nav2_map_server/src/map_server/map_server.cpp)
- **Exact Version / Revision:** Navigation2 1.3.12
- **Observed Scope:** configure loads configured YAML through MapIO; load failure causes configure failure; map publication occurs only after activate.
- **Limitations:** configure-only adds node lifecycle machinery without improving the public direct-read-back contract needed here.
- **Access Date:** 2026-08-14

### 9.4 Jazzy binary release metadata

- **Evidence Type:** ROS build-farm status
- **Source:** [ROS 2 Jazzy package status](https://repo.ros2.org/status_page/ros_jazzy_default.html)
- **Exact Version / Revision:** `nav2_map_server` 1.3.12-1 for Ubuntu Noble/Jazzy
- **Observed Scope:** confirms the assessed package version exists in the Jazzy binary release line.
- **Limitations:** availability does not prove the version installed in the target image.
- **Access Date:** 2026-08-14

## 10. Recommended 04 Record

```text
SYS-024 Map Package Read-back
Candidate Mature Solution: ROS 2 Jazzy nav2_map_server 1.3.12-1 public MapIO loadMapFromYaml
Coverage Status: Fully Covered
Covered Scope: YAML/image parsing; OccupancyGrid conversion; standard LOAD_MAP_STATUS; native failure-reason logs
Custom Behavior Gap: None; direct library call and standard-result forwarding are integration/composition
Configuration / Composition Gap: just-stored authoritative YAML path; same-package identity; persistent readable filesystem; preserve status/log; no /map publication side effect
Evidence Gap: target version; successful real-package read-back; each standard failure status/reason; correct path identity; no /map side effect; parseable-but-low-quality limitation recorded separately
MVP Change Candidate: None
```

完成SYS-024 record後才進入下一個requirement；不要把標準read-back擴張成map quality assessment。
