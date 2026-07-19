# 测试用例文档索引

> 本目录存放 Legado（阅读M）网络性能与稳定性优化项目的测试用例文档。
> 每个功能模块完成后同步生成对应的测试用例文档。

## 文档清单

| 文档 | 功能模块 | 状态 | 更新日期 |
|------|---------|------|---------|
| [P0-network-stability.md](./P0-network-stability.md) | P0-1~P0-8 网络层与稳定性优化 | ✅ 完成 | 2026-07-06 |
| [F-P0-1-debug-tools.md](./F-P0-1-debug-tools.md) | F-P0-1 调试工具集（6大工具） | ✅ 完成 | 2026-07-06 |
| [F-P0-2-backup-selector.md](./F-P0-2-backup-selector.md) | F-P0-2 备份选择器 | ✅ 完成 | 2026-07-06 |
| [F-P0-3-web-backup.md](./F-P0-3-web-backup.md) | F-P0-3 Web 端备份管理 | ✅ 完成 | 2026-07-06 |
| [F-P0-4-rss-page-selector.md](./F-P0-4-rss-page-selector.md) | F-P0-4 订阅源页面选择器 | ✅ 完成 | 2026-07-06 |
| [P1-A3-cookie-lru.md](./P1-A3-cookie-lru.md) | P1-A3 CookieStore LRU 淘汰 | ✅ 完成 | 2026-07-06 |
| [P1-A6-proxy-client-lru.md](./P1-A6-proxy-client-lru.md) | P1-A6 proxyClientCache LRU 上限 | ✅ 完成 | 2026-07-06 |
| [P1-C3-connection-pool.md](./P1-C3-connection-pool.md) | P1-C3 连接池调优 | ✅ 完成 | 2026-07-06 |
| [P1-C5-custom-ip-lru.md](./P1-C5-custom-ip-lru.md) | P1-C5 customIp LRU 上限 | ✅ 完成 | 2026-07-07 |
| [P1-B1-backstage-webview-runblocking.md](./P1-B1-backstage-webview-runblocking.md) | P1-B1 BackstageWebView runBlocking 修复 | ✅ 完成 | 2026-07-07 |
| [P1-B2-bottom-webview-dialog-runblocking.md](./P1-B2-bottom-webview-dialog-runblocking.md) | P1-B2 BottomWebViewDialog runBlocking 优化 | ✅ 完成 | 2026-07-07 |
| [F-P1-6-cronet-upgrade.md](./F-P1-6-cronet-upgrade.md) | F-P1-6 Cronet 网络引擎升级（128→149） | ✅ 完成 | 2026-07-07 |
| [F-P1-8-source-folder-view.md](./F-P1-8-source-folder-view.md) | F-P1-8 书源/订阅源分组文件夹视图 | ✅ 完成 | 2026-07-07 |
| [P1-C4-memory-leak-fix.md](./P1-C4-memory-leak-fix.md) | P1-C4 内存泄漏治理（4 处无界缓存改 LRU + 删源清理） | ✅ 完成 | 2026-07-07 |
| [F-P1-1-auto-task-system.md](./F-P1-1-auto-task-system.md) | F-P1-1 自动任务系统（cron 定时 JS 脚本） | ✅ 完成 | 2026-07-08 |
| [F-P1-2-highlight-rule-system.md](./F-P1-2-highlight-rule-system.md) | F-P1-2 高亮规则系统（9 通道样式 + 手动高亮 + 分组 + 预设） | ✅ 完成 | 2026-07-08 |
| [F-P1-3-debug-log-floating-ball.md](./F-P1-3-debug-log-floating-ball.md) | F-P1-3 调试日志悬浮球（级别过滤 + 生命周期跟随） | ✅ 完成 | 2026-07-08 |

## 测试级别说明

| 级别 | 说明 | 验证方式 |
|------|------|---------|
| Level 1 | 单元测试 | `./gradlew test` 自动化执行 |
| Level 2 | 集成测试 | APK 编译通过 + 模块间交互验证 |
| Level 3 | 端到端验证 | 真机安装 APK，用户实际操作验证 |

## 规范

- 每个功能模块完成后**必须**同步生成测试用例文档
- 测试用例需覆盖 3 类场景：正常业务用例 + 边界值用例 + 异常/非法输入用例
- 文档命名格式：`{任务编号}-{功能名称}.md`
- 真机验证结果由用户填写，AI 负责提供测试步骤和预期结果
