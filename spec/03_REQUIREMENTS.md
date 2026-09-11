# System Requirements

本文件定義 `mobile_base` 之可觀察功能需求、安全需求與操作限制。

Requirement 描述系統必須滿足之可觀察行為、限制與驗證邊界，不描述系統實作方式。

---

# UC-001 建立地圖

## SYS-001 建立地圖

系統應建立可供定位與導航使用之二維 Occupancy Grid 地圖；建圖功能無法完成初始化並進入就緒狀態時，系統應回報失敗及原因。

---

## SYS-002 儲存地圖

系統應將建圖結果儲存為 Map Package；無法儲存 Map Package 時，系統應回報失敗及原因。

---

## SYS-006 持續更新地圖

建圖進行期間，系統應於取得新的有效感知與里程資料後更新目前二維 Occupancy Grid；資料暫時不可用時，系統應保留目前地圖並等待後續有效資料，直到使用者完成或終止建圖。

---

## SYS-007 載入地圖

系統應載入所選定之 Map Package，並提供其中的二維 Occupancy Grid 給地圖定位與導航功能使用；Map Package 無法載入或解析時，系統不得進入可導航就緒狀態，並應回報原因。

---

## SYS-024 Map Package Read-back

系統應於 Map Package 儲存後，確認其中的地圖可重新解析為二維 Occupancy Grid；無法解析時，系統應依標準解析結果回報失敗及原因。

---

## SYS-034 手動移動控制

建圖期間，系統應接受使用者提供之手動速度命令以控制 AMR 移動巡覽環境；該移動控制應遵守既有底盤運動控制、運動限制、命令逾時與安全啟停需求。未提供手動速度命令或命令停止時，建圖程序不應因此終止。

---

# UC-002 導航至指定目標

## SYS-008 Navigation Target

系統應支援以下兩種形式之 Navigation Target：

- **Generic Pose Target**：由外部提供可直接作為導航目標使用之 Canonical Goal Pose（包含位置與朝向）。
- **Station Target**：使用 Station ID 指定預先定義站點，並透過 Station Target Resolution 轉換為 Canonical Goal Pose。

---

## SYS-032 Station Target Resolution

系統應使用目前場域之 Station Catalog，將使用者提交的 Station ID 解析為該 Station 預先定義之位置與朝向，以形成 Canonical Goal Pose；Station ID 為空、找不到對應 Station 或無法解析時，系統應拒絕該目標並回報原因。

---

## SYS-033 Canonical Goal Pose Validation

針對 Station Target 所解析產生之 Canonical Goal Pose，系統應於提交導航前驗證其合法性；其位置與朝向資訊應為有效數值，且應能在目前導航使用之座標基準下正確解釋。驗證失敗時，系統應拒絕該目標並回報原因；只有通過驗證的 Canonical Goal Pose 才可提交至後續導航流程。

---

## SYS-010 地圖定位

系統應根據已載入地圖與可用的感知及里程資料估測 AMR 在地圖中的位置與朝向，並提供導航所需的地圖座標基準。當 AMR 開機位置無法可靠得知時，系統應接受使用者提供目前地圖中的 approximate initial pose，作為定位初始化起點，該輸入不得直接作為導航目標。

---

## SYS-045 定位失效恢復

導航期間，系統應持續判斷目前地圖定位是否仍足以支援安全導航；當定位持續無法可靠使用時，系統應停止目前自主導航運動並嘗試重新建立地圖定位。重新定位成功後，系統應使用恢復後之目前位姿重新建立後續導航；若在有限次數之恢復嘗試後仍無法建立可靠定位，系統應終止導航並回報定位失敗原因。定位可靠性判定門檻、持續時間及最大恢復嘗試次數應由後續整合與驗證決定。

---

## SYS-011 路徑規劃

系統應根據目前位姿與目前導航階段之目標位姿，產生安全可行之路徑供該導航階段使用。無法產生有效路徑時，系統不得開始該階段之路徑追蹤，並應回報規劃失敗。

---

## SYS-013 Route-preferred Navigation Strategy

