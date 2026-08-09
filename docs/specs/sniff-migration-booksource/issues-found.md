# sniff-migration-booksource — issues-found

> 本文件记录嗅探与滑动切换能力迁移至书源过程中的真机验证与限制。创建 2026-08-09。

## 真机测试结果

### RSS 回归（Level 3，真实数据回测通过）

| 场景 | 结果 | 备注 |
|------|------|------|
| RSS 视频播放 | ✅ PASS | MEmu 127.0.0.1:21503，包 `io.legado.miss.app.debug`；桃花视频文章 → VideoPlayerActivity；ExoPlayer `prepareAsyncInternal callCount=1` → `STATE_READY contentType=2 fallbackIndex=0/2` |
| RSS 垂直上滑切换 | ✅ PASS | 上滑后标题「第1集」→ 下一文章标题（显示线路：默认/0.0），无回归 |
| 崩溃检查 | ✅ 无 FATAL | 全程无 AndroidRuntime 崩溃 |

### 书源侧（无测试数据，用户决策跳过真机验证）

- `book_sources` 表为 **0 行**（无书源）。
- 探测可复用视频站（用于构造测试书源的尝试）：
  - `91.taohua48.cfd` 等 7 个 RSS 视频源走 `?m=searchall_async&api=xxx` JSON 聚合 API，`/api.php/provide/vod/` 404；
  - `?m=play` 返回反爬 JS 检查页（`window.location.href/https://xn--` 动态跳转），静态 ruleToc 无法取得集列表，不适合构造书源。
- 本地无图片/视频书源 JSON（`temp/output/book/groups/` 与 `ai_tests/testdata/` 均无）。
- **用户决策**（AskUserQuestion m0348，2026-08-09）：「跳过真机书源验证，直接检查点2」→ 5.2-5.6 改源码级验证，关键改动点 grep 全部确认（见 tasks.md 5.2-5.6 与 AOAdapt）。

## 遗留事项

1. 书源侧（type=2 图片 / type=4 视频）嗅探兜底与上下滑动切换的真实设备验证待补：需先导入可用书源（建议用直链 m3u8/mp4 的多集视频书源 + 纯 JS 渲染图片页的图片书源）。
2. MEmu 模拟器启动需管理员权限（`memuc.exe`/`MEmu.exe` 报 requires elevation），非提升态 shell 无法自行启动；RSS 源为成人内容站，仅用于功能回归测试。