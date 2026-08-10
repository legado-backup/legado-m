# P8 正文内浮层（搜索/目录/替换/书签/高亮）

> 参考：DESIGN-MD "BottomSheet 底部抽屉, 高频阅读设置不放二三季内"，现状 ReadMenu/BottomWebViewDialog/HighlightStyleDialog 能力全保留。这是"减少多层弹窗"的最大改动面。

## 一、浮层清单（搜索 → 替换为 BottomSheet）

| 现状弹窗 | 新做法 | 入口 |
|---------|--------|------|
| 目录（TocDialog） | `TocSheet` | 底栏·目录（1步） |
| 书签列表 | `BookmarkSheet`（长按书签进入） | 底栏·书签 |
| 高亮列表 | `HighlightSheet`（含高亮样式切换） | 阅读选中后工具条 |
| 详情搜索 | `SearchInBookSheet` | 阅读浮层·放大镜 |
| 替换规则 | `ReplaceRuleSheet`（启用/管理） | 阅读浮层·替换 |
| 阅读更 tj | `ReadingSettingsSheet`（可拉伸） | 底栏·更多 |

## 二、交互流程

| 触发 | 行为 |
|------|------|
| 底栏"目录" | 弹 `TocSheet`（章节列表、进度百分比、多选书签） |
| 底部"更多" | `ReadingSettingsSheet`（字号/亮度/夜间/行距/对齐一屏可达；扩展含 翻页方式/字体） |
| 长按高亮文字 | 工具条：划色（色盘2行6色）→ 直接改该段样式（无二级） |
| 浮层 3s 无操作 | 自动收起为半透明胶囊（保留进度） |

## 三、Compose 组件实现思路

- 统一 `ModalBottomSheet(containerColor=surface)`，`RememberModalBottomSheetState(skipPartiallyExpanded=true)`。
- 重用组件：`BottomSheetTitle`（含返回/标题/关闭）、`ListScreen`（章节/书签通用列表）、`SliderRow`（字号/亮度）。
- 防止与正文触摸冲突：`Modifier.pointerInput` 限定 sheet 区域消费，翻页手势不误触。
- 高亮调色：升级现状 `HighlightStyleDialog` 为 chooser（色板+下划线样式，参考 youfeng Span 族）。

## 四、绘图 Prompt

```
Material 3 Android 阅读App 阅读中底部软弹抽屉(BottomSheet)高保真：
章节目录列表在纸感阅读器下半部，可拉伸，圆角顶，列表项有 分割线 与 当前章高亮，
页码百分比在底部,浅色暖黄护眼配色,抽屉外正文虚化,回收禁用多层弹窗。
```

## 五、Key NFR

- 浮层全部替代旧 Dialog，读阅设置不藏三层内。
- 所有浮层 3s 无操作自动淡隐（排除正在滚动/输入焦点）。