系統應以有效 Route Graph 為主要導航依據（route-preferred），根據目前位姿、Canonical Goal Pose 與 Route Graph 建立可安全執行之 route-assisted navigation strategy，並由 First Mile、On Route 與 Last Mile 共同形成通往目標之導航路徑。

---

## SYS-014 障礙物避讓

導航期間，系統應使用有效之環境障礙物資訊，避免規劃或執行穿越已判定占用區域之運動；無法維持可安全執行之導航時，系統應嘗試使底盤停止並回報失敗。

---

## SYS-015 路徑追蹤

系統應控制 AMR 追蹤目前 active navigation stage 之有效路徑，並監控路徑追蹤狀態；無法繼續安全追蹤或停滯無法前進時，系統應終止該 stage 之路徑追蹤、使底盤停止並回報追蹤失敗。

---

## SYS-016 到站判定

系統僅應在 AMR 目前位姿符合解析後 Navigation Target 所設定之位置與朝向接受條件，且底盤已停止時，判定導航成功。位置、朝向與停止判定門檻應經整合及實機驗證。

---

## SYS-017 導航結果

系統應於導航任務結束時回報明確之最終結果，包含成功（Success）、失敗（Failure）或取消（Canceled）；導航失敗時，系統應回報可取得之失敗原因。

---

## SYS-018 First Mile

目前位姿不在選定 route entry 時，系統應規劃並執行由目前位姿至該 entry 的安全連接；目前位姿已位於適用的 route entry 時，First Mile 應視為不需要執行，不得因此判定導航失敗。

---

## SYS-019 On Route Navigation

系統應沿選定 Route Graph route 由 route entry 移動至 route exit，並遵守 Route Graph 所定義的 connectivity、direction 與 availability constraints。

---

## SYS-020 Last Mile

選定 route exit 未直接到達 Canonical Goal Pose 時，系統應規劃並執行由該 exit 至 Canonical Goal Pose 的安全連接；Canonical Goal Pose 已位於適用的 route exit 時，Last Mile 應視為不需要執行，不得因此判定導航失敗。

---

## SYS-025 導航取消

系統應接受使用者對進行中導航任務提出之取消要求，終止該導航任務，並回報取消結果。

---

# UC-004 精準停靠

## SYS-044 精準停靠控制

系統應支援根據外部提供之停靠目標資訊執行精準停靠控制：

1. **任務控制與觸發**：系統應接受外部任務控制端提出之停靠要求以啟動停靠任務；系統應支援於停靠期間提供執行狀態反饋、接受取消要求，並回報停靠結果。
2. **外部目標資訊使用**：系統應接收外部系統提供之停靠目標資訊，並於確認該資訊有效且可供使用後，控制 AMR 在目標鄰近範圍內執行局部精準接近與對準；停靠期間應持續使用外部更新之目標資訊調整停靠運動。僅接收停靠目標資訊不得視為啟動停靠任務。
3. **安全防護與異常終止**：停靠期間若外部停靠目標資訊不可用或失效、無法維持安全運動、或在允許時間內無法完成停靠時，系統應終止停靠、使 AMR 停止並回報失敗。
4. **任務取消**：收到外部任務控制端之取消要求時，系統應終止停靠、使 AMR 停止並回報取消結果。
5. **完成條件**：AMR 抵達預定停靠相對位置與朝向容差範圍且 AMR 停止時，系統應判定停靠成功並回報結果。停靠成功僅表示預定相對位置與朝向條件達成並停止，不代表充電連接或充電流程完成。

---

# UC-003 觀察與診斷 AMR 運行

## SYS-035 AMR 運行資訊觀察

系統應提供主要 AMR 與 ROS Runtime Information，供 Actor 查看及人工診斷；可提供的資訊應涵蓋與 Perception、State Estimation / Localization、Mapping / Navigation、Control、Hardware Communication 及 Host / Runtime 相關的選定運行資訊。缺少任一資訊時，系統不得據此推論相關 subsystem 正常。

---

## SYS-036 Logs 與運行事件歷史

