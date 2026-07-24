# OpenSpec 四角度深度审查报告

> **审查日期**：2026-07-22
> **审查范围**：tvbox-source-converter + tvbox-optimization 两个 spec 的四文档
> **审查角度**：产品角度 / 用户角度 / 技术架构角度 / 测试角度
> **源码核实**：RssSource.kt 字段定义、build.gradle productFlavors 现状、文件路径均已核实

---

## 一、tvbox-source-converter 四角度审查

### 1. 产品角度

#### P1.1 功能定位清晰度
- **评价**：单向转化器定位清晰，将影视仓 Site 转化为 legado RssSource
- **问题**：转化后的源质量无法保证（降级策略导致部分源不可用），缺少转化成功率指标
- **建议**：在 ConvertResult 中增加成功率统计（成功数/总数），让用户评估转化效果

#### P1.2 与现有功能的关系
- **问题**：与现有订阅源导入功能的关系未明确——是替代还是补充？
- **问题**：转化后的源如何管理？是否复用现有订阅源管理界面？
- **建议**：明确与现有导入流程的集成点（如：订阅源导入页新增"导入TVBox配置"入口）

#### P1.3 产品价值评估
- **价值**：扩大 legado 的源生态，复用影视仓积累的播放源
- **风险**：降级后的源质量差，可能影响用户体验（用户导入后发现大量源不可用）
- **建议**：提供转化预览功能，用户导入前可查看哪些源可用/降级/失败

#### P1.4 优先级合理性
- P0：字段映射 + type=2 降级 + 冲突处理 ✅
- P1：type=0 模板 + 降级标注 ✅
- **缺失**：转化成功率指标、用户反馈机制、转化预览功能

### 2. 用户角度

#### U1.1 用户使用流程
- **问题**：design.md 说"离线纯函数"，但用户如何调用转化器？缺少 UI 入口设计
- **用户操作流程**（推测）：获取 TVBox JSON → 喂给转化器 → 导入 legado → 校验修正
- **缺失**：第一步"获取 TVBox JSON"的来源未说明，用户可能不知道从哪获取
- **建议**：提供常用 TVBox 配置源链接或导入入口

#### U1.2 用户体验
- **问题**：降级源需要用户手动补规则，学习成本高
- **问题**：没有转化预览，用户导入前不知道哪些源可用
- **建议**：提供转化报告（成功率/降级列表/需校验列表），并在导入后高亮显示降级源

#### U1.3 用户痛点
- **痛点1**：TVBox 配置获取困难（需用户自行寻找）
- **痛点2**：降级源不可用时的挫败感
- **痛点3**：手动补规则需要理解 legado 规则语法
- **建议**：提供"降级源修复指南"文档，降低用户学习成本

#### U1.4 学习成本
- 需要理解 Site.type 语义（0-4 五种类型）
- 需要理解降级标注格式（`// 降级说明: xxx | 已知上限: xxx | 升级路径: xxx`）
- 需要手动补规则的能力（CSS/XPath/JSONPath/正则/JS）
- **建议**：在 sourceComment 中提供修复提示链接或帮助文档入口

### 3. 技术架构角度

#### T1.1 架构设计合理性
- **优点**：独立 object，纯函数，可测试，不依赖 Android 运行时
- **阻塞点**：sourceUrl 映射策略矛盾（Site.key vs Site.api）
  - Site.key 是唯一标识（可能是 UUID 或短字符串），不是 URL
  - RssSource.sourceUrl 在 legado 中既是 PrimaryKey 也是请求入口
  - **建议**：sourceUrl = Site.api（保证可访问性），冲突时追加 Site.key 后缀
- **阻塞点**：Site bean 定义来源不明
  - **建议**：定义新的 Kotlin data class `TvBoxSiteDTO`，仅包含字段定义

#### T1.2 与现有架构的兼容性
- **已核实**：RssSource.kt 确认有以下字段，但 design.md 遗漏了生成逻辑：
  - `ruleContent`（正文规则）：视频类源需要此字段解析播放地址，design.md 仅 type=2 有占位符
  - `searchUrl`（搜索URL）：design.md 仅 type=0 有，其他类型缺失
  - `singleUrl`（是否单url源）：type=2 降级用到，但未说明其他 type 是否设置
  - `enableJs`/`loadWithBaseUrl`：type=2 设置了，但未说明其他 type 的默认值
  - `articleStyle`（列表样式）：视频类应为 2（视频样式），但 design.md 未设置
  - `customOrder`（自定义排序）：批量导入时应设置，但 design.md 未提及
