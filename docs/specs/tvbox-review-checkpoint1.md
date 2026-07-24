# OpenSpec 检查点1 审查报告

> **审查日期**：2026-07-22
> **审查范围**：tvbox-source-converter + tvbox-optimization 两个 spec 的四文档
> **审查目的**：识别遗漏点/阻塞点/待优化点

---

## 一、tvbox-source-converter 审查（10个问题）

### 阻塞点（2个）

#### B1. Site.api 的映射策略矛盾
- **位置**：design.md L28 vs spec.md R2
- **问题**：design.md 说"type=0→sourceUrl；type=1/3/4→sortUrl 推导；type=2→sourceUrl"，但 spec.md R2 说"Site.key→RssSource.sourceUrl"
- **矛盾**：type=0 时 sourceUrl 是 Site.key 还是 Site.api？
- **背景**：Site.key 是唯一标识（类似ID），Site.api 是接口地址。RssSource.sourceUrl 在 legado 中既是唯一标识也是请求入口
- **建议**：明确 sourceUrl 映射策略——Site.key 作为唯一标识映射到 sourceUrl（保证不冲突），Site.api 按 type 分派到 sortUrl 或 sourceUrl

#### B2. Site bean 定义来源不明确
- **位置**：design.md L249 vs tasks.md 2.2
- **问题**：design.md 说"从 forks-comparison 复制纯字段定义"，tasks.md 说"定义 Site 输入 DTO"
- **矛盾**：是复制 Site.java 到 legado 项目（改包名），还是定义一个新的 Kotlin data class DTO？
- **建议**：定义新的 Kotlin data class `TvBoxSiteDTO`，仅包含字段定义，不引入影视仓依赖

### 遗漏点（5个）

#### M1. 嗅探配置的具体内容缺失
- **位置**：design.md L72-78
- **问题**：type=2 降级模板中 `ruleContent: <嗅探配置>` 是占位符，没有说明嗅探配置的具体字段和值
- **建议**：参考 legado 现有 VideoUrlExtractor 的嗅探配置格式，补充具体字段（如 `ruleContent: @js:\n<video src=...(.*?)/>`）

#### M2. ruleContent 字段在 type=0/1/3/4 中未定义
- **位置**：design.md L52-94
- **问题**：规则模板只定义了 sortUrl/ruleArticles/ruleTitle/ruleLink/ruleImage，但 RssSource 还有 ruleContent（正文规则），视频类源需要 ruleContent 来解析播放地址
- **建议**：为每个 type 补充 ruleContent 生成逻辑

#### M3. searchUrl 字段未定义
- **位置**：design.md L52-94
- **问题**：仅 type=0 模板有 searchUrl，其他类型的源如何支持搜索？
- **建议**：为 type=1/3/4 补充 searchUrl 生成逻辑，或在 Out of Scope 明确声明不支持搜索

#### M4. 缺少 UI 集成方案
- **位置**：spec.md Out of Scope
- **问题**：转化器如何被用户调用？通过命令行、API、还是 UI？如果是独立工具，用户如何访问？
- **建议**：至少说明转化器的调用入口和触发方式（如：订阅源导入页新增"导入TVBox配置"按钮）

#### M5. 缺少真实数据验证计划
- **位置**：tasks.md 8.x
- **问题**：单元测试只验证逻辑正确性，没有计划用真实 TVBox 配置验证转化后的源是否可用
- **建议**：补充真机验证任务（导入真实 TVBox 配置 → 验证列表加载 → 验证搜索 → 验证播放）

### 待优化点（3个）

#### O1. type=0 采集站 API 模板的字段路径可能不准确
- **位置**：design.md L52-60
- **问题**：模板使用 `$.class_list`、`type_name`、`type_id`，但实际 Maccms API 响应通常是 `$.list`、`vod_name`、`vod_id`
- **建议**：核实 Maccms API 真实响应格式，修正字段路径

#### O2. searchable 字段映射逻辑需精确
- **位置**：design.md L31
- **问题**：Site.searchable 有 0/1/2 三种值（0=禁用, 1=启用, 2=用户禁用），当前映射仅说"1→true, 0→false"
- **建议**：补充 2→false 的映射逻辑

#### O3. enableJs 字段在 type=2 降级中设置但未说明原因
- **位置**：design.md L74
- **问题**：设置 `enableJs: true` 但未说明为什么需要启用 JS
- **建议**：补充说明（嗅探可能需要 JS 执行来触发视频加载）

---

## 二、tvbox-optimization 审查（17个问题）

### 阻塞点（4个）

#### B1. ADR 格式不符合 Y-Statement 模板
- **位置**：design.md L301-347
- **问题**：openspec.md L39-51 要求 ADR 使用 Y-Statement 模板（Context/Concern/Decision/Goal/Tradeoff/Status/Superseded-by），但当前使用 Context/Decision/Consequences 格式
- **建议**：改为 Y-Statement 模板

#### B2. VideoPlayerActivity/VideoSettingsPanel 路径可能不准确
- **位置**：design.md 多处引用
- **问题**：引用 `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` 和 `VideoSettingsPanel.kt`，但项目已有多个视频播放器重构 spec，实际路径可能不同
- **建议**：Grep 核实真实路径

