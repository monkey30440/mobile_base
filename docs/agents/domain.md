# Domain Docs

採 single-context：移動底座；術語與 owning package README 放在一起。

探索模型術語前讀取 `src/mobile_base_description/README.md` 的「模型術語」。
探索 IMU 標定／補償語意前讀取 `src/mobile_base_perception/README.md` 的標定章節。
Architecture decisions 以 GitHub decision tickets 為單一來源；相關 ADR 若存在則讀取。

使用已定義的術語；缺口由 domain-modeling 在 owning documentation 釐清。
遇到 ADR／confirmed decision 衝突時明確提出，不靜默覆寫。
不重新建立根目錄 CONTEXT.md 或空 domain 文件。