- **建议**：补充上述字段的生成逻辑

#### T1.3 扩展性
- **优点**：规则模板可扩展（TvBoxRuleTemplates）
- **问题**：新增 Site.type 时需修改 TvBoxRuleDispatcher 分派逻辑
- **建议**：考虑策略模式替代 when 分派（每个 type 一个策略类）

#### T1.4 依赖关系
- 依赖 GSON（legado 已有）✅
- 依赖 RssSource（legado 已有）✅
- 不引入新外部依赖 ✅
- **问题**：Site bean 定义需从 forks-comparison 复制，但 forks-comparison 不在 legado 项目内
- **建议**：定义 TvBoxSiteDTO，不依赖 forks-comparison

### 4. 测试角度

#### T1.1 可测试性
- **优点**：纯函数，可脱离 Android 环境单测 ✅
- **问题**：缺少真实数据验证计划

#### T1.2 测试覆盖
- tasks.md 7.x 有10个单元测试 ✅
- **缺失**：集成测试（转化后源是否可被 legado RssSource 反序列化）
- **缺失**：真机验证计划（转化后源在 legado 中是否可加载列表/搜索/播放）

#### T1.3 验证计划
- **缺失**：真实 TVBox 配置验证（用真实数据测试转化效果）
- **缺失**：转化后源在 legado 中的可用性验证（列表加载/搜索/播放）

#### T1.4 边界条件
- 空 sites 数组 ✅
- 字段缺失 ✅
- sourceUrl 冲突 ✅
- **缺失**：超大配置文件（1000+ sites）性能测试
- **缺失**：特殊字符处理（源名称含表情/HTML标签/引号）
- **缺失**：Site.header 为 null 时的处理
- **缺失**：Site.categories 为空列表时的 sortUrl 生成

---

## 二、tvbox-optimization 四角度审查

### 1. 产品角度

#### P2.1 功能定位清晰度
- **评价**：四方向优化（播放器/网络层/DLNA/本地服务器），方向清晰
- **问题**：legado 核心定位是阅读器，过度视频化会偏离核心定位
- **问题**：四个方向同时做，产品聚焦度不足
- **建议**：明确本 spec 与现有视频播放器 spec（douyin-style-video-player 等）的关系

#### P2.2 与现有功能的关系
- **问题**：与现有视频播放器 spec 的协调缺失
  - 项目已有 douyin-style-video-player、video-article-swipe-switch、video-control-visibility-enhancement 等
  - 本 spec 的播放器优化方向可能与现有 spec 冲突或重复
- **建议**：明确本 spec 是扩展现有 spec 还是替代

#### P2.3 产品价值评估
- **DLNA 投屏**：高价值（用户需求明确，当前完全缺失）
- **本地服务器扩展**：中价值（开发者用户需求，普通用户无感）
- **双引擎播放**：中价值（少数硬解失败场景，但影响大）
- **QuickJS**：低价值（性能优化，用户无感，Rhino 够用）
- **Python 嵌入**：极低价值（实验性，维护成本高，商用授权问题）

#### P2.4 优先级合理性
- spec.md 说"DLNA → 本地服务器 → 播放器 → 网络层"
- **问题**：缺少方向间依赖关系分析
  - 本地服务器播放控制 API 依赖播放器引擎抽象（PlayerEngine 接口）
  - DLNA 投屏控制依赖播放器状态查询
- **建议**：补充方向间依赖关系图，调整实施顺序

### 2. 用户角度

#### U2.1 用户使用流程
- **DLNA**：视频界面点击投屏按钮 → 选择设备 → 投屏控制 ✅
- **双引擎**：自动切换 + 设置面板手动切换 ✅
- **QuickJS**：设置面板选择引擎（全局/单源）✅
- **本地服务器**：浏览器访问 `http://手机IP:1122` ✅

#### U2.2 用户体验
- **优点**：配置驱动，默认关闭，用户按需开启 ✅
- **问题**：APK 体积增加 18MB，用户需下载更大包
- **问题**：productFlavors 导致用户需选择版本（lite/full/python），增加选择困难
- **建议**：提供默认推荐版本（lite），在设置中引导用户按需升级