系統應將 AMR 產生之選定診斷 Logs 與運行 Events 傳送至 Server；Server 應保存所收到的 Logs 與 Events，並支援依基本時間範圍及來源查詢。

---

## SYS-037 關鍵時間序列 Telemetry

系統應將選定的關鍵時間序列 Telemetry 由 AMR 傳送至 Server；Server 應保存所收到的關鍵 Telemetry，並支援依時間範圍查詢。Telemetry profile 由後續設計與實作配置決定，本需求不要求保存所有 ROS Topics 或完整高頻 Raw Payload。

---

## SYS-038 基本時間關聯

系統應為傳送至 Server 的 Logs、Events 與關鍵 Telemetry 保留可用 timestamp 及 source identity；Server 應支援 Actor 依共同時間範圍進行基本關聯。

---

## SYS-042 Observability Failure Isolation

Observability Component Failure、Network Unavailable 或 Server Unavailable 不得成為 Navigation、Localization、Control 或 Safety 運行的必要依賴。Observability Data 無法傳送或持續累積時，系統不得因此無限制消耗 AMR 端系統資源，並應維持既有 AMR 核心功能運行。

---

# Shared Requirements

## SYS-003 LiDAR 感知

系統應提供 LiDAR 掃描資料供建圖、定位與導航使用。

---

## SYS-004 IMU 感知

系統應提供 IMU 量測資料供定位使用。

---

## SYS-005 系統里程

系統應提供連續且具時間資訊之 AMR 平面位姿與速度里程估測，並提供里程參考基準與機器人本體基準之動態座標關係，供建圖、定位與導航使用。

---

## SYS-022 底盤運動控制

系統應接收底盤速度命令，並依差速輪運動學控制底盤完成移動。

---

## SYS-023 機器人描述

系統應提供機器人幾何、座標系與關節定義，供感知、定位、建圖與導航使用。

---

## SYS-026 底盤故障處理

當底盤硬體或通訊發生故障時，系統應停止對底盤發出運動驅動，並使故障狀態可被觀察。

---

## SYS-027 運動命令逾時

底盤執行運動期間，若系統未在設定之逾時時間內收到有效的新速度命令，應使底盤停止；逾時值與停止行為應經整合及實機驗證。

---

## SYS-028 底盤運動限制

系統應將 AMR 的直線與旋轉速度，以及相應的加速與減速，限制於設定之 operational limits；限制值應依操作需求選定，並於部署前完成整合及實機驗證。

---

## SYS-029 底盤狀態回授

系統應提供由馬達驅動器有效回授所取得之左右輪位置與速度狀態，供里程估測、控制與診斷使用；無有效回授時，系統不得以命令值取代量測狀態，並應將狀態視為不可用或故障。

---

## SYS-030 底盤安全啟停

系統僅應在底盤通訊正常、無馬達驅動器警報、輪端為停止狀態且驅動器已確認可運動後接受非零運動命令。底盤停用或系統關閉時，系統應嘗試使底盤停止、確認停止狀態並停用馬達驅動；任一安全動作失敗不得阻止其餘安全動作之嘗試。狀態轉換等待時間與停止確認條件應經實機驗證。

---

## Traceability

