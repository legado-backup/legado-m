# 文件夹封面替换回归修复 — 规格

## Intent

修复本 fork 中「书架 / 订阅源文件夹」自定义封面替换功能失效的回归问题。用户长按文件夹分组 ->「选择图片」替换封面后，期望封面立即在文件夹网格中刷新显示；当前实际表现为替换后仍显示默认文件夹图标，替换无效果。

## Scope

### 范围内

- **订阅 / 书源文件夹**：`SourceFolderComposeGrid` 封面替换的 Compose state 刷新
- **订阅 / 书源文件夹**：恢复默认封面的 Compose state 刷新
- **书架文件夹**：确认 `GroupCover`（`BookGroup.cover`）替换链路在 Compose 化后是否失效；若失效一并修复
- 两者行为一致性：替换 / 恢复默认 / 初始化加载三个环节均正确

### 范围外

- 不改封面文件复制、MD5 命名、数据库 upsert 逻辑（已有实现正确）
- 不动 View 版 `SourceFolderAdapter` 的缓存机制（保留，供非 Compose 分支使用）
- 不改封面网络加载 / 缓存策略
- 不改 UI 尺寸 / 间距 / 圆角等视觉参数（`folder-cover-ratio-archive-align` 已闭环）

## Approach

### Selected Approach

订阅端：在 `SourceFolderComposeGrid` 的数据源层补齐双向同步。具体为：

1. 让 `folderComposeCovers` 成为替换 / 恢复真正被更新的 **唯一 Compose 状态源**；
2. 在现有 `folderAdapter.updateCover(groupKey, cover)` 调用处**同步更新 `folderComposeCovers`**（利用 `mutableState` 赋值触发重组）；
3. 复核初始化 `initFolderComposeView` 时已从 DB 一次性加载 `folderComposeCovers`，保证流程闭环。

持续目标：**Compose 渲染分支与 View 渲染分支各自持有能正确刷新的数据源**，逻辑集中在 `RssFragment`。

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 方案 A：仅更新 `folderComposeCovers`，废弃 `folderAdapter.updateCover` | 只维护 Compose state，去掉 View 分支调用 | 保留了 View 版 adapter 与回调（`upCovers`/`updateCover`），为避免将来 View 分支再次失同步，改为两者同步更稳妥 |
| 方案 B：让 `SourceFolderComposeGrid` 也走 View adapter 数据 | 复用 `coverCache` 作为唯一数据源 | Compose 渲染读纯 Kotlin `mutableStateOf` map 更直接；反向引入 adapter 依赖，耦合加重 |
| 方案 C：全局事件刷新（事件总线触发 `initFolderComposeView` 重新加载 DB） | 懒规避单个 state 更新 | 每次替换都重查 DB + 全量重组，开销大、非最小改动 |

被选定方案改动最小、最贴近现有代码结构，且同步更新两个分支避免未来回归。

### Drawbacks

- 两处调用点（替换、恢复）都需要成对维护 `folderAdapter.updateCover` + `folderComposeCovers` 更新，日常维护需留意同步；已在 tasks / 注释中显式标注。
- 书架侧若确认需修复，涉及 DB flow 驱动重组的验证，存在真机表现与静态分析不一致的风险（需真机回测确认）。

### Prior Art

- 原版书架文件夹封面即采用 `BookGroup.cover` + DB flow 驱动；订阅文件夹封面新近由 View 适配器迁移至 Compose（`SourceFolderComposeGrid`），迁移时遗漏了写入侧同步，是本次回归根因。

## Requirements

1. 订阅文件夹：长按分组 -> 选择并替换封面后，**当前界面立即**显示新封面。
2. 订阅文件夹：恢复默认封面后，**当前界面立即**恢复默认文件夹图标样式。
3. 书架文件夹：替换封面后封面显示即刻生效（不强制重启）。
4. 初始化进入文件夹视图时，DB 中已有自定义封面正确加载显示（不回归）。
5. 修改后不引入新的编译错误、不引入多余日志（符合 AGENTS.md logging 规范）。

## Scenarios

### 场景 1：订阅文件替换封面（主路径）
1. 用户切到订阅页，文件夹样式（sourceGroupStyle=2，sourceLayout>=2）。
2. 长按某真实分组 -> 弹菜单「选择图片」。
3. 从相册选一张图。
4. **期望**：该分组卡片封面立即变为所选图片。
5. **现状**：封面不变化（仍显示默认文件夹图标）——即本 bug。

### 场景 2：订阅文件夹恢复默认封面
1. 某分组已有自定义封面。
2. 长按 -> 菜单出现「恢复默认」。
3. 点恢复。
4. **期望**：封面立即恢复默认文件夹图标。
5. **现状**：封面不变——同因 bug。

### 场景 3：书架文件夹替换封面
1. 书架 folder 样式，进入根分组文件夹视图。
2. 长按分组（`GroupEditDialog`）替换封面保存。
3. **期望**：分组封面立即更新。
4. 需真机确认是否同因失效；若失效按同思路修复。

### 场景 4：重启后封面仍生效（无回归）
1. 替换并保存封面。
2. 冷启动进入对应文件夹视图。
3. 封面仍显示自定义图片（验证 DB 持久化链路未破坏）。