#### U2.3 用户痛点
- **投屏需求**：当前完全无法投屏 → DLNA 解决 ✅
- **硬解失败**：当前无法播放 → 双引擎解决 ✅
- **规则慢**：当前 Rhino 性能差 → QuickJS 解决（但用户无感）
- **Python 规则**：无实际需求 → 建议放弃或延后

#### U2.4 学习成本
- **双引擎**：低（自动切换，用户无需理解）✅
- **DLNA**：低（点击投屏，类似常用 App）✅
- **QuickJS**：中（需理解引擎差异，但默认 Rhino 不影响）
- **Python**：高（需编写 Python 规则，受众极小）

### 3. 技术架构角度

#### T2.1 架构设计合理性
- **优点**：接口抽象（PlayerEngine/ScriptEngine/Device）✅
- **阻塞点**：ADR 格式不符 Y-Statement 模板（要求 Context/Concern/Decision/Goal/Tradeoff/Status）
- **阻塞点**：productFlavors 与现有 build.gradle 冲突
  - **已核实**：build.gradle 已有 `flavorDimensions = ['mode']` + `productFlavors { app { dimension "mode" } }`
  - design.md 新增 `flavorDimensions "engine"` + `lite/full/python` 会导致多维 flavor
  - 影响打包流程（包名、签名、资源、APK 命名）
  - **建议**：改为在现有 `app` flavor 内通过依赖配置区分，或新增 `engine` 维度但需评估打包影响
- **阻塞点**：MPV so 库来源不明
  - design.md 使用 `com.github.jeffersonlicardona:mpv-android:0.1.4`
  - 影视仓使用自己编译的 libmpv.so，不是 Maven 依赖
  - **建议**：调研 MPV so 库获取方式（自己编译 / JitPack / 其他开源项目）

#### T2.2 与现有架构的兼容性
- **已核实**：文件路径均正确 ✅
  - VideoPlayerActivity.kt: `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` ✅
  - VideoSettingsPanel.kt: `app/src/main/java/io/legado/app/ui/video/VideoSettingsPanel.kt` ✅
  - ExoPlayerHelper.kt: `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` ✅
  - VideoUrlExtractor.kt: `app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt` ✅
- **问题**：GSYVideoPlayer 现状描述不准确
  - README.md 说"GSYVideoPlayer + ExoPlayer"
  - 但项目已有多次视频播放器重构，现有播放器架构可能是 GSYVideoBase + ExoPlayer
  - **建议**：核实当前播放器架构，更新现状描述

#### T2.3 扩展性
- **优点**：接口抽象便于扩展（PlayerEngine/ScriptEngine）✅
- **问题**：双引擎增加维护复杂度（两套引擎的 Bug 排查）
- **问题**：QuickJS 与 Rhino 的 API 差异需适配层

#### T2.4 依赖关系
- **方向间依赖**：
  - 本地服务器播放控制 API → 依赖播放器引擎抽象（PlayerEngine 接口）
  - DLNA 投屏控制 → 依赖播放器状态查询
  - QuickJS → 独立（不依赖其他方向）
- **缺失**：方向间依赖关系图
- **建议**：补充依赖关系图，调整实施顺序（PlayerEngine 接口应先于本地服务器/DLNA）

### 4. 测试角度

#### T2.1 可测试性
- **单元测试**：PlayerEngineFactory/ScriptEngine/DlnaController/PlaybackController ✅
- **问题**：MPV/JNI/QuickJS 难以单元测试（需真机验证）

#### T2.2 测试覆盖
- tasks.md 6.x 有构建验证 + 端到端测试 + 性能兼容性 ✅
- **缺失**：AOAdapt 日志格式（openspec.md 要求）
- **缺失**：HttpServer.serve 膨胀风险未对应重构任务

#### T2.3 验证计划
- **真机测试**：5种编码 + 3种电视品牌 ✅
- **问题**：minSdk 23 兼容性未评估
  - README.md 说"minSdk 24"，但 legado minSdk 是 23
  - jupnp/QuickJS/MPV 在 minSdk 23 下的兼容性需逐库评估
- **缺失**：回退方案（如果某方向实施失败如何回退）

