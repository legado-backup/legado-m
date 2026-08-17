# 项目状态面板

> 最后更新：2026-08-16
> 状态判定原则：以源码实证为准，任务勾选框/README 状态不视为最终事实（本仓库存在大量"已实现但未勾选"，本次已大幅校正）。

## 项目概况

| 项目 | 值 |
|------|------|
| 名称 | Legado（阅读M） |
| 类型 | Android 应用 |
| 语言 | Kotlin + Java |
| 最低SDK | 23 |
| 目标SDK | 36 |
| 数据库版本 | 101（持续演进迁移） |

## 仓库 spec 总量

共 ~100 个 spec 目录（含 `docs/specs/`）。分类概览：
- ✅ 已完成/可完成：约 53（含本次源码实证校正）
- 🔄 进行中（部分实现）：约 31
- 📋 设计中（纯设计未实现）：约 10
- ♻️ 被取代/废弃（建议归档）：约 12
- ❓ 待源码核验：0（2026-08-04 已全部核验归位）

---

## ✅ 已完成（源码实证 / 勾选 100%）

### 图片播放器

| 功能 | 说明 | 文档 |
|------|------|------|
| 图片前置嗅探能力 | 三层降级 + 8 项静态策略，ImageUrlExtractor.kt 已落地 | [image-sniffer-optimization/](./image-sniffer-optimization/) |
| 图片画布 3 处修复 | 初始定位/图片数/回退循环，源码注释含 Q1/Q2/Q3 | [image-canvas-3fix-20260728/](./image-canvas-3fix-20260728/) |
| 图片画布线程修复 | Glide 回调切主线程 + currentUrl 守卫 | [image-canvas-thread-fix-20260728/](./image-canvas-thread-fix-20260728/) |
| 图片垂直画布 | 单 RecyclerView 长画布 + 大图详情 + 自动翻篇（92%） | [image-player-vertical-canvas-optimization/](./image-player-vertical-canvas-optimization/) |

### B. 嗅探 / 稳定性

| 功能 | 说明 | 文档 |
|------|------|------|
| 嗅探结果管线修复 | 移除外层超时抢占 + StreamReset 重试 + DoH 清理 | [sniff-result-pipeline-fix-20260731/](./sniff-result-pipeline-fix-20260731/) |
| 嗅探稳定性 V3 | 降级误判削减 + 连接池/重定向增强 | [sniff-stability-fix-20260731/](./sniff-stability-fix-20260731/) |

### C. 视频播放

| 功能 | 说明 | 文档 |
|------|------|------|
| 播放器韧性 | 5 级 MIME 链 + WebView 自动降级 | [exoplayer-resilience/](./exoplayer-resilience/) |
| HLS 边播边缓存 | cachePlay 全量接入；设置开关待接 | [video-m3u8-cache/](./video-m3u8-cache/) |
| 视频抓包层提取 | 全量拦截 + 5 路 JS hook + __videoUrls__ | [video-extractor-enhancement/](./video-extractor-enhancement/) |
| 视频搜索/嗅探修复 | R5 抓包 + fallback 链 + 首帧超时 + 默认源 | [video-search-sniff-fix-20260727/](./video-search-sniff-fix-20260727/) |
| 手势/UI/布局系列 | video-gesture-overhaul、video-mute-highspeed、video-ui-dedup-layout-adjust、gsy-fullscreen-button-removal | （已完成 100%） |

### D. RSS

| 功能 | 说明 | 文档 |
|------|------|------|
| 统一搜索 | RssSearchActivity 全套（去重/换源/历史） | [rss-unified-search/](./rss-unified-search/) |
| 缓存优先 | fullRefresh + RssSource.cacheFirst=true | [rss-cache-first/](./rss-cache-first/) |

### E. Cronet（2026-07-31 三连）

| 功能 | 说明 | 文档 |
|------|------|------|
| ProGuard 修复 | proguard-rules.pro L161-212 保留规则 | [cronet-proguard-fix-20260731/](./cronet-proguard-fix-20260731/) |
| SO 下载修复 | GitHub Releases + md5 重下 + 国内 DoH + QUIC | [cronet-so-download-fix-20260731/](./cronet-so-download-fix-20260731/) |

### F. 修复批次 / 构建 / 依赖

