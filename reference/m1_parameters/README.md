# M1 馬達參考設定

使用者提供的 RWF 馬達設定 ver3.1，用於追溯 V1 硬體參數與協定研究。
原始來源目錄：
`RWF_base_motordriver_param_ver3.1-20261002T071439Z-1-001/RWF_base_motordriver_param_ver3.1/`。
來源目錄的時間文字不代表已確認的設定匯出時間。

| 檔案 | 對應裝置 |
|---|---|
| `MotorDriver_RW_ID1_param_ver3.1.PELB` | 右輪，drive ID1 |
| `MotorDriver_LW_ID2_param_ver3.1.PELB` | 左輪，drive ID2 |

兩份檔案保留原始 bytes 與 CRLF，未修改參數。
Runtime 不讀取這些檔案，也不會自動寫入馬達；目前啟動設定為
`src/mobile_base_control/config/m1.yaml`。
參考檔不代表裝置目前設定，適用性須與實機讀回及驗證證據核對。
參數來源、實機比對與限制見 `docs/validation/m1-software.md`。

## SHA-256

```text
4b17d2f0f327d726c5e1e6330a9d043ab0485fff97dc43b7b135446dca166396  MotorDriver_LW_ID2_param_ver3.1.PELB
1525982ea0ad79a35900b8c9fcf37a3071763e4d7d2cea4457b254c5c54b541c  MotorDriver_RW_ID1_param_ver3.1.PELB
```