#### T2.4 边界条件
- 硬解失败切换 ✅
- QuickJS 不兼容回退 ✅
- **缺失**：DLNA 设备不可达时的处理
- **缺失**：并发投屏控制（多个设备同时投屏）
- **缺失**：网络中断恢复（投屏中 WiFi 断开）
- **缺失**：Chaquopy 商用授权问题未解决

---

## 三、修订建议汇总

### tvbox-source-converter 修订建议（优先级排序）

| # | 修订项 | 类别 | 优先级 |
|---|--------|------|--------|
| 1 | sourceUrl 映射策略：Site.api→sourceUrl（保证可访问性），冲突时追加 Site.key 后缀 | 阻塞 | P0 |
| 2 | Site bean 定义：新建 Kotlin data class TvBoxSiteDTO，不引入影视仓依赖 | 阻塞 | P0 |
| 3 | 补充 ruleContent 生成逻辑（所有 type） | 遗漏 | P0 |
| 4 | 补充 searchUrl 生成逻辑（type=1/3/4）或声明不支持 | 遗漏 | P1 |
| 5 | 补充嗅探配置具体内容（type=2） | 遗漏 | P1 |
| 6 | 补充 articleStyle=2（视频样式）设置 | 遗漏 | P1 |
| 7 | 补充 UI 集成方案（调用入口） | 遗漏 | P1 |
| 8 | 补充真机验证计划 | 遗漏 | P2 |
| 9 | 修正 Maccms API 字段路径（$.list/vod_name/vod_id） | 优化 | P2 |
| 10 | 补充 searchable 0/1/2 三值映射 | 优化 | P2 |
| 11 | 补充 enableJs 说明 | 优化 | P3 |
| 12 | 增加转化成功率指标 | 产品 | P2 |
| 13 | 增加转化预览功能 | 产品 | P3 |
| 14 | 增加特殊字符/超大配置边界测试 | 测试 | P2 |

### tvbox-optimization 修订建议（优先级排序）

| # | 修订项 | 类别 | 优先级 |
|---|--------|------|--------|
| 1 | ADR 改为 Y-Statement 模板 | 阻塞 | P0 |
| 2 | productFlavors 方案：评估多维 flavor 影响，或改为依赖配置区分 | 阻塞 | P0 |
| 3 | MPV so 库来源调研 | 阻塞 | P0 |
| 4 | 核实并更新 GSYVideoPlayer 现状描述 | 阻塞 | P1 |
| 5 | 明确与现有视频播放器 spec 的关系 | 遗漏 | P0 |
| 6 | 补充方向间依赖关系图 | 遗漏 | P0 |
| 7 | 补充 minSdk 23 兼容性评估 | 遗漏 | P1 |
| 8 | 补充回退方案 | 遗漏 | P1 |
| 9 | 补充 AOAdapt 日志格式 | 遗漏 | P1 |
| 10 | 补充 HttpServer Controller 分发重构任务 | 遗漏 | P1 |
| 11 | 解决 Chaquopy 商用授权问题（建议放弃 Python 嵌入） | 遗漏 | P1 |
| 12 | 评估 APK 体积增量比例 | 优化 | P2 |
| 13 | 评估 QuickJS/jupnp 库版本 | 优化 | P2 |
| 14 | 评估 DLNA DMR 电量影响 | 优化 | P3 |
| 15 | 补充 DLNA 设备不可达/网络中断边界处理 | 测试 | P2 |
| 16 | 建议放弃 Python 嵌入方向（价值极低，成本极高） | 产品 | P1 |
| 17 | 建议先实施 DLNA + 本地服务器，延后播放器 + 网络层 | 产品 | P1 |

---

## 四、总结

### tvbox-source-converter
- **整体评价**：设计思路清晰，但需修正2个阻塞点 + 补充5个遗漏点 + 3个优化点
- **关键风险**：转化后源质量无法保证（降级策略），用户可能体验不佳
- **修订工作量**：中等（主要是补充字段生成逻辑 + UI 集成方案）

### tvbox-optimization
- **整体评价**：方向全面，但需修正4个阻塞点 + 补充6个遗漏点 + 7个优化点
- **关键风险**：productFlavors 冲突 + MPV so 库来源 + 过度视频化偏离阅读器定位
- **修订工作量**：较大（ADR 重写 + productFlavors 方案重设计 + 依赖关系梳理）
- **建议**：放弃 Python 嵌入方向，先实施 DLNA + 本地服务器，延后播放器 + 网络层
