# Design: 新增 8 个内置主题

## Technical Approach

直接在 `themeConfig.json` 中追加 8 个主题配置对象。ThemeConfig.Config 数据模型无需变更，加载和应用逻辑自动适配。

## Architecture Decisions

### AD-01: JSON 配置而非 Kotlin 硬编码
- **Context**: 内置主题可以通过 JSON 文件或 Kotlin 代码定义
- **Concern**: Kotlin 硬编码需要重新编译才能修改主题，JSON 可热更新
- **Decision**: 使用 JSON 配置，追加到现有 themeConfig.json
- **Goal**: 保持与现有主题系统一致，支持导入/导出/分享
- **Tradeoff**: JSON 加载有微量反序列化开销，但可忽略
- **Status**: Accepted

### AD-02: 仅追加不修改原有 4 个主题
- **Context**: 原有 4 个主题已存在用户偏好
- **Concern**: 修改原有主题可能导致用户已选主题外观突变
- **Decision**: 仅在 JSON 数组末尾追加 8 个新主题，不修改原有 4 个
- **Goal**: 零破坏性，已有用户无感知
- **Tradeoff**: 原有主题的配色问题（如默认主题的棕色主色）不在本次优化范围
- **Status**: Accepted

## Data Flow

```
themeConfig.json (assets)
    │
    ├─ [0] 默认 (day) — 不变
    ├─ [1] 典雅蓝 (day) — 不变
    ├─ [2] 黑白 (night) — 不变
    ├─ [3] A屏黑 (night) — 不变
    ├─ [4] 绿意 (day) — 新增
    ├─ [5] 莫兰迪 (day) — 新增
    ├─ [6] 海洋 (day) — 新增
    ├─ [7] 薰衣草 (day) — 新增
    ├─ [8] 琥珀 (day) — 新增
    ├─ [9] 暗夜绿 (night) — 新增
    ├─ [10] 暗夜蓝 (night) — 新增
    └─ [11] 暗夜紫 (night) — 新增

ThemeConfig.configList
    → 读取 themeConfig.json
    → 自动包含 12 个主题
    → ThemeListDialog 展示 12 项
```

## File Changes

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| themeConfig.json | 数据追加 | 追加 8 个主题 JSON 对象 |
| updateLog.md | 内容更新 | 追加更新日志条目 |

## 新增主题配色表

### 日间主题（5 个）

| 主题 | primaryColor | accentColor | backgroundColor | bottomBackground | 设计理念 |
|------|-------------|-------------|----------------|-----------------|---------|
| 绿意 | #2E7D32 | #BF360C | #F1F8E9 | #DCEDC8 | 护眼绿，低视网膜刺激 |
| 莫兰迪 | #5D4037 | #3949AB | #EFEBE9 | #D7CCC8 | 高级灰调，低饱和度 |
| 海洋 | #00695C | #DD2C00 | #E0F7FA | #B2EBF2 | 冷静青绿，专注深度 |
| 薰衣草 | #7B1FA2 | #00796B | #F3E5F5 | #E1BEE7 | 优雅浅紫，年轻喜爱 |
| 琥珀 | #BF360C | #1565C0 | #FFF8E1 | #FFECB3 | 暖调书香，蓝光最低 |

### 夜间主题（3 个）

| 主题 | primaryColor | accentColor | backgroundColor | bottomBackground | 设计理念 |
|------|-------------|-------------|----------------|-----------------|---------|
| 暗夜绿 | #2E7D32 | #66BB6A | #1B1B1B | #1B1B1B | OLED+绿色低色温高亮 |
| 暗夜蓝 | #1565C0 | #4FC3F7 | #121212 | #121212 | M3推荐，Gmail同款 |
| 暗夜紫 | #7B1FA2 | #CE93D8 | #1E1E32 | #1E1E32 | Discord风格，星空氛围 |
