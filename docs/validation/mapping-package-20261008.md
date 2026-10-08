# Mapping 套件驗證 — 2026-10-08

## 範圍與版本

對應 #39／spec32 的 mobile_base_mapping 獨立套件。
實裝 Ubuntu24.04／ROS2Jazzy，slam_toolbox2.8.5、nav2_map_server1.3.13。
原生能力及責任研究見 [研究筆記](../research/mapping-native-20261008.md)。
實作前基準 ec4a22f；user同意作為本輪 code-review 比較點。

## 軟體結果

測試於正式開發容器 mobile_base、隔離 ROS_DOMAIN_ID=149 執行。
新增入口之前，公開ROS測試因找不到 mapping.launch.py 失敗（RED）。
加入原生 launch/config後，三項測試通過：

1. 真實已安裝URDF含前左rollπ／yawπ/4，加上合成非對稱房間
   LaserScan／odom TF；靜止→位移0.65m→旋轉0.65rad→回訪。
   原生SLAM active、只訂閱FL、不訂閱BR、單一map publisher／map→odom；
   完整map→sensorTF可用。房間相對格網旋轉0.15rad，避免所有牆點
   恰落最大格網邊界的退化fixture；beam0.1°、無實體裝置。
2. 485 occupied cells全數位於fixture已知牆面0.15m內；取樣scan端點
   經完整TF轉到map後，全數距occupied cells小於0.20m，最大最近距離
   0.047935m。這是fixture容差／結果，**不是實機精度標定**。
3. 原生CLI成功保存map.pgm／map.yaml（image:map.pgm），原生map_server
   configure／activate並重載同geometry／occupied-cell數；不存在的選定
   config直接錯誤、不fallback；無map及圖片輸出父目錄不存在時原生保存失敗。

單檔最終命令：

```bash
ROS_DOMAIN_ID=149 python3 -m pytest src/mobile_base_mapping/test/test_mapping.py \
  -x -q --basetemp=/tmp/mapping39-final
```

結果：3 passed in31.38s。原生程序於fixture結束後清理；沒有fake deployment
sensor／odom publisher，沒有存圖wrapper或新Mappingruntime演算法。

Raw map、alignment數字、原生logs保留於
[software archive](artifacts/mapping-software-20261008.tar.gz)。

Archive SHA256：`133e135a234ac2f61629403cbfeb7d27c4e976f56324796857174950976f207d`。

## 新發現的部署 blocker（以上成功僅限對稱 software fixture）

實機前左與右後scan皆1200束，angle_min=-2.4086289405822754、
angle_max=2.8230104446411133、angle_increment=0.00436333566904068。
原生2.8.5倒裝只反轉ranges，未將bounds改為[-angle_max,-angle_min]。
偏差angle_min+angle_max=0.4143815040588379rad（約23.742°）。
Operator在Foxglove確認scan/map有明顯旋轉角差；尚未做任何非零動作。

使用實機角度重新執行fixture後，只有100/455occupied cells在已知牆面
容差內，公開ROS驗收失敗；此deployment不是通過狀態。
套件原生配置無法補足倒裝非對稱bounds責任，**#39保持OPEN**。
不修改已確認真實URDF、不宣稱對稱fixture代表實機正確；候選補足需獨立驗證。

全套回歸在首次Mapping測試遇到native loader discovery race（Node not found）；
已將test改為先等待原生ChangeState service再configure/activate。
當時結果82tests／1failure，不能宣稱全套通過。後續須含真實非對稱scan重驗。

所有實機元件已停止，獨立FC03讀回兩輪status6／alarm0／RPM0／target0。

## 實機與後續交付

**REQUIRES HARDWARE VALIDATION**：Operator需在Foxglove同map frame觀察真實scan／map，
涵蓋靜止、移動／旋轉、回訪；保存與原生重載作開發驗收，不增加日常保存後檢查。
套件通過後才接入產品Mapping Bringup；此文件不宣稱#39已完成。
正式輪參數、IMU bias／covariance及量化建圖／估測精度仍REQUIRES CALIBRATION。

## 最小原生source修正候選（software proof，不是正式部署）

官方2.8.5 commit ec8f7635dea317b531c419f798f87d90a336f32e，於/tmp
source workspace僅在toLaserMetadata的inverted branch將scan_的bounds
改為[-original_max,-original_min]，再讓原生makeLaser建立metadata。
scan_.為metadata的local copy；不改rawscan／frame／URDF，原生
scanToReadings仍reverse ranges，不新增scanrelay。

以實機1200束／非對稱angle bounds重新驗證；有限視野巡覽補足左右
旋轉與回訪的多視角（不是假設300°FOV能一次看到所有牆面）。
使用原生ChangeState service等候loader就緒後configure／activate。
結果3passed in41.00s，涵蓋真實角度倒裝map／scan對齊、native保存／重載
與缺config／無map／不可寫圖片路徑failure。仍未證明真實硬體map品質。

