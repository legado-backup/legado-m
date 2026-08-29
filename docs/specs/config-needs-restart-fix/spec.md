# spec.md — 配置修改需重启生效 + 视效对齐 archive

## Intent

修复一类同根因的前端回归：**多个界面修改配置后必须重启才生效**（订阅顶栏残留 + 书架布局失效），并缩小书架视效与 archive 的差距。目标：配置即时生效、无残留、视效向 archive 基线收敛。

## Scope

### In（本次实现）

- **订阅顶栏**：modern↔classic 切换顶栏 primaryBar/tagsBar 无残留、即时生效
- **书架布局**：`BookshelfScreen` 5 项渲染快照响应式化 + margin/listItemStyle/introLines 三配置接入；布局/分组/书名/列表样式/边距即时生效
- **结构重建事件**：新增 `BOOKSHELF_STRUCTURE_CHANGED`，`applyBookshelfConfig` 分类发事件，style1/2 双侧 `rebuildBookshelfContent()`
- **书架视效对齐**：先产出 OURS vs archive 差异清单交用户确认后收敛（间距/卡片/封面比例/边距）
- **诊断日志**：统一 tag 插桩实证后清除
- **ui-standards 沉淀** + 文档同步
- **真机 L2 验证**

### Out（明确不做）

- 不做书架标签管理（BookshelfTagManage）功能补齐（另文）
- 不做 style1 `BooksFragment`/旧 Adapter 死代码清理（另文，避免扩大改动面）
- 不改书籍数据/排序逻辑、不做 `BookshelfComposeItems/ComposeList` legacy 组件复用（仅登记防复燃）
- 不做顶栏样式重构、不做非书架同型屏改造（explore/rss/my/readrecord/video/toc/widget 已确认有结构重建或合理本地编辑态）

## Approach

### Selected Approach

**「配置响应式化 + 结构重建事件」双管齐下，对齐 archive。**

1. **诊断实证先行**：订阅 `RssModeSwitch` + 书架 `BookshelfConfig` 统一 tag 插桩，真机复现读日志锁定断链，再精准修
2. **订阅顶栏复位**：`applyRssMode` 内基于目标模式做顶栏三态复位（清空标签 + 复位可见性 + 覆盖监听）
3. **书架渲染快照响应式化**：`BookshelfScreen` 顶部 `remember{AppConfig.x}` 改受控入参，Fragment 在结构重建回调重读传入；补齐 margin/listItemStyle/introLines 消费
4. **结构重建事件**：新增 `BOOKSHELF_STRUCTURE_CHANGED`，结构类配置变更发此事件，双侧 rebuild 使 Compose 配置重算
5. **视效对齐**：先产出差异清单经用户确认再收敛
6. **L2 验证**：真机逐项即时生效

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 仅将 `remember{AppConfig.x}` 改 collectAsState 订阅 AppConfig | AppConfig 为普通 SharedPreferences 非 Compose 状态源，改造基建面大；archive 也不用此方案 |
| 仅发 `BOOKSHELF_REFRESH` 覆盖结构配置 | 语义混乱，无法区分「刷数据/重建布局」；archive 已明确双轨，跟随 archive 更稳 |
| 只修单侧（仅 style1 或订阅） | 另一侧仍不生效，用户感知为"部分不生效"，必须双侧+跨模块统一 |
| 直接照搬 archive 全量替换 OURS 书架 | 破坏 OURS 已 Compose 化拆分（archive-gap 认定的"保留特色"），改动面过大 |
| 手工在弹框关闭后触发 recomposition hack | 治标，未根治 remember 快照与结构重建机制，回归风险高 |

### Drawbacks

- 结构/数据事件分界需清晰划线，划错可能误刷/漏刷
- 结构重建会清空 items 重载，需防闪屏/丢滚动位置
- 视效对齐边界需用户确认，避免过度改动与习惯冲突
- 需真机验证；临时日志需善后清理
- 本次修复面跨订阅+书架多文件，回归面较广

### Prior Art

- archive fork `legado-08172114`：事件双轨（`BOOKSHELF_REFRESH`+`BOOKSHELF_STRUCTURE_CHANGED` → `rebuildBookshelfContent`）；Compose 视效基线（`BookshelfComposeList` RoundedCard/Classic、`BookshelfComposeCover`、`BookListCardComponents`）
- 本项目 `BookshelfConfigDialog.kt`（Compose 弹框）已在 D1 批完成；缺事件消费链
- ui-style-unify-deep-fix S 批：订阅页切换「监听 guard/状态重置/事件兜底」six 项，本 bug 为其后存活的顶栏残留分支

## Requirements

1. **订阅顶栏即时生效**：modern→classic 返回后顶栏立即显示经典标签，反向对称，无新版残留
2. **书架布局即时生效**：layout/groupStyle/showBookname/listItemStyle/introLines/sort/margin 修改后立即反映，无需重启
3. **书架三配置补齐**：margin/listItemStyle/introLines 由"改了无效"变为"即时生效"
4. **数据刷新类仍走原路径**：showUnread/更新时间/快滑/读后置顶 仅刷数据，不重建
5. **结构重建防闪屏/丢状态**：rebuild 不闪白、不丢滚动位置（除非值变化）
6. **双侧统一**：style1（分组 Tab）与 style2（文件夹）配置均即时生效
7. **视效对齐 archive**：差异清单经用户确认后收敛（间距/卡片/封面比例/边距）
8. **无硬编码色**：沿用 AppShapes/主题 token
9. **无调试残留**：诊断日志后清除，Grep 确认 0
10. **不破坏既有功能**：书籍数据/排序/分组 Tab/文件夹交互/ S 批六项回归不变

## Scenarios

### 场景 A：订阅新版→经典（主 bug A）
1. 当前新版订阅
2. 设置切经典，返回订阅 Tab
3. **期望**：顶栏立即显示经典分组/类型胶囊 + 二级源标签
4. **现状**：残留新版分类标签，需重启

### 场景 B：书架切网格列数（主 bug B）
1. 书架列表布局
2. 顶栏菜单→书架布局→切「网格4」
3. **期望**：返回后立即 4 列网格
4. **现状**：仍列表，需重启

### 场景 C：书架分组/书名/列表样式/简介行数/边距
1. 修改任一项
2. **期望**：立即反映（含 margin/listItemStyle/introLines 由无效转生效）
3. **现状**：需重启

### 场景 D：数据刷新类开关
1. 修改「显示未读/更新时间/快滑/读后置顶」
2. **期望**：仅数据刷新，不重建布局

### 场景 E：书架视效 archive 对照
1. 书架网格/列表观感与 archive 快照对比
2. **期望**：间距/封面比例/卡片/边距经确认后收敛一致

### 场景 F：冷启动对照
1. 经典/特定书架布局下冷启动
2. **期望**：直接正确显示（确认原重启生效路径不改）