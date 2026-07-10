# Spec: 抖音风格沉浸式竖屏视频播放器重设计

## Intent

将当前传统竖屏 LinearLayout 布局的 VideoPlayerActivity 重构为抖音/红果短视频风格的沉浸式竖屏视频播放器，提供更现代、更沉浸的视频观看体验。同时修复 R2 日志分析发现的 3003 Bug（R5 抓取返回播放器页面 URL）。

## Scope

### In Scope

| 编号 | 范围项 | 说明 |
|------|--------|------|
| S1 | VideoPlayerActivity UI 层重构 | LinearLayout → ConstraintLayout + ViewPager2 悬浮控件叠加 |
| S2 | ViewPager2 + Fragment 垂直滑动切换 | 上下滑动切换播放列表中的视频 |
| S3 | 三种播放状态设计 | 纯净播放态 / 竖屏常态 / 横屏全屏态 |
| S4 | 悬浮控件布局 | 左下角标题 + 右侧功能按钮（静音/收藏/倍速/设置）+ 下方全屏按钮 |
| S5 | 横屏适配 | 等比缩放居中 + 全屏按钮 + 双指缩放手势 |
| S6 | 控件显隐逻辑 | 默认隐藏 + 单击切换 |
| S7 | 设置面板（BottomSheetDialog） | 将当前所有功能重新组织到设置面板 |
| S8 | 100%功能保留 | 当前所有功能（快进快退/倍速/调试/多集/复制URL/简介/书籍信息/章节选择/菜单功能）全部保留 |
| S9 | 3003 Bug 修复 | R5 VideoUrlExtractor 增加播放器页面 URL 识别，提取 `?url=` 参数 |
| S10 | 多线路支持 | 视频详情页多播放线路支持：RssRoute 二级数据结构 + 左下方线路选择器 + 集数选择器 + 兼容单集/多集无线路场景 |

### Out of Scope

| 编号 | 排除项 | 原因 |
|------|--------|------|
| O1 | ExoPlayer/GSY 播放器核心播放逻辑 | 非本次 UI 重构范围 |
| O2 | 订阅源/书源数据层 | 非本次 UI 重构范围 |
| O3 | R5 VideoUrlExtractor 核心提取逻辑 | 只增加播放器页面 URL 识别，不重构提取逻辑 |
| O4 | HTML 版视频播放器 | 本次只重构内置播放器（VideoPlayerActivity） |
| O5 | 视频推荐算法 | 非本次范围，播放列表来自订阅源/书源 |

## Approach

### 选中方案：ViewPager2 + Fragment 垂直滑动切换

**核心架构**：
```
VideoPlayerActivity（容器，持有 ViewPager2）
├── ViewPager2（垂直方向，OrientedVertical）
│   └── VideoFragment（每个视频一个 Fragment 实例）
│       ├── 播放器视图（ExoPlayer/GSY，铺满屏幕）
│       ├── 悬浮控件层（ConstraintLayout 叠加）
│       │   ├── 左下角：视频标题
│       │   ├── 右侧竖直排列：静音/收藏/倍速/设置
│       │   └── 下方水平居中：全屏按钮（仅横屏比例视频显示）
│       └── 设置面板（BottomSheetDialogFragment）
│           ├── 快进快退按钮
│           ├── 调试面板
│           ├── 多集选择列表
│           ├── 复制URL
│           ├── 视频简介
│           ├── 书籍信息
│           ├── 章节/卷选择
│           └── 其他菜单功能（自定义按钮/配置/登录/编辑源/日志/其他播放器）
```

### Alternatives Considered

| 方案 | 描述 | 优点 | 缺点 | 决策 |
|------|------|------|------|------|
| A. ViewPager2 + Fragment | 引入 ViewPager2 垂直滑动，每个视频一个 Fragment | 原生抖音体验，滑动流畅，Fragment 生命周期管理清晰 | 架构改动大，需处理 Fragment 间播放器实例管理 | ✅ 选中（用户确认接受架构重构） |
| B. 单 Activity + 手势切换 | 保持单 Activity，上下滑动手势触发视频加载 | 架构改动小，保持现有结构 | 无滑动动画，体验差，非真正抖音风格 | ❌ 否决（体验不达标） |
| C. RecyclerView + Player | 用 RecyclerView 实现视频列表 | 复用 RecyclerView 机制 | 播放器实例管理复杂，不适合视频场景 | ❌ 否决（复杂度高） |

