# 20260822 真机反馈 Bug 修复（bugfix-20260822）

> 状态：🔄 设计中（2026-08-22，基于 `docs/issues/user/temp/20260822/` 用户反馈 + 100+ 份真机日志深度分析）

## 功能概述

针对用户 2026-08-22 持最新测试包实测反馈的 6 类问题 + 日志中 12 处 FATAL 崩溃 + 100+ 份 appLog 运行时异常进行**专项修复**，核心原则：

- **严格对齐 Archive**：备份恢复页样式、订阅页管理设置、新版/经典订阅切换、主题设置顶栏管理行为全部对标 `archive-ref/legado-08172114/`
- **深度日志分析**：`Downloadslogs(1).zip` 全量扫描（logcat 12 处 FATAL + appLog 约 9400 行异常），不遗漏任何问题
- **统计框隐藏不删码**：我的页头部四框统计信息用 `if(false)` 保留代码，后期可一键恢复
- **快速打测试包**：修复编译通过后立即 `build-legado.bat` 产出测试包

## 六条用户反馈 → 问题映射

| # | 用户反馈 | 根因 | 修复方向 |
|---|---------|------|---------|
| 1 | 备份与恢复页面样式没从 archive 搬迁 | `BackupConfigFragment` 原为纯 `PreferenceFragment` | 迁移为 `ComposeSettingFragment`（✅ 已实施） |
| 2 | 我的页头部四框统计信息（书架书籍/使用书源/订阅源/累计阅读）隐藏 | `MetricGrid` 无条件渲染 | `if(false)` 保留代码隐藏（✅ 已实施） |
| 3 | `Downloadslogs(1).zip` 大量报错，深度分析不遗漏 | 12 处 FATAL + 海量运行时异常 | 逐项分析（见 spec.md §Scenarios / design.md §Bug 分析） |
| 4 | 订阅页管理设置不生效、新版/经典订阅切换无反应 | `modernRssPage` PreferKey 存在但全项目无读取、RssFragment 无切换逻辑 | 对齐 Archive：读 `AppConfig.modernRssPage` + RssFragment 双形态渲染（待实施） |
| 5 | 不用自己真机测试，全力修复后快速打测试包 | — | 修复完编译门禁 + `build-legado.bat` 打包 |
| 6 | 主题设置顶栏管理行为完全和 archive 不一样 | `ThemeManageActivity`/顶栏管理链路未对齐 Archive | 对齐 Archive 顶栏管理（待核实实施） |

## 日志分析结论摘要

- **12 处 FATAL**（全部 `io.legado.miss.app.debug` 主线程）：
  - `StackOverflowError` ×2：`BookSourceActivity.onBackPressed` ↔ Compose `BackHandler` 无限递归（✅ 已修：删除 `initComposeHost`/`onBackPressed` 覆写）
  - `IndexOutOfBoundsException` ×1：`VideoPagerAdapter` ViewPager2 holder 位置不一致（✅ 已修：稳定 `getItemId`/`containsItem`）
  - `ActivityNotFoundException` ×9：`ThemeManageActivity` ×6 + `BookInfoComposeActivity` ×3 未在 Manifest 注册（✅ 已修：补注册）
- **appLog 运行时异常**（约 9400 行命中）：以网络层为主（DNS/DoH/连接重置，多为环境与书源问题）；**应用代码缺陷 2 类**：`ClassCastException: String→StrResponse` ×26（✅ 已修：`SourceNetworkClient.analyzeLoginResult` 类型容错）、`NullPointerException` ×12（`AnalyzeByJSonPath.getStringList`，待修）

## 文档索引

- [spec.md](./spec.md) — 需求规格（Intent / Scope / Approach / Requirements / Scenarios）
- [design.md](./design.md) — 技术设计（Bug 根因分析 / ADR / 文件变更）
- [tasks.md](./tasks.md) — 任务清单（`- [ ] X.Y`）

## 状态标记

- [x] 需求分析（六条反馈 + 全量日志深度分析）
- [x] 部分先行修复（崩溃类 3 项 + 备份页 Compose 化 + 统计框隐藏）
- [x] 设计审查（2026-08-23 用户确认通过）
- [x] 实施（订阅双形态切换/主题顶栏对齐/NPE 判空全部完成）
- [x] 编译门禁 + 打测试包（legado_miss_app_3.26.082301.apk）
- [ ] 验收（✅ 已完成，待用户真机验证 6.8/7.3）