| 功能 | 说明 | 文档 |
|------|------|------|
| V3.26.0717 批次 | Issue-2/3/5.x 源码注释实证 | [v3.26.0717-bug-fix-batch/](./v3.26.0717-bug-fix-batch/) |
| 真机修复批次 003/004 | Exo/DohDns/Glide 修复，源码实证 | [realdevice-test-fix-003/](./realdevice-test-fix-003-20260727/) 、[004/](./realdevice-test-fix-004-20260727/) |
| 全局问题修复与沉淀 | 并发字段/回填/lastHost + spec-sedimentation 文档 | [global-issue-fix-and-spec-sedimentation/](./global-issue-fix-and-spec-sedimentation/) |
| 依赖升级 | okhttp 5.4.0 / coroutines 1.11.0，minSdk 23 | [dependency-upgrade-optimization/](./dependency-upgrade-optimization/) |
| 文档体系合并 | docs/01-15 删除，project-flow 单树 | [docs-consolidation/](./docs-consolidation/) |
| P0 核心 Bug 修复 | sourceSort 拆分/换集静音/搜索框回填/多选（代码全落地，E2E 待跑） | [p0-bugfix-round1/](./p0-bugfix-round1/) |
| 2026-07-30 批次 | 12 个 bug 修复（含 BUG6-9-V2 隐藏项）代码实证 | [bugfix-20260730-batch1/](./bugfix-20260730-batch1/) |
| 高亮规则修复 | 匹配/数据/绘制三层代码全落地 | [highlight-rule-fix-20260727/](./highlight-rule-fix-20260727/) |
| 高亮恢复默认 | RestoreMode + 菜单 + 二次确认，代码实证 | [highlight-rule-restore-default-20260729/](./highlight-rule-restore-default-20260729/) |
| 内存/Context 压缩保留、memory 重设计、内置主题、Sigma 同步 | 见末表 | [memory-*](./memory-mechanism-redesign/) 等 |

### H. 书源/订阅源管理 UI（2026-07-08 大重构批次）

| 功能 | 说明 | 文档 |
|------|------|------|
| 布局设置重做 | 视图模式/排序/类型筛选全链路，adapterCompact/Grid 方案落地 | [source-layout-redesign/](./source-layout-redesign/) |
| 书架风格布局 | item 布局重构 + SourceExt + 域名分组链路全落地（25/51，余真机） | [source-layout-bookshelf-style/](./source-layout-bookshelf-style/) |
| 详情精修 | 标签模式/类型筛选/搜索框/视频缓存 Spinner（36/48，D4 待验） | [source-layout-detail-refinement/](./source-layout-detail-refinement/) |
| 文件夹视图/欢迎页 | 文件夹卡片 3:4 渐变 + 欢迎页默认开启（39/54，余真机） | [folder-view-welcome-refactor/](./folder-view-welcome-refactor/) |
| RSS 并发+源检查 | parseConcurrency + 5 维源检查 + 权重回填 + 去重（49/54） | [rss-concurrency-and-checksource-optimization/](./rss-concurrency-and-checksource-optimization/) |

### G. 其余勾选 100% 的已完成 spec（简表）

app-stability-round2、子代理预算、技术文档审计修复、视频播放问题 round1、线程池拆分配置、jvm-webview（116/116）、legado-skill-v2-rebuild（89/89）、skill-core-capability-rebuild（312/312）、内置主题、sigma-sync-202607、上下文压缩反馈保留（90/91）。

---

## 🔄 进行中（部分实现）