### Drawbacks

| 缺陷 | 影响 | 缓解措施 |
|------|------|---------|
| 架构改动大 | VideoPlayerActivity 需重构为容器 + Fragment | 保留现有 LiveEventBus 事件机制，降低改动风险 |
| Fragment 间播放器实例管理 | 需要处理播放器实例的创建/释放/复用 | 使用 ViewPager2 的 `setOffscreenPageLimit(1)` 只保留相邻1页 |
| 书籍源模式适配 | 书籍源有章节/卷结构，非视频列表 | 书籍源模式下禁用 ViewPager2 滑动，保持现有章节选择逻辑 |
| 内存占用 | 多个 Fragment 可能占用较多内存 | 非当前页的 Fragment 释放播放器，只保留视图 |

## Requirements

### 功能需求

| 编号 | 需求 | 优先级 | 验收标准 |
|------|------|--------|---------|
| REQ-1 | 竖屏全屏展示 | P0 | 视频画面铺满整个屏幕，沉浸式体验 |
| REQ-2 | 左下角视频标题 | P0 | 固定放置视频名称，支持长文本省略 |
| REQ-3 | 右侧竖直功能按钮 | P0 | 静音、收藏、倍速、设置四项核心功能 |
| REQ-4 | 横屏比例视频等比缩放 | P0 | 保留原始宽高比，不拉伸裁剪，居中展示 |
| REQ-5 | 全屏按钮 | P0 | 视频下方水平居中，点击切换横屏全屏 |
| REQ-6 | 双指缩放手势 | P1 | 双指向外拉伸触发横屏全屏，效果与全屏按钮一致 |
| REQ-7 | 横屏全屏状态功能适配 | P0 | 功能按钮集合与交互逻辑保持不变，布局适配横屏 |
| REQ-8 | 默认隐藏悬浮控件 | P0 | 默认进入纯净播放态，仅保留纯视频画面 |
| REQ-9 | 单击切换控件显隐 | P0 | 隐藏态单击显示标题+功能按钮，显示态单击恢复隐藏 |
| REQ-10 | 向下滑动播放下一个 | P0 | ViewPager2 垂直滑动，自动播放下一个视频 |
| REQ-11 | 向上滑动播放上一个 | P0 | ViewPager2 垂直滑动，播放上一个视频 |
| REQ-12 | 切换视频后纯净播放 | P0 | 控件自动隐藏，视频自动开始播放 |
| REQ-13 | 100%保留当前功能 | P0 | 所有现有功能重新组织到设置面板 |
| REQ-14 | 三种状态完整设计 | P0 | 竖屏常态/横屏全屏态/纯净播放态的布局与交互 |
| REQ-15 | 3003 Bug 修复 | P0 | R5 识别播放器页面 URL，提取 `?url=` 参数 |
| REQ-16 | RssRoute 二级数据结构 | P0 | 新增 RssRoute(name, episodes) 数据类，VideoPlay 增加 rssRoutes/rssRouteIndex 字段，与书源 volumes/episodes 范式对称 |
| REQ-17 | 左下方线路选择器 | P0 | 视频标题下方显示当前线路名称，点击弹出线路选择列表（Spinner/Dialog），切换线路后更新集数列表 |
| REQ-18 | 集数选择器 | P0 | 线路选择器下方显示当前线路的集数列表（横向滚动），点击切换集数播放 |
| REQ-19 | 多线路兼容性 | P0 | 单URL场景：不显示线路/集数选择器；多集无线路：不显示线路选择器只显示集数；多线路多集：显示线路+集数选择器 |
| REQ-20 | ruleContent 多线路格式 | P0 | ruleContent 支持嵌套 JSON 表达多线路：`[{name, episodes:[{title,url}]}]`，兼容旧版扁平 JSON 数组/多行URL |
| REQ-21 | ruleContent JS 标准数据格式规范 | P0 | 定义 ruleContent 返回数据的三种标准格式（嵌套JSON/扁平JSON/多行URL）、字段说明（name可选/episodes必须/title可选/url必须）、兼容性保证（格式2/3自动包装为单线路） |
| REQ-22 | R5 多线路通用性 5 站点验证 | P0 | 通过5个典型站点DOM分析验证R5四种模式覆盖率：Tab式(MacCMS mxtheme/stui)60%/分组式(80s模板)20%/多级嵌套式20%，并输出MacCMS指纹识别策略+三种ruleContent模板(MacCMS/80s/嵌套) |