| Requirement | Use Case | Capability |
|---|---|---|
| SYS-001 | UC-001 | CAP-001 |
| SYS-002 | UC-001 | CAP-001 |
| SYS-003 | UC-001 | CAP-001 |
| SYS-004 | UC-001 | CAP-001 |
| SYS-005 | UC-001 | CAP-001 |
| SYS-006 | UC-001 | CAP-001 |
| SYS-007 | UC-001 | CAP-001 |
| SYS-022 | UC-001 | CAP-001 |
| SYS-026 | UC-001 | CAP-001 |
| SYS-027 | UC-001 | CAP-001 |
| SYS-028 | UC-001 | CAP-001 |
| SYS-029 | UC-001 | CAP-001 |
| SYS-030 | UC-001 | CAP-001 |
| SYS-023 | UC-001 | CAP-001 |
| SYS-024 | UC-001 | CAP-001 |
| SYS-034 | UC-001 | CAP-001 |
| SYS-008 | UC-002 | CAP-002 |
| SYS-032 | UC-002 | CAP-002 |
| SYS-033 | UC-002 | CAP-002 |
| SYS-010 | UC-002 | CAP-002 |
| SYS-045 | UC-002 | CAP-002 |
| SYS-011 | UC-002 | CAP-002 |
| SYS-013 | UC-002 | CAP-002 |
| SYS-014 | UC-002 | CAP-002 |
| SYS-015 | UC-002 | CAP-002 |
| SYS-016 | UC-002 | CAP-002 |
| SYS-017 | UC-002 | CAP-002 |
| SYS-018 | UC-002 | CAP-002 |
| SYS-019 | UC-002 | CAP-002 |
| SYS-020 | UC-002 | CAP-002 |
| SYS-025 | UC-002 | CAP-002 |
| SYS-003 | UC-002 | CAP-002 |
| SYS-004 | UC-002 | CAP-002 |
| SYS-005 | UC-002 | CAP-002 |
| SYS-022 | UC-002 | CAP-002 |
| SYS-023 | UC-002 | CAP-002 |
| SYS-026 | UC-002 | CAP-002 |
| SYS-027 | UC-002 | CAP-002 |
| SYS-028 | UC-002 | CAP-002 |
| SYS-029 | UC-002 | CAP-002 |
| SYS-030 | UC-002 | CAP-002 |
| SYS-035 | UC-003 | CAP-003 |
| SYS-036 | UC-003 | CAP-003 |
| SYS-037 | UC-003 | CAP-003 |
| SYS-038 | UC-003 | CAP-003 |
| SYS-042 | UC-003 | CAP-003 |
| SYS-044 | UC-004 | CAP-004 |
| SYS-022 | UC-004 | CAP-004 |
| SYS-027 | UC-004 | CAP-004 |
| SYS-028 | UC-004 | CAP-004 |
| SYS-030 | UC-004 | CAP-004 |

### Requirement to Implementation Area Allocation

下表定義各系統需求在 [04_SYSTEMS.md](./04_SYSTEMS.md) 中的主要實作責任區域；Secondary Implementation Area 僅用於需求本身跨越多個直接實作責任的情況。

| Requirement | Primary Implementation Area | Secondary Implementation Area |
|---|---|---|
| SYS-001 | Mapping | — |
| SYS-002 | Mapping | — |
| SYS-003 | Sensor Ingestion | — |
| SYS-004 | Sensor Ingestion | — |
| SYS-005 | State Estimation | — |
| SYS-006 | Mapping | — |
| SYS-007 | Localization | — |
| SYS-008 | Navigation Target Admission | — |
| SYS-010 | Localization | — |
| SYS-045 | Localization | — |
| SYS-011 | Route-Assisted Navigation | — |
| SYS-013 | Route-Assisted Navigation | — |
| SYS-014 | Route-Assisted Navigation | — |
| SYS-015 | Route-Assisted Navigation | — |
| SYS-016 | Route-Assisted Navigation | — |
| SYS-017 | Route-Assisted Navigation | — |
| SYS-018 | Route-Assisted Navigation | — |
| SYS-019 | Route-Assisted Navigation | — |
| SYS-020 | Route-Assisted Navigation | — |
| SYS-022 | Base Control | — |
| SYS-023 | Robot Model | — |
| SYS-024 | Mapping | — |
| SYS-025 | Route-Assisted Navigation | — |
| SYS-026 | Base Control | — |
| SYS-027 | Base Control | — |
| SYS-028 | Base Control | — |
| SYS-029 | Base Control | — |
| SYS-030 | Base Control | — |
| SYS-032 | Navigation Target Admission | — |
| SYS-033 | Navigation Target Admission | — |
| SYS-034 | Base Control | Mapping |
| SYS-035 | Observability | — |
| SYS-036 | Observability | — |
| SYS-037 | Observability | — |
| SYS-038 | Observability | — |
| SYS-042 | Observability | — |
| SYS-044 | Precision Docking | — |
