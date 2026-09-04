# red-team-report.md — 五轮红队对抗审查

> 对象：ui-theme-governance-followup 四文档；总判定：第 1 轮评审 **NO-GO**（1P0+4P1+P2 批）→ 整改落盘后具备开工条件

## 第 1 轮 需求覆盖（2 项）
- R1-1：README F3 根因"notifyDataSetChanged 全量重绑"已失效——现行 RoundedTagBarView L147-152 已有 sameItems 早退 → 删除无操作任务 4.3，F3 根因收敛为 LayoutTransition alpha
- R1-2：spec 缺 S-F1b（搜索跨源末部）/S-F2b（刷新中再下拉）场景 → 补录

## 第 2 轮 边界与异常（3 项）
- R2-1 (P1)：BookshelfScreen 两 state 位于 else 分支内（loading 时不组合）→ 3.2 改 state hoist+Saveable；拦截 gate 加 `books.isNotEmpty()`（防分离态读 false 放行刷新循环）
- R2-2 (P2)：F1 注入统一按 isVideo 过滤（防混排分类上滑落入文本书）；矩阵补混排用例
- R2-3 (P2)：Saveable 无 key=跨分组保持为有意决策（design 注明防实施者加 key）

## 第 3 轮 可落地性（7 项抽查）
- ①VideoPlaylistHolder.set/neighborOf/clear/Book.toSearchBook 全实存，`git show 05e4dde3c` 注入 diff 与 design 一致 ✓
- ②BookshelfScreen 结构属实，"loading 改叠加"可行（需 state hoist）✓
- ③MainTopBarView 行号精确命中；但 L703-706/720-729 旧值比较**已存在**（4.2 前半无操作），APPEARING/DISAPPEARING 确未 disable（4.1 成立）✓
- ④page 消费面实测 **15 处/14 文件**（design 只点名 3 个根层）；TocComposeScreen 吸顶分支受影响未登记 → 补登记
- ⑤**AppManagementAction.iconRes 是 @DrawableRes Int，MenuAction.icon 是 ImageVector，不可逆转换 → 任务 6.1 原文不可实现**，改为加 icon 槽位
- ⑥分型矩阵与源码相符（C 类 4 页实为 View+RecyclerView）✓
- ⑦33 宿主 override 计数精确 ✓

## 第 4 轮 完整性一致性（3 项）
- R4-1：File Changes 缺 AppManagementScaffold/AppMenuSheet/TocComposeScreen → 补
- R4-2：F1"每处 3-8 行"失实（ExploreFragment 实为 20 行三级兜底）；锚点行号漂移 → 改"以 git show 为准重新定位"
- R4-3：README 引用 red-team-report.md 死链 → 本文件补链

## 第 5 轮 对抗性破坏（5 项，含 1 P0）
- **R5-1 (P0)**：F4 v1 消费模型数学性自毁——decorView 恒不透明 backgroundColor 后，page(backgroundColor, alpha) 叠同色底=**全档位零可见变化**，且把现有效果的书源/订阅源管理一并归零 → **采纳 v2 预混不透明色模型**：`manageBgBlendedColor(base)=lerp(base, fadeTarget, 1-fraction)`（fadeTarget=浅白/深黑），三消费点（Scaffold/page/BaseActivity tint）统一换用，根治安蒙蒙/叠加/泄漏/E-Ink
- R5-2 (P1)：page 带 alpha 的 15 处消费点泄漏（TagManage 双重叠透/TocComposeScreen 吸顶分支）→ 预混方案自动消解
- R5-3 (P1)：PullToRefreshBox 外层 nestedScroll 拦截无效（onPostScroll 在内容与外层之间）→ 改 onRefresh 短路（最简）
- R5-4 (P2)：LockableViewPager 现状仅 swipeEnabled 布尔，无判定基线可"追加" → 从零实现轴向优势拦截
- R5-5 (P2)：suite 横排入口注入语义错位风险 → AD-01 Tradeoff 登记+矩阵补用例

## 量化
共发现 **1 P0 + 4 P1 + 8 P2**，全部整改落盘（v2 预混模型/层级修正/槽位重定义/无操作任务销项/补登记）。F1/F2/F3/F5 源码锚点吻合度高，F4 经模型重定后需真机 S-F4 四页×三档位实测确认视觉效果。
