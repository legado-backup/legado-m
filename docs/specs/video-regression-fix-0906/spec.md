# spec.md — video-regression-fix-0906

## Intent
修复用户真机实测的 4 个播放器回归/缺陷：嗅探播放下滑（解码失败兜底+DoH 熔断+嗅探复用）、书源切布局即时生效、书源上滑上下部恢复、分类列表页三点死按钮。

## Scope

### 做什么
1. ExoPlayer 4003 解码失败兜底：ERROR_CODE_DECODING_FAILED 时重建播放器实例重试一次（同 URL），失败再降错误提示。
2. DoH server#2 快速熔断：连续失败达阈值后本会话内跳过 #2（仅用 #1 并行/单发），避免无效等待。
3. 书源切布局短路重采集：switchLayoutMode 后书源重启播放时，若已解析 videoUrl 且章节未变 → 跳过 getContent/三层嗅探直接 setUp 播放（失败回退全量采集）。
4. 书源上滑/上下部恢复：VideoPlaylistHolder 队列兜底注入（详情页/播放器直进入口至少单元素队列，有兄弟列表注入全列表）；switchToBookFromList 无队列时降级集内切换（upDurIndex）；onBookVerticalFling 静默路径补 toast。
5. ExploreShowActivity 三点接线：ModernActionPopup 收纳"第 N 页"跳页，删除三横线 pageButton。

### 不做什么
- 不推翻 video-booksource-align-rss AD-01 单页化决策（不恢复多页 ViewPager）。
- 不改嗅探规则引擎本体（SniffEngine 三层解析逻辑不动）。
- 不做订阅源语义对齐改动（书源滑动语义条件化已在 design 披露）。
- 不新增分类列表页搜索/换源功能（原版无此功能）。

## Approach

### Selected Approach
- 问题1a 解码失败兜底：在 ExoPlayer 错误回调（videoPlayError 事件源头）识别 4003 且本 token 未重试过 → 释放重建播放器实例后同 URL 重试一次。
- 问题1b DoH 熔断：DohDns 内 server#2 连续失败 ≥5 次后置会话级熔断标记，本进程内不再尝试 #2。
- 问题2 短路重采集：startPlayBookChapter/Pipeline 入口加快速路径守卫（book 非空、videoUrl 非空、chapter 未变 → 直接 setUp+seek 恢复）。
- 问题3 队列兜底：BookInfoActivity/BookInfoComposeActivity/MyFeatureBooksActivity 启动播放器前注入 VideoPlaylistHolder（兄弟列表或单元素）；switchToBookFromList 邻居为空时降级 upDurIndex；onBookVerticalFling 静默返回改 toast。
- 问题4：ExploreShowActivity.moreButton 接 ModernActionPopup（"第 N 页"），删 pageButton。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 问题3：恢复书源多页 ViewPager（回退 AD-01） | 推翻既有决策，需重建占位页/双索引镜像，回归面大（历史上三类状态失步事故） |
| 问题3：仅隐藏上滑手势 | 用户明确要求恢复行为，隐藏是倒退 |
| 问题2：先解析后拆除原子切换 | 双容器并存需重审六步时序契约，回归风险显著大 |
| 问题1b：直接下线 DoH | server#1 并行成功是现网主要解析通道，整体下线风险大；熔断仅摘除已死的 #2 |
| 问题4：补搜索/换源菜单 | 原版此页无此功能，属新功能范畴 |

### Drawbacks
- 解码失败重试对真损坏流会多一次失败等待（约 1~2s）；兜底：仅重试一次。
- 书源短路重采集在播放地址有时效性时可能失败；兜底：失败自动回退全量采集链。
- 书源上滑语义条件化（有列表=跨影片，无列表=集内/边界提示），与订阅源"永远换文章"不一致；兜底：边界均 toast 明示。
- DoH 熔断后若 server#2 恢复需重启进程才恢复；兜底：熔断仅会话级，且 #1 正常时不影响解析。

## Requirements

### Requirement: 快速切换视频不因解码失败而终止播放
沉浸式/传统布局快速切换视频（上一部/下一部/选集/滑动）时，若 ExoPlayer 报 4003 解码失败且流本身可解码，自动重建播放器重试一次并成功播放；真损坏流给出错误提示。

#### Scenario: 快速切换触发解码竞态
- **WHEN** 2 秒内连续切换 2 次视频且旧解码器释放与新实例竞争
- **THEN** 出现 4003 时自动重建重试一次并成功播放（AppLog 留"解码失败重建重试"标记）

#### Scenario: 真损坏流
- **WHEN** 重试仍 4003
- **THEN** 呈现既有"播放失败"提示，不无限重试

### Requirement: DoH 死节点快速熔断
DoH server#2 连续解析失败达阈值后，本会话内不再尝试该节点；server#1 解析不受影响。

#### Scenario: server#2 持续不可达
- **WHEN** server#2 连续失败 ≥5 次
- **THEN** 本会话后续解析仅用 server#1（AppLog 留熔断标记），解析延迟不回退

### Requirement: 书源切布局立即生效且无长死窗
沉浸式/传统布局互切（书源）后立即完成容器切换；若已解析 videoUrl 有效则短路复用（无三层嗅探等待），失效才回退全量采集。

#### Scenario: 有效 videoUrl 切布局
- **WHEN** 书源播放中切换布局且当前章节已解析出视频地址
- **THEN** 容器立即切换并复用地址起播（无 getContent/嗅探等待），AppLog 留"短路重采集"标记

#### Scenario: 地址失效回退
- **WHEN** 复用地址起播失败
- **THEN** 自动回退全量采集链并成功起播

### Requirement: 书源上滑/下滑切换恢复可用
书源沉浸式上滑/下滑在有播放队列时跨影片切换，无队列时降级集内切换或边界 toast；不再出现静默无反应。详情页直进播放有可用的切换上下文。

#### Scenario: 列表入口进入（有队列）
- **WHEN** 从发现/搜索/书架列表进入书源视频并上滑
- **THEN** 切换到队列下一影片并自动起播

#### Scenario: 详情页直进（无队列）
- **WHEN** 从书籍详情页直进播放且 TOC 多集
- **THEN** 上滑切换上/下一集并自动起播；单集则 toast"已是最后一个视频/已到开头"

#### Scenario: 静默路径消除
- **WHEN** 播放器未就绪时滑动
- **THEN** toast 提示而非无反应

### Requirement: 分类列表页三点菜单可用
ExploreShowActivity 右上角三点点击弹出含"第 N 页"跳页的菜单；原三横线按钮移除，功能不丢失。

#### Scenario: 点击三点
- **WHEN** 经典发现页进入分类列表页点击右上角三点
- **THEN** 弹出菜单含"第 N 页"，选择页码后列表跳转

#### Scenario: 功能不回归
- **WHEN** 使用页码跳转
- **THEN** 行为与原三横线按钮一致