#### B3. productFlavors 配置与现有 build.gradle 冲突
- **位置**：design.md L511-527
- **问题**：新增 productFlavors（lite/full/python）可能与现有 buildTypes（debug/release）和 flavorDimensions 冲突，影响打包流程
- **建议**：评估对现有打包流程的影响（包名、签名、资源等），与 package-naming.md 规范协调

#### B4. MPV so 库来源不明确
- **位置**：design.md L503
- **问题**：使用 `com.github.jeffersonlicardona:mpv-android:0.1.4`，但影视仓使用自己编译的 libmpv.so，不是 Maven 依赖。该库可能不维护或不可用
- **建议**：调研 MPV so 库的获取方式（自己编译 / 可用 Maven 仓库 / 其他开源项目）

### 遗漏点（6个）

#### M1. 缺少与现有视频播放器 spec 的协调
- **问题**：项目已有 douyin-style-video-player、video-article-swipe-switch、video-control-visibility-enhancement 等多个 spec，本 spec 的播放器优化方向可能与现有 spec 冲突或重复
- **建议**：明确本 spec 与现有 spec 的关系（重做/扩展/替代）

#### M2. 缺少 minSdk 兼容性详细评估
- **问题**：README.md 说"minSdk 24"，但 legado minSdk 是 23。jupnp/QuickJS/MPV 在 minSdk 23 下的兼容性未评估
- **建议**：逐库评估 minSdk 要求，tasks.md 1.11 需细化

#### M3. 缺少回退方案
- **问题**：如果某个方向实施失败或效果不佳，如何回退？
- **建议**：为每个方向明确回退策略（productFlavors 隔离本身就是一种回退机制）

#### M4. tasks.md 缺少 AOAdapt 日志格式
- **问题**：openspec.md L137-143 要求 tasks.md 包含 AOAdapt 日志，但当前只有任务清单
- **建议**：在 tasks.md 补充 AOAdapt 日志格式说明

#### M5. HttpServer.serve 膨胀风险未对应重构任务
- **问题**：ADR-4 提到"API 路由增多导致 HttpServer.serve 膨胀，需重构为 Controller 分发模式"，但 tasks.md 没有对应的重构任务
- **建议**：在 tasks.md 5.x 补充 HttpServer Controller 分发重构任务

#### M6. Chaquopy 商用授权问题未解决
- **问题**：design.md L180 提到"商用授权问题"但没有解决方案。legado 是开源项目，Chaquopy 商用授权可能不适用
- **建议**：明确决策——放弃 Python 嵌入 / 寻找替代方案 / 联系 Chaquopy 授权

### 待优化点（7个）

#### O1. GSYVideoPlayer 现状描述不准确
- **问题**：README.md 说"GSYVideoPlayer + ExoPlayer"，但项目已有多次视频播放器重构，现状可能与描述不符
- **建议**：核实当前播放器架构，更新现状描述

#### O2. QuickJS 库选择需评估
- **问题**：`com.github.taoweiji.quickjs:quickjs-android` 的维护状态、性能、兼容性需评估
- **建议**：调研替代库（如 quickjs-ng）

#### O3. jupnp 版本需核实
- **问题**：`org.jupnp:jupnp:2.7.1` 是否为最新版本，Android 兼容性如何
- **建议**：核实最新版本和兼容性

#### O4. 缺少 APK 体积影响的量化评估
- **问题**：Drawbacks 说"+18MB"，但没有评估对现有 APK 体积的影响比例
- **建议**：结合当前 APK 体积评估增量比例（当前 debug APK 约 60-70MB？）

#### O5. 缺少实施优先级和依赖关系
- **问题**：spec.md 说"建议顺序：DLNA → 本地服务器 → 播放器 → 网络层"，但没有说明方向间的依赖关系
- **建议**：补充方向间依赖关系图（如：本地服务器播放控制 API 依赖播放器引擎抽象）

#### O6. DLNA DMR 角色增加电量消耗未评估
- **问题**：ADR-3 提到"DMR 角色增加电量消耗"但未评估具体影响和缓解措施
- **建议**：评估电量影响，提供缓解措施（如：仅在充电时启用 DMR）

#### O7. 缺少方向间的依赖关系说明
- **问题**：四个方向并非完全独立，如本地服务器播放控制 API 依赖播放器引擎抽象
- **建议**：在 spec.md 补充方向间依赖关系说明

---

## 三、审查结论

### tvbox-source-converter
- **整体评价**：设计思路清晰，但存在2个阻塞点需解决后才能进入实施
- **关键阻塞**：sourceUrl 映射策略矛盾 + Site bean 定义来源不明
- **建议**：修正阻塞点后可进入实施

### tvbox-optimization
- **整体评价**：方向全面，但存在4个阻塞点需解决后才能进入实施
- **关键阻塞**：ADR格式不符 + 文件路径待核实 + productFlavors冲突 + MPV so库来源不明
- **建议**：修正阻塞点后可进入实施，建议分方向逐步实施（先DLNA/本地服务器，后播放器/网络层）
