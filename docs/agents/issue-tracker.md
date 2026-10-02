# Issue tracker: GitHub

Specs 與 tickets 位於 `monkey30440/mobile_base` 的 GitHub Issues。
使用 `gh` CLI；多行內容使用 `--body-file`。

目前 V1 輸入：

- [Wayfinder map](https://github.com/monkey30440/mobile_base/issues/18)
- [Specification](https://github.com/monkey30440/mobile_base/issues/32)
- Implementation tickets：依各 ticket 的 Parent 與 blocking edges 查詢。

讀取 issue 時包含 body、comments 與 labels。
「publish」表示建立 GitHub issue。
「fetch」表示讀取相關 issue 與 comments。

## Pull requests as a triage surface

PRs as a request surface: no.

## Wayfinding operations

Map 使用 `wayfinder:map`；tickets 為 native sub-issues。
使用 `wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling`、`wayfinder:task` labels。
以 GitHub native dependencies 表示 blockers。
Frontier 為 open、未指派、所有 blockers 已 closed 的 tickets。
開始前指派給執行者；完成後發布 resolution、close，
並將 gist/link 加入 map 索引。
Native relationships 不可用時才使用文件連結 fallback。