| 功能 | 勾选 | 残留 | 文档 |
|------|------|------|------|
| 图片线程协调修复 | 0/134 | FR-1 进度阈值 / FR-7 待补 | [image-thread-coordination-fix-20260731/](./image-thread-coordination-fix-20260731/) |
| 嗅探稳定性增强 | 0/43 | FR-3 路径直通部分 | [sniff-stability-enhance-20260731/](./sniff-stability-enhance-20260731/) |
| 视频缓冲提速 | 0/57 | 监控/OkHttp/解码器 + ABR 缺失 | [video-buffer-speed-optimization/](./video-buffer-speed-optimization/) |
| 播放器审查优化 | 0/109 | 架构项 + 2 新文件缺失 | [player-review-and-optimization/](./player-review-and-optimization/) |
| 日志审计与增强 | 0/55 | collect_app_log.py 缺失 | [logging-audit-and-enhancement/](./logging-audit-and-enhancement/) |
| Cronet 全局启用 | 0/24 | P0 已落地；P1-3 扩展未做 | [cronet-global-enable-20260731/](./cronet-global-enable-20260731/) |
| RSS V5.7 深修 | 6/21 | 数据交付（output/rss）缺失 | [rss-v5_7-deep-fix/](./rss-v5_7-deep-fix/) |
| fork 借用实现 | 12/163 | 设计阶段；纸墨/撞色/预加载未做 | [forks-archive-borrow-implementation/](./forks-archive-borrow-implementation/) |
| 构建流程优化 | 37/74 | 剩余验证项 | [build-workflow-optimization/](./build-workflow-optimization/) |
| Skill 统一优化重设计 | 24/151 | 9 方向 3 阶段 | [legado-skill-unified-redesign/](./legado-skill-unified-redesign/) |
| Legado 核心质量 | 64/100 | 3 批次渐进 | [legado-core-optimization/](./legado-core-optimization/) |
| 端到端自动化测试 | 107/168 | 全量用例收敛 | [e2e-automated-testing/](./e2e-automated-testing/) |
| 源修复闭环 | 180/208 | 尾项 | [source-repair-loop-optimization/](./source-repair-loop-optimization/) |
| Git 多 remote 隔离 | 9/49 | pre-push hook/public 推送已落地；设计命名未落实（master-private/private 别名缺失、token 明文） | [git-multi-remote-isolation/](./git-multi-remote-isolation/) |
| 网络性能稳定（大伞） | 190/229 | P2/P3 项待做 | [network-perf-stability/](./network-perf-stability/) |
| 多行按需提取 | 71/101 | 尾项 | [multiline-on-demand-extraction/](./multiline-on-demand-extraction/) |
| RSS 解析优化 / 并发源检查 / 视频源周边 | 72/133 等 | 尾项 | [rss-parse-optimization/](./rss-parse-optimization/) 等 |

> 其余中低勾选（30-70%）：apk-size、video-prebuffer、video-playback-failure-fix、rss-enhancement 等，均为进行中/待补，需逐项按源码核实。

---

## 📋 设计中（纯设计未实现，源码无实证）

| 功能 | 优先级 | 说明 | 成本/价值 | 文档 |
|------|--------|------|----------|------|
| 大书源 JSON ANR 修复 | P1 | CodeView 超长 native 重排 >10s | 🥇 极小/高 | [book-source-edit-anr-fix-20260731/](./book-source-edit-anr-fix-20260731/) |
| Cookie 管理修复 | P0 | WebView↔CookieStore↔OkHttp 失同步 | 中/中 | [cookie-management-fix/](./cookie-management-fix/) |
| RSS 图片解密优化 | P1 | P0 截断已被 logging 覆盖；并行未做 | 小-中/中 | [rss-image-decrypt-optimization/](./rss-image-decrypt-optimization/) |
| RSS 批量优化 V2 | P1 | Playwright 脚本 + output/rss 均缺失 | 中/中 | [rss-batch-optimize-v2/](./rss-batch-optimize-v2/) |
| 书源↔订阅源互转 | P1 | DB+双规则引擎+转换层 | 大/中 | [source-convert-20260730/](./source-convert-20260730/) |
| TVBox 优化 4 方向 | P2 | MPV/QuickJS/DLNA 原生依赖 | 大/大 | [tvbox-optimization/](./tvbox-optimization/) |
| legado_client 平台化 | P2 | FastAPI+MySQL+Vue3，与 skill 精简冲突 | 大/中 | [legado-client-enhancement/](./legado-client-enhancement/) |
| RSS 年龄验证自动绕过 | P2 | 三层绕过配置全未实施（仅调研勾选）；loginCheckJs 等为原版框架字段 | 中/中 | [rss-age-verify-autobypass/](./rss-age-verify-autobypass/) |
| 上游 fork 对比分析 | P3 | 分析型产出为设计文档；实现/集成 47 项未做，temp/forks-comparison/legados 缺失 | 小/中 | [legados-forks-comparison/](./legados-forks-comparison/) |
| 本地视觉大模型测试 | P1 | ai_tests 接入 Qwen3VL-8B（脱离 LM Studio 自动托管）：AI 判定器回填 ai_verdict + GUI Agent 混合定位执行器 + 经验层，全部存在于设计文档 | 中/高 | [ai-llm-testing/](./ai-llm-testing/) |
| 上游同步优化批次 20260816 | P0 | ✅设计定稿(08-16)待实施。近一月生态对比（10 仓库：喵公子 14 版 + legado-E EPUB 修复 + 阅读T/MD3/Archive/Jingshiro 提交级，原版已停更）→ 16 项同步：EPUB delTag 位运算实锤 bug、章节缓存写入保护、更新弹窗大小日期、日志分享、下拉书签、目录分卷折叠、TTS 段落停顿+定时三模式、JS 并发工具、漫画长按保存、WebDAV 删书联动、预测返回、URL 超时/重定向、TextDialog 文档内搜索、TXT 分割字数、ReadRecord OOM 核查、HttpTTS CookieJar；2 硬门禁（3.1.0 Rhino 线程模型先对比上游、3.4.1 onBackPressed 清零）；阶段0 门禁=等 Compose 化提交固化 | 中/高 | [sync-upstream-optimizations-20260816/](./sync-upstream-optimizations-20260816/) |
| 主题架构 v2（全局即时换肤） | P0 | ✅已实施+真机验证(08-17)。修复 Compose 迁移后主题设置大面积失效（RECREATE 仅 2 处订阅/LegadoTheme 一次性读值/非激活组静默无效）→ ThemeSync 全局版本信号（bump 即全 Compose 换肤零重建）+ BaseActivity 统一订阅（沉浸/设置页豁免改刷系统栏）+ onResume 令牌懒同步（Archive 模式）+ ThemeSpec 撞色守卫（对比度<1.3 跨昼夜兜底，压平 alpha 防崩）+ 底栏选中色改跟随主色（消除蓝顶栏红选中撞色）；主题设置页全 Compose 重设计（主题瓦片网格/ColorPickerSheet HSL 活预览/非激活组 toast/AppMenuSheet 背景图流）；新组件 ThemeSync/ColorPickerSheet/SettingsColorRow，删孤儿 ThemeListDialog；VLM 评审 8.5/10、主页综合 75/100（间距圆角细节留独立立项） | 中 | [theme-architecture-v2/](./theme-architecture-v2/) |

