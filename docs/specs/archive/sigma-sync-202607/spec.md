# Spec: 同步阅读 Sigma 2026-07 最新提交

## Intent

将阅读 Sigma（Luoyacheng/legado）2026-07-03~07-04 的 4 个提交同步到当前项目，确保 bug 修复和配置更新不遗漏。

## Scope

### In Scope
- WebDAV 进程同步 forEach 循环 bug 修复
- 预设布局切换后翻页动画不刷新 bug 修复
- 内置订阅源 CSS 选择器和域名更新
- 搜索线程默认值 16→32
- 预下载默认值 10→2
- joinToString Kotlin 惯用法优化

### Out of Scope
- 其他 Sigma 提交（2026-03 及更早已全部同步）
- 新功能开发
- UI/UX 优化（已在 2026/07/04 单独完成）

## Approach

### Selected Approach: 逐提交精准同步

按照上游提交逐个应用变更，确保每处修改与上游完全一致。这种方式最安全，因为变更量小（5 个文件、7 处修改），可以直接验证。

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| git merge 上游 | 直接 merge Sigma/main | 变更量大（7228 commits ahead），merge 冲突风险极高，且我们已有 Sigma 没有的 UI/UX 优化 |
| git cherry-pick | 挑选 4 个提交 cherry-pick | 需要添加上游 remote，且 commit 可能依赖之前的提交上下文 |
| 手动逐文件同步 | 读取上游 diff，手动应用到本地 | ✅ 选定方案，变更量小，可控性高 |

### Drawbacks

- 手动同步可能遗漏细微差异（如行尾符、import 顺序）
- 内置订阅源 JSON 文件较大，完整替换需仔细对比

### Prior Art

- 本项目此前已从 Sigma 同步了大量功能（7228 commits 中的绝大部分）
- 本次同步的是最近 4 个提交，是最后的增量

## Requirements

| ID | 需求 | 优先级 |
|----|------|--------|
| REQ-01 | AppWebDav.kt 中 forEach 循环的 `return` 改为 `return@forEach`（2处） | P0 |
| REQ-02 | ReadBookActivity.kt 中新增 `13 -> upPageAnim()` case | P0 |
| REQ-03 | BgTextConfigDialog.kt 中事件列表新增 13 | P0 |
| REQ-04 | ReadBookActivity.kt 中 joinToString 惯用法优化 | P2 |
| REQ-05 | rssSources.json 中"源仓库"CSS 选择器更新 | P1 |
| REQ-06 | rssSources.json 中"导入"域名更新 | P1 |
| REQ-07 | rssSources.json 中新增字段补全 | P1 |
| REQ-08 | AppConfig.kt 中 threadCount 默认值 16→32 | P2 |
| REQ-09 | AppConfig.kt 中 preDownloadNum 默认值 10→2 | P2 |

## Scenarios

### Scenario 1: WebDAV 同步多本书
- **Given**: 用户有多本书使用 WebDAV 同步阅读进度
- **When**: 某本书的进程文件不存在或不需要同步
- **Then**: 跳过该书，继续处理下一本（而非终止整个循环）

### Scenario 2: 切换预设布局
- **Given**: 用户在阅读界面打开文字排版配置
- **When**: 选择一个预设布局（如"舒适"→"紧凑"）
- **Then**: 翻页动画也随之更新，与新的布局匹配

### Scenario 3: 新安装用户默认配置
- **Given**: 全新安装的用户
- **When**: 首次使用搜索和预下载功能
- **Then**: 搜索线程默认 32，预下载默认 2（而非旧的 16 和 10）

### Scenario 4: 内置订阅源可用
- **Given**: 用户使用内置的"源仓库"订阅源
- **When**: 订阅源获取最新源列表
- **Then**: CSS 选择器能正确匹配新 DOM 结构，域名可访问
