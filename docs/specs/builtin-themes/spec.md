# Spec: 新增 8 个内置主题

## Intent

为阅读 App 提供更丰富的主题选择，覆盖当前 Android 设计主流趋势（护眼绿、莫兰迪、M3 暗色、互补色高亮、OLED 友好、低蓝光暖调），满足不同用户群体的审美和护眼需求。

## Scope

### In Scope
- 在 themeConfig.json 中新增 8 个主题配置
- 确保 WCAG AA 对比度合规
- 确保新主题在 ThemeListDialog 中正确显示和切换
- 更新 updateLog.md

### Out of Scope
- 修改 ThemeConfig 数据模型（不需要新字段）
- 修改主题切换 UI 布局（复用现有）
- 新增主题自定义编辑器
- 新增主题预览功能
- 阅读页排版主题（ReadBookConfig，独立系统）

## Approach

### Selected Approach: 直接追加 JSON 条目

在现有 `themeConfig.json` 末尾追加 8 个新主题对象。这是最简单的方案，因为：
1. ThemeConfig.Config 数据模型不变，所有新主题的字段都已有默认值
2. ThemeConfig.configList 加载逻辑会自动读取新条目
3. ThemeListDialog 会自动显示新主题
4. 无需修改任何 Kotlin 代码

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 新增主题 Kotlin 代码 | 在 DefaultData.kt 中硬编码新主题 | JSON 配置更灵活，用户可导入/导出，Kotlin 硬编码不可修改 |
| 从网络下载主题包 | 启动时从 CDN 下载最新主题 | 增加网络依赖和启动延迟，离线场景无法使用 |
| 仅新增 5 个日间主题 | 不加夜间主题 | 夜间模式是阅读 App 高频场景，3 个夜间主题是必须的 |

### Drawbacks

- 新安装用户首次打开主题列表将看到 12 个主题（4 原有 + 8 新增），选择过多可能造成决策疲劳
- 已有自定义主题配置的用户需要手动导入新主题（`getConfigs()` 优先读取用户配置，不会自动合并）

### Prior Art

- 微信读书：护眼绿主题
- 豆瓣阅读：莫兰迪色系
- Google Play Books：M3 暗色 #121212
- Discord/Spotify：暗色紫主题

## Requirements

| ID | 需求 | 优先级 |
|----|------|--------|
| REQ-01 | 在 themeConfig.json 中追加 8 个新主题 JSON 对象 | P0 |
| REQ-02 | 每个新主题的 primaryColor、accentColor 在 backgroundColor 上满足 WCAG AA (≥4.5:1) | P0 |
| REQ-03 | 日间主题 backgroundColor 为浅色系，bottomBackground 略深 | P1 |
| REQ-04 | 夜间主题 backgroundColor 为深色系，OLED 友好 | P1 |
| REQ-05 | 主题名称 2-4 字中文，不与现有主题重名 | P1 |
| REQ-06 | 新主题在 ThemeListDialog 中可点击切换 | P0 |

## Scenarios

### Scenario 1: 新用户首次使用
- **Given**: 全新安装的用户
- **When**: 打开主题列表
- **Then**: 看到 12 个主题（4 原有 + 8 新增），可正常切换

### Scenario 2: 切换到绿意主题
- **Given**: 用户当前使用默认主题
- **When**: 在主题列表中选择"绿意"
- **Then**: 工具栏变深绿，背景变浅绿，高亮变深橘红，底栏变浅绿

### Scenario 3: 切换到暗夜蓝主题
- **Given**: 用户当前使用日间主题
- **When**: 在主题列表中选择"暗夜蓝"
- **Then**: App 切换到夜间模式，背景变 #121212，工具栏变深蓝，高亮变亮蓝

### Scenario 4: 已有自定义配置的用户
- **Given**: 用户已有自定义主题配置文件 (filesDir/themeConfig.json)
- **When**: 打开主题列表
- **Then**: 看到用户自定义的主题列表（可能不包含新增主题，需手动导入）
