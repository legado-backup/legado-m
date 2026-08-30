# design.md - 文案调整：视频缓存开关改名 + 订阅「全部」分组标签缩短

## Technical Approach

纯字符串资源值变更，无逻辑改动：

1. `cache_play`：`app/src/main/res/values/strings.xml:1673` 值改为「播放时缓存」。UI 唯一引用点 `VideoSettingsPanelContent.kt:284`（Compose `stringResource(R.string.cache_play)`）自动生效。
2. `all_groups`：4 个语言文件值变更（见 File Changes）。UI 引用点：
   - `RssFragment.kt:1092/1100/1176/1205/1318`（标签栏胶囊、文件夹头部等，`getString(R.string.all_groups)` 自动生效）
   - `SourceFolderAdapter.kt:173`（按资源 ID 比对映射封面 key，不读值，天然不受影响）

## Architecture Decisions

### AD-01: 改字符串值不改资源名
- **Context**: 两处文案需调整，且 `cache_play` 资源名与实际语义（SimpleCache 总开关）已有偏差
- **Concern**: 是否趁机把资源名 `cache_play`/`all_groups` 一并重命名以求语义一致
- **Decision**: 只改值不改名
- **Goal**: 最小 diff、零逻辑风险、快速交付
- **Tradeoff**: 资源名与文案语义的轻微不对齐保留（`cache_play` 名字仍在），接受——引用点极少且均有注释
- **Status**: Proposed

### AD-02: 订阅「全部分组」缩短为「全部」但不动书源侧同名词
- **Context**: 仓库中「全部分组」出现在多处（高亮规则「查看全部分组」、书源搜索对话框「是否切换到全部分组？」）
- **Concern**: 用户要求是否应波及所有「全部分组」文案
- **Decision**: 仅改 `all_groups`（订阅页专用字符串）；书源搜索对话框为硬编码中文、高亮规则为独立字符串，均不在本次范围
- **Goal**: 精准命中用户反馈的订阅页场景，不产生范围外 UI 变化
- **Tradeoff**: 全 App 内"全部分组"字样不再唯一（书源搜索对话框仍是四字），接受——场景隔离，用户无感知冲突
- **Status**: Proposed

## Data Flow

无数据流变更。文案变更仅影响显示层：

- 视频设置：`videoCache` 配置（SharedPreferences）→ `VideoSettingsPanelContent` 渲染 → 显示新文案「播放时缓存」，勾选逻辑不变
- 订阅页：分组数据流不变 → `RssFragment` 标签渲染 → 特殊文件夹显示「全部」；封面存取 key（`KEY_ALL_GROUPS`）不变

## File Changes

| 文件 | 操作 | 变更内容 |
|------|------|---------|
| `app/src/main/res/values/strings.xml` | 修改 | `cache_play`: 边下边播 → 播放时缓存；`all_groups`: All groups → All |
| `app/src/main/res/values-zh/strings.xml` | 修改 | `all_groups`: 全部分组 → 全部 |
| `app/src/main/res/values-zh-rHK/strings.xml` | 修改 | `all_groups`: 全部分組 → 全部 |
| `app/src/main/res/values-zh-rTW/strings.xml` | 修改 | `all_groups`: 全部分組 → 全部 |
| `app/src/main/assets/updateLog.md` | 修改 | 顶部追加条目：①「边下边播」更名「播放时缓存」②订阅「全部分组」缩短为「全部」 |