候選source diff、版本／compiled-libraryhash、失敗fixture與實機資料、
通過fixture map／logs保存於
[gap and candidate archive](artifacts/mapping-inverted-gap-20261008.tar.gz)。
正式可重現Docker部署、decision/spec reconciliation、code-review、
實機靜止／移動／旋轉／回訪與保存重載驗收仍未完成；不能宣稱#39完成。

Candidate proof結果：478occupied cells，wall alignment fraction1.0、scan alignment fraction1.0，最大最近occupied-cell距離0.051567m（fixture-only）。
Gap archive SHA256：ff5d0101fef38b226a7af421266c3b2fdcbecf536ab0b2b02e9538db26c0cf19。

## 正式 overlay 靜止實機結果與第二個 blocker

已依 Operator 採用的 decision 建置正式 Docker overlay。Image 為
`sha256:2c9d890de8434c7db4b63d5d26cabf0c7bc0c9e52f0cd3b9dccdbcccb56419b6`，
正式使用 `/opt/mobile_base/slam_toolbox/slam_toolbox` 的 2.8.5 修正版。
Operator 在 Foxglove 的 map frame 同時觀察 scan 與 map，確認：
**「角差消失，輪廓對齊」**。此結論限於靜止對齊；尚未驗收移動、旋轉與重訪。

正式 Mapping 軟體測試 3 項通過（42.24 秒）。同次全套 82 tests 有 1 項
既有 Bringup invalid-PGM 測試等待 native service response 超時；無修改重跑
該 dataset 測試檔 9 項全數通過（5.96 秒）。因此目前不宣稱全套已通過。

另確認 SICK 3.9.0 的 LaserScan range bounds 隨當幀 extrema 變動，
而 SLAM 快取首幀 bounds，會排除之後超出首幀範圍的有效點。
現場 scan.range_max 約 6.869 m，不能解讀成感測器能力。
兩台裝置唯讀 OrdNum 都是 1134608、DeviceIdent 為 picoScan 2.1.0.0R；
官方 Core-1 datasheet 對應工作範圍 0.05–25 m。詳見研究筆記。
這是尚未補足的 producer metadata gap，不是角差修正回歸。

本段沒有發送非零馬達命令，也未以 IMU-only EKF 輸出宣稱輪端資料鏈就緒。
為處理新 blocker，所有實機驗證程序已正常退出（exit 0）；獨立 FC03
讀回兩輪 status 6／alarm 0／RPM 0／target 0。

正式靜止觀察、裝置唯讀識別與測試 logs 保存於
[formal static archive](artifacts/mapping-formal-static-20261008.tar.gz)。
SHA256：`cfef804be7b639f27ffa8367f62237b4113f4368ce77834126c212dc3d14c042`。
#39 保持 OPEN；第二個 gap 的 decision 與補足、動態實機、保存重載、
產品 Mapping Bringup 與 code review 仍待完成。

## LaserScan measurement-bounds 補足與 differential proof

Operator 採用後已補入 decision22／spec32；正式 Docker image 更新為
`sha256:bb8807e3aa46589c09db406a1bea2b7f748143c31e1999c4b1071eb8e143e741`。
同一 SICK 3.9.0／commit a562c5d098de21f6284359f4dfea97e93bd2b4d5
加入預設停用的 metadata bounds，平台 lidar.yaml 明確提供 0.05／25 m。
range patch SHA256：`97287b13d1b9d66e89183c24c6b1318b4ba31f4de767421b026bbd9ebf0df5d2`。

驗證透過公開 ROS／native executable，不讀取私有 publisher 方法：

1. Native UDP compact v4 fixture 送入 2 m→10 m 的量測；未修正時
   scan bounds 回報 1.99899995／2.00099993 m，測試失敗。
   修正版同一原生 parser／publisher 固定回報 0.05／25 m，實際 ranges、
   同一 layer 的角度、intensities、frame 保持，1 項通過（0.70 秒）。
   fixture 是官方兩層 multiScan packet，因此可有 `_1`／`_2` frame，
   不能以此宣稱實機 picoScan 多層或改動已確認的 FL_1／BR_1 契約。
2. 同一真實模型、非對稱 scan 的較大 software room，以連續旋轉提供
   重疊視角與原生 occupancy 最小證據數。**相同原生 scan gate／幾何**，
   當幀 extrema metadata 的較遠點對齊比例 0，fixed capability bounds 為 1.0。
   首幀 observed maximum 10.07842255 m；後續 11.02018738 m；4 個超過
   首幀最大距離加 0.10 m 的取樣點全數距 occupied cell 小於 0.20 m。
   這是合成 fixture 的辨別門檻與證據，不是實體距離精度驗收。