---

## ♻️ 被取代 / 废弃（建议归档）

| 目录 | 原因 |
|------|------|
| sniff-degradation-fix-20260731 | 空目录，前提被证伪（Cronet 降级归因错误） |
| image-gallery-activity | 双 ViewPager2 被垂直画布显式废弃 |
| skill-optimization（0/182） | 老版 skill，被 unified-redesign 链取代 |
| legado-skill-optimization（15/251） | 同上 |
| legado-skill-optimization-v2 / v2/v3/v4-rebuild | 历史迭代，现行 SKILL.md 已含全方向 |
| spec-system-optimization | 被 global-spec-restructure 续接 |
| jvm-webview-and-test-fix | 已完成（111/111）可归档 |
| forks-archive 对比类 | 对比仓 temp/forks-comparison，主线不实施 |

---

## ❓ 待源码核验

> ~~约 8 个低勾选 spec 待核实~~：**2026-08-04 已全部核验归位**（见上方分类）：
> - ✅ 已实现未勾选（已同步勾选/归位）：`p0-bugfix-round1`（代码全落地）、`bugfix-20260730-batch1`（12 bug 已修复）、`highlight-rule-fix-20260727`、`highlight-rule-restore-default-20260729`（代码落地）、`source-layout-bookshelf-style`（25/51）、`source-layout-redesign`（26/37，仅 showConfigDialog 迁移未做）、`folder-view-welcome-refactor`、`rss-concurrency-and-checksource-optimization`（49/54）
> - 🔄 部分实现：`git-multi-remote-isolation`（门禁已落地，设计命名未落实）
> - 📋 真设计中：`rss-age-verify-autobypass`（仅调研）、`legados-forks-comparison`（分析型，集成未做）

---

## 待办（低成本高收益候选）

1. **book-source-edit-anr-fix 落地**：唯一纯设计中的小改动，修复打开大书源 JSON ANR/闪退（4 UI 文件 + ids.xml）
2. **video-m3u8-cache 补开关**：给 SettingsDialog 加 `cb_cache_play`，约 30 行
3. **rss-image-decrypt P1 并行化**：RssParserByRule 串行循环改 async/awaitAll + Semaphore(6)
4. **Cronet 全局启用 P1-3 扩展**：CronetTransportForOkHttp 桥接/HttpURL 替换等
5. **INDEX/勾选持续同步**：新增 spec 落地后及时勾选，避免再次积累"0% 但已实现"

## 归档

已完成/已过期 spec 归档在 `archive/`（当前在 `specs/` 下）。归档与还原操作见 [git-repo-management](../project-flow/git-repo-management.md)。