### 非功能需求

| 编号 | 需求 | 验收标准 |
|------|------|---------|
| NFR-1 | 性能 | 视频切换动画流畅（60fps），无明显卡顿 |
| NFR-2 | 内存 | 非当前页 Fragment 释放播放器实例，内存占用不超过当前+30% |
| NFR-3 | 兼容性 | 支持 Android 7.0+（minSdk 23），适配刘海屏/全面屏 |
| NFR-4 | 向后兼容 | 书籍源模式保持现有章节选择逻辑不变 |
| NFR-5 | 编译 | 编译通过，无新增 lint 警告 |

## Scenarios

### 场景1：打开视频播放器（订阅源模式）

```
用户从订阅源列表点击视频条目
→ ReadRss 启动 VideoPlayerActivity，传入 videoUrl + videoTitle + rssEpisodes
→ VideoPlayerActivity 初始化 ViewPager2 + VideoFragment
→ VideoFragment 加载第一个视频
→ 默认进入纯净播放态（控件隐藏）
→ 视频自动开始播放
```

### 场景2：切换视频（上下滑动）

```
用户在纯净播放态向上/向下滑动屏幕
→ ViewPager2 捕获垂直滑动手势
→ 滑动到下一个/上一个 VideoFragment
→ 新 Fragment 的视频自动开始播放
→ 默认进入纯净播放态（控件隐藏）
→ 旧 Fragment 释放播放器实例
```

### 场景3：控件显隐切换

```
用户在纯净播放态单击屏幕
→ 切换到竖屏常态
→ 显示左下角标题 + 右侧功能按钮（静音/收藏/倍速/设置）
→ 若是横屏比例视频，显示下方全屏按钮
用户在竖屏常态单击屏幕
→ 切换到纯净播放态
→ 所有控件隐藏
```

### 场景4：横屏全屏切换

```
场景4a：点击全屏按钮
用户在竖屏常态点击全屏按钮
→ 切换到横屏全屏态
→ Activity 旋转为横屏
→ 视频铺满横屏
→ 功能按钮适配横屏布局

场景4b：双指缩放手势
用户在纯净播放态/竖屏常态双指向外拉伸
→ 触发横屏全屏（与点击全屏按钮效果一致）
→ 切换到横屏全屏态
```

### 场景5：设置面板

```
用户在竖屏常态点击右侧"设置"按钮
→ 弹出 BottomSheetDialog 设置面板
→ 设置面板包含：
  - 快进快退按钮（←30s / ←10s / 10s→ / 30s→）
  - 倍速选择（Spinner）
  - 调试面板（切换显示/隐藏 + 调试日志）
  - 多集选择列表（RecyclerView）
  - 复制URL按钮
  - 视频简介
  - 书籍信息（封面/书名/作者/简介）
  - 章节/卷选择（书籍源模式）
  - 其他菜单功能（自定义按钮/配置/登录/编辑源/日志/其他播放器）
用户向下滑动或点击外部关闭设置面板
```

### 场景6：3003 Bug 修复

```
R5 VideoUrlExtractor 从文章页面抓取到 URL
→ 检测 URL 是否是播放器页面 URL（包含 ?url= 或 &url= 参数）
→ 若是播放器页面 URL：
  - 提取 url 参数值
  - URL 解码
  - 返回实际视频流 URL
→ 若不是播放器页面 URL：
  - 直接返回原始 URL
→ ExoPlayer 使用实际视频流 URL 播放
```

### 场景7：书籍源模式（向后兼容）

