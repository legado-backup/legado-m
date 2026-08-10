# P5 书源管理（BookSource）

> 参考：现状 BookSourceActivity/Edit/Debug 全保留；legados 卡片列表、SwipeActionContainer 左滑动作、youfeng 高亮预置。长按 BottomSheet 富操作，编辑功能一个不少。

## 一、布局结构（文字框图）

```
┌──────────────────────────────────┐
│ 磨砂顶栏：返回│书源(N)│搜索 │更多    │
├──────────────────────────────────┤
│ 分组筛选 chips（全部/启用/我的/订阅） │
├──────────────────────────────────┤
│ ┌────────┬───────────────┐       │
│ │启用开关 │ 书源名(16sp)          │
│ │Primary │  网址/最近(14sp 灰)     │
│ └────────┴───────────────┘       │
│ （卡片18dp，左滑=快捷）               │
├──────────────────────────────────┤
│ 长按 → BottomSheet：编辑/调试/复制/  │
│        移到分组/删除                 │
└──────────────────────────────────┘
```

## 二、交互流程

| 触发 | 行为 |
|------|------|
| 点行 | 进编辑（BookSourceEditActivity） |
| 启用开关 | 即时启用/禁用（本地 db，不重请求） |
| 左滑 | 快捷：编辑 / 调试 / 复制 URL |
| 长按 | BottomSheet：分组管理、删除、移动、检查源 |
| 顶栏"更多" | 批量选择（全选/反选）、导入导出 |
| 分组 chip 长按 | 分组管理 Dialog |

## 三、Compose 组件实现思路

- 列表：`LazyColumn` + `CardSourceItem`（`SwipeActionContainer` 封装左滑删除/编辑，参考 legados SwipeActionContainer 成品）。
- 开关：复用 `SettingsSwitch`；长按用 `combinedClickable(onClick,onLongClick)`。
- 空态/加载：`EmptyState` 复用。
- 编辑页暂不 Compose 化（JSON 编辑器/RuleEngine 复杂度高），保留 View，仅换壳（圆角/阴影一致）。

## 四、绘图 Prompt

```
Material 3 Android 阅读App 书源管理页高保真：卡片列表每行含圆形启用开关
+ 书源名 + 灰色网点，分组chips可横滑，扁平磨砂顶栏，留白充足，
一个卡片左滑露出底操作（编辑/调试），柔和低饱和配色。
```

## 五、Key NFR

- 编辑/调试二级页不改业务逻辑（规则引擎不碰）。
- 分组数据与 `precise-manage` 保持一致。