3. 更新後 Mapping 3 項通過（47.12 秒），涵蓋較遠點、倒裝 scan／map、
   單一 map→odom owner、native 保存與重載，以及缺 config／保存失敗。
   最終 934 occupied cells，wall／scan alignment fractions 均 1.0，
   最大最近 occupied-cell 距離 0.08870682 m（fixture-only）。
4. 原生 LiDAR Operator launch regression 11 項通過（9.56 秒），含無配置
   的 upstream 行為與平台 bounds 參數服務；非法 bounds 啟動前拒絕，
   另 4 項通過（1.58 秒），不連接實體裝置。

較遠牆面的初始探針同時受原生「預設跳過純旋轉」scan gate 影響，
不能單憑那些失敗歸因 range bounds。最終 differential proof 兩邊都啟用
原生 `check_min_dist_and_heading_precisely=true`，排除這個干擾；平台
也使用此原生配置支援 Teleop 旋轉建圖，沒有新增 SLAM source 修正。

Raw native logs、RED／GREEN 差異、fixture maps／reload logs 與硬體識別見
[range-bounds archive](artifacts/mapping-range-bounds-20261008.tar.gz)。
SHA256：`bfb4d64f4cb492c1c5062fdee47932905fcd2a9de5f252cdde2a80ae67874ebd`。

實機重新啟動後，兩路 1200 束／原生 FL_1、BR_1／非對稱角度保持，
兩路 bounds 固定 0.05／25 m。Operator 按 k 初始化後，輪端 odometry 與
EKF 均持續更新；Operator 確認靜止及左轉停止後輪廓對齊、沒有明顯雙牆。
Operator 後續確認旋轉返回、前進約 0.6 m 與後退重訪後仍對齊，沒有明顯雙牆，
各段最後均停止，並已退出鍵盤。這是目視 workflow 驗收，不是里程計標定。

實機 native 保存產出固定 map.pgm／map.yaml；Map Server configure／activate
重載成功，181×213、resolution 0.05 m、549 occupied cells，occupancy 完全一致。
原生 MapIO 將 origin XY 保存至小數三位，因此重載 XY 差分別為
0.000136202／0.000378895 m，在每軸 0.0005 m 序列化界限內，
不宣稱 origin bitwise 相同；沒有修改原生存圖行為。

停止全部獨立元件後，2026-10-08 07:29:24 UTC 獨立讀回兩輪 inhibited、
alarm 0、目前／目標 RPM 0。產品 Mapping composition 的啟動驗收及最終
回歸／code review 仍待完成，#39 保持 OPEN。

上述完整實機 logs、最後地圖／重載結果與停用讀回已保存於
[hardware archive](artifacts/mapping-hardware-20261008.tar.gz)。
SHA256：`bfbc93c2319e85950bfe7992061965ff4aa4232ec9176fbc8ef779dd8d5be80d`。
最終 sequential colcon 全套回歸：6 packages，89 tests，0 errors／failures／skipped；
其中 Mapping 3 項、Bringup 11 項通過。

## 產品 Mapping Bringup 靜止驗收

獨立套件全部通過後，使用安裝後的單一 `mobile_base_bringup mapping.launch.py`
組合入口啟動既有 owning entries；沒有新增 runtime manager、TF owner 或速度 publisher。
Operator 按 k 初始化、等待 5 秒並退出鍵盤，確認全程靜止。
輪端 odometry、IMU、雙 scan、EKF 與 map 持續更新，兩條動態 TF 及完整模型 chain
可查詢。觀察時資料 age：輪端 0.049 s、IMU 0.012 s、FL 0.002 s、BR 0.009 s，
EKF 與 map→odom 持續發布；此為一次 startup 驗收，非硬體時序保證。
全部節點正常退出後，獨立 FC03 讀回兩輪 status 6／alarm 0／目前與目標 RPM 0。

[Bringup evidence](artifacts/mapping-bringup-20261008.tar.gz)
SHA256：`175f4786019d63c429a73e90905d5daba75af3be96e380305557261f6e8fa7d0`。
讀回工具內歷史 `position_scale: UNRESOLVED` 字串不參與此停用驗收，亦不推翻
#35 已確認的 position scale；本次判定只使用 status／alarm／RPM／target RPM。

獨立 Mapping、產品 composition 與完整回歸均完成。
以使用者指定 ec4a22f 為基準進行平行兩軸 review：Spec 0 findings；Standards
找到測試幾何重複、replay thread 清理範圍與 ROS domain 隔離問題，均已修正並複查，
無殘留 actionable finding。runtime 未再變更；受影響的 Mapping／native range
4 項測試重跑通過（47.53 秒），原 89 項完整回歸結果保留在 evidence archive。
此結論僅涵蓋 #39；Localization／Navigation 與完整 V1 實機驗收留原定後續 tickets。
