# ui-issues-round-20260818 — UI 问题综合整改

## 状态

🔄 **设计中**（2026-08-18 用户验收反馈 9 大 UI 问题，需求分析+**全页面深度调研完成**：Compose 化现状三分类清单 84 页逐页核实 + 功能裁剪/降级证据 C1-C5/D1-D5/✅15 项 + 用户点名 5 疑点根因核实，详证 `docs/temp-analysis/` 三份报告，见 design.md「调研结论」）

> **本 spec 的最终目标：系统性整改 UI Compose 化改造（ui-redesign-m3）遗留的 9 大用户反馈问题**，保证整改不引入新回归、不触碰阅读详情页，并对功能裁剪红线执行回溯自查。
>
> **来源**：承接 [`ui-redesign-m3`](../ui-redesign-m3/README.md) 改造进度（Phase0-3 已落地），本批次聚焦用户验收时反馈的遗留 UI 问题，逐项定位根因后精准修复。

## 功能概述

针对 2026-08-18 用户验收反馈的 **9 大 UI 问题** 进行综合整改：

1. **书架分组样式切换失效**——「标签」样式下头部不按原标签展示（`bookGroupStyle` 切换只通知不重建 fragment，且 style1 头部 Compose 结构与原版 Toolbar+TabLayout 不同）。
2. **沉浸式操作栏行为不符**——打开后只对底部导航栏生效，头部（状态栏/顶栏）未联动沉浸（`immNavigationBar` 与 `transparentStatusBar` 两开关分离）。
3. **启动页/我的页/子页面样式问题**——欢迎页样式功能被缩减、部分开关"感觉不生效"、主/子页面样式不统一、子页面 Compose 化未完成。
4. **发现/订阅缺分组设置**——无书架那样的 `GroupManageDialog` + 批量改分组功能。
5. **发现/订阅默认展示样式不符**——应为「标签」；分组/文件夹样式下搜索框应隐藏、进入文件夹后才展示且仅限当前文件夹搜索。
6. **发现/订阅三点菜单冗余**——弹出一大片分组列表（布局可切换，无存在意义），应去掉。
7. **书源编辑页被改丑**——头部「类型/启用/发现」等按钮下拉菜单改为紧凑 FlowRow 风格，需保留原样式不被改丑（订阅源编辑页保留原 XML 表单反被认可）。
8. **长按书架书本进详情页报 "book is null"**——`onBookLongClick` 只传 name/author 不传 bookUrl，`BookInfoActivity.getBook()` 查询为 null。
9. **弹框体系统一 + 组件风格统一 + 功能裁剪回溯 + 除阅读详情页外全页面 Compose 化**——统一三种弹框样式（AppDropdownMenu / AppModalBottomSheet / Dialog 族）与组件风格（SettingsToggleRow 等），自查 8 月 4 号前被私自裁剪的功能。

## 核心能力

| 整改点 | 说明 |
|------|------|
| 书架分组样式切换修复 | `bookGroupStyle` 切换后正确重建 fragment / 头部按标签展示，对齐原版 Toolbar+TabLayout 行为 |
| 沉浸式操作栏联动 | 头部（状态栏/顶栏）与 `immNavigationBar` 联动沉浸，与底部导航栏行为一致 |
| 启动/我的/子页面样式统一 | 欢迎页四要素回归与补齐、单选/滑动开关恢复生效、主/子页面样式统一、子页面 Compose 化推进 |
| 发现/订阅分组设置 | 补齐类似书架 `GroupManageDialog` + 批量修改当前书源/订阅源分组信息能力 |
| 发现/订阅展示样式对齐 | 默认「标签」样式、分组/文件夹下搜索框显隐规则（进入文件夹才展示、搜索限当前文件夹） |
| 发现/订阅三点菜单精简 | 移除动态分组列表，只保留有实际意义的菜单项 |
| 书源编辑页样式保留 | 头部按钮/下拉菜单回归原样式，不被紧凑 Compose 风格改丑 |
| 长按进详情 Null 修复 | `onBookLongClick` 补传 bookUrl，`BookInfoActivity` 可正确加载 book |
| 弹框体系统一 | 三种弹框样式（AppDropdownMenu / AppModalBottomSheet / Dialog 族）+ 组件风格（Switch/单选滑动 SettingsToggleRow 等）统一 |
| 功能裁剪回溯 | 自查 8 月 4 号之前版本被私自裁剪的功能并回补 |
| 全页面 Compose 化 | 除阅读详情页外，所有页面组件 Compose 化推进 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / 各问题根因与修复方案 / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 整改任务拆解（PR 粒度）/ 验收标准 / 真机验证项 |
| [design.md](./design.md#调研结论) | **调研结论**：全页面 Compose 化现状三分类清单（84 页逐页核实）+ 功能裁剪/降级证据（C1-C5/D1-D5/✅15 项）+ 用户点名 5 疑点根因核实 + git 基线回溯范围 |
| [regression-inventory.md](./regression-inventory.md) | **功能裁剪回溯清单**（设计阶段产出，CUT 5 / DEGRADED 5 / PRESERVED 15，含恢复方案与回执） |
| [docs/temp-analysis/compose-status-inventory.md](../../temp-analysis/compose-status-inventory.md) | 逐页 Compose 化现状盘点（84 页代码位置证据，迁移缺口 Top 页） |
| [docs/temp-analysis/regression-diff.md](../../temp-analysis/regression-diff.md) | git 基线功能裁剪回溯审计报告（只读 diff 证据） |
| [docs/temp-analysis/user-suspicion-check.md](../../temp-analysis/user-suspicion-check.md) | 用户点名 5 疑点根因调查报告（开关不生效/sourceLayout/欢迎页/布局设置/弹框盘点） |
| [checkpoint-test-report.md](./checkpoint-test-report.md) | 阶段验收真机/模拟器测试报告（可选，随实施生成） |
| **[p3-3](./p3-3/)** | **长尾页 Compose 化收尾子 spec**（spec/design/tasks 三件套，7 个长尾低频页：搜索/全文搜索/目录/订阅源管理/RSS 文章/替换规则/RSS 搜索） |

> **关联 spec**：[`ui-redesign-m3`](../ui-redesign-m3/README.md)（UI Compose 化改造主 spec，本批次承接其遗留问题整改）；设计/实现需遵循其 `ui-standards.md` 组件规格。

## 边界说明

- **阅读详情页禁止改动**：阅读器正文引擎/漫画/音频/WebView 池等内核与第三方控件保留原生 View（对齐 ui-redesign-m3 AD-02），不在本批次整改范围。
- **功能裁剪红线**：本批次为"整改回归"性质，任何整改不得再次裁剪既有功能；凡发现 8 月 4 号之前被私自裁剪的功能，纳入回溯清单回补。
- **禁止臆测**：各问题根因以需求分析确认结论为准（见功能概述），实施前先到源码核实再动手，避免凭经验臆测引入新问题。