```
用户从书籍章节列表点击视频章节
→ VideoPlayerActivity 初始化
→ 检测到 book != null（书籍源模式）
→ 禁用 ViewPager2 垂直滑动
→ 显示书籍信息区 + 章节/卷选择区（保持现有逻辑）
→ 视频播放器铺满屏幕上方区域
→ 单击切换控件显隐（与订阅源模式一致）
```

### 场景8：多线路选择（订阅源多线路模式）

```
用户从订阅源列表点击视频条目（如奈飞中文网）
→ ReadRss 启动 VideoPlayerActivity
→ R5/ruleContent 解析返回多线路数据 List<RssRoute>
  场景8a：ruleContent 返回嵌套 JSON
    → parseRssRoutes 解析 [{name:"线路1", episodes:[...]}, {name:"线路2", episodes:[...]}]
  场景8b：R5 自动抓取（ruleContent 为空）
    → VideoUrlExtractor 增强抓取线路+集数结构
    → 返回 List<RssRoute>
→ VideoPlay.rssRoutes = routes, rssRouteIndex = 0
→ VideoPlay.rssEpisodes = routes[0].episodes（兼容现有逻辑）
→ VideoFragment 显示：
  - 左下角：视频标题
  - 标题下方：线路选择器（显示"线路1"，点击弹出线路列表）
  - 线路下方：集数选择器（显示当前线路的集数列表）
→ 用户点击线路选择器
  → 弹出线路列表 Dialog/Spinner
  → 选择"线路2"
  → rssRouteIndex = 1
  → rssEpisodes = routes[1].episodes
  → 集数选择器更新为线路2的集数列表
  → 自动播放线路2的第1集
→ 用户点击集数项
  → 切换到该集播放
```

### 场景9：多线路兼容性（单集/多集无线路）

```
场景9a：单URL订阅源（无 ruleContent，R5 抓到1个URL）
→ rssRoutes = null（或单元素 List<RssRoute>）
→ 不显示线路选择器
→ 不显示集数选择器
→ 直接播放（100%兼容现有逻辑）

场景9b：多集无线路订阅源（ruleContent 返回扁平JSON数组或多行URL）
→ parseRssRoutes 返回单元素 List<RssRoute>(name="默认线路", episodes=[...])
→ rssRoutes.size == 1 → 隐藏线路选择器
→ 只显示集数选择器（与现有 UI 一致）
→ 100%兼容现有逻辑

场景9c：多线路多集订阅源（ruleContent 返回嵌套JSON）
→ parseRssRoutes 返回多元素 List<RssRoute>
→ rssRoutes.size > 1 → 显示线路选择器 + 集数选择器
→ 默认选中线路1的第1集
```

### 场景10：ruleContent JS 标准数据格式验证（5站点实证）

```
场景10a：MacCMS 站点 ruleContent 编写（覆盖60%站点）
→ 用户编写 ruleContent JS，使用 MacCMS 模板选择器
→ 返回嵌套 JSON：[{name:"WJ线路",episodes:[...]}, {name:"OK线路",episodes:[...]}]
→ parseRssRoutes 解析成功 → 显示线路选择器

场景10b：80s模板站点 ruleContent 编写（覆盖20%站点）
→ 用户编写 ruleContent JS，按文本节点分割线路
→ 返回嵌套 JSON：[{name:"暴风4K",episodes:[...]}, {name:"非凡高速",episodes:[...]}]
→ parseRssRoutes 解析成功 → 显示线路选择器

场景10c：多级嵌套站点 ruleContent 编写（覆盖20%站点）
→ 用户编写 ruleContent JS，含二次请求逻辑
→ 返回嵌套 JSON：[{name:"线路1",episodes:[]}占位] → 需二次请求填充
→ R5 智能识别标注"需二次请求"，抓取第一个线路的集数作为降级

场景10d：R5 MacCMS 指纹自动识别
→ ruleContent 为空，R5 进入智能模式识别
→ 检测到 player_aaaa JS 变量 → 判定 MacCMS 站点
→ 套用 Tab 式选择器组合 → 自动提取线路+集数
→ 成功率约 60%（MacCMS 生态站点）
```
