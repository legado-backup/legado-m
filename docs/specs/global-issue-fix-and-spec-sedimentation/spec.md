# Spec: 全局问题修复与规范沉淀

## Intent

用户在 2026-07-16 反馈 13 项问题，涵盖 UI Bug、数据库升级、校验逻辑设计偏差、规范沉淀缺失等多个层面。这些问题暴露了 AI 开发过程的三个根因缺陷：

1. **缺乏全局思考**：改动功能时不评估前端入口数量、后端接口影响、数据库改动、覆盖安装兼容性
2. **规范沉淀不足**：同类错误（如数据库升级覆盖安装、真机测试流程复用）反复犯，未沉淀到子规范
3. **功能闭环缺失**：lastHost 字段只在校验时回填，真实使用/调试时不回填，导致字段"有等于没有"

本任务系统性修复这 13 项问题，并建立**错误→沉淀→子规范→主规范引用**的闭环机制，防止反复犯错。

## Scope

### In Scope（本次实现）

**A. 数据库升级覆盖安装修复（P0 阻塞）**
- 问题 #6：migration_95_96 已执行但 view 未重建，覆盖安装触发 IllegalStateException
- 修复：提升 version 到 97，新增 migration_96_97 强制重建 view

**B. 高亮规则崩溃修复（P0 崩溃）**
- 问题 #3：dialog_highlight_rule_edit.xml 使用 MaterialButton 但项目主题是 AppCompat
- 修复：4 个布局的 MaterialButton 改为 AppCompatButton 或 Button

**C. 校验逻辑重构（P1 功能）**
- 问题 #7：当前校验和原来没区别，拿不到真实域名
- 重构：参考调试模式，多线程维度并发，关键元素获取程度加权
- 扩展 lastHost 回填点到 WebBook/Rss 真实使用层 + Debug 调试层

**D. lastHost 字段设计修正（P1 功能）**
- 问题 #13：lastHost 应在真实使用/调试/校验三层回填，域名分组按"真实地址+源类型"合并
- 修正：BookSourceActivity 分组逻辑改为复合键 (host, type)
- 补齐：RssSourceActivity 域名分组入口

**E. UI Bug 修复（P1）**
- 问题 #1：订阅源内置播放器详情页右上角刷新+三个点菜单丢失
- 问题 #2：订阅源内置播放器返回按钮不生效
- 问题 #4：订阅源编辑页单源解析线程数配置按钮缺失
- 问题 #5：内置视频浏览器下方功能区弹框样式不搭

**F. 工程规范沉淀机制（P2 规范）**
- 问题 #9：真机测试流程复用未沉淀
- 问题 #10：数据库升级覆盖安装问题未沉淀到子规范
- 问题 #11：反复犯同样错误需要沉淀机制
- 问题 #12：复杂需求要反复验证可行性
- 问题 #14：全局思考检查清单缺失

### Out of Scope（本次不实现）

- 订阅源校验的完整重写（仅在现有基础上扩展回填点和加权逻辑）
- 视频播放器手势交互优化（不在本次范围）
- 网络层 Cronet 优化（已有独立 spec）
- R5 嗅探逻辑重写（视频URL解析失败是站点适配问题，非本次范围）

## Approach

### Selected Approach

采用**"先规范后修复"分层架构**：

1. **规范层先行**：先建立"全局思考检查清单"和"错误沉淀机制"子规范，作为后续所有修复的约束
2. **数据库层优先**：先修复覆盖安装问题（version 97），让用户能装上后续修复
3. **崩溃修复次之**：高亮规则 MaterialButton 主题兼容
4. **功能闭环修复**：lastHost 三层回填 + 域名分组复合键
5. **校验逻辑重构**：参考调试模式的多线程维度并发
6. **UI Bug 修复**：播放器菜单、返回按钮、单源线程数、弹框样式
7. **规范沉淀收尾**：将本次所有错误沉淀到子规范，主规范引用

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 只修复 Bug 不建规范 | 治标不治本，下次还会犯同类错误（用户批评#11） |
| 数据库用 fallbackToDestructiveMigration | 会清空用户全部书源数据，不可接受 |
| 数据库让用户卸载重装 | 规避问题不是解决问题（用户批评#6） |
| 校验逻辑完全重写 | 风险大，应在现有基础上扩展，复用现有 Debug 模型 |
| lastHost 改为每次请求都写 DB | 性能问题，应内存缓存+批量持久化 |
| MaterialButton 改主题为 Material3 | 影响全局，风险大，改组件类型更安全 |
| 域名分组只按 host 不按 type | 不符合用户要求（#13：一个域名可有多个类型源） |

### Drawbacks

1. **version 升到 97 需再次 migration**：但这正是正确做法，Room 要求 version 递增
2. **lastHost 三层回增性能开销**：用"变化才写 DB"策略缓解
3. **校验逻辑重构复杂度高**：需复用 Debug 模型，改动面大
4. **规范沉淀是长期投入**：短期不直接产出功能，但防止反复犯错

### Prior Art

- 原版 legado 的 `BookSourceDebugActivity` / `Debug` 模型：分步骤收集结果，可作为校验逻辑重构参考
- `CheckRssSourceService.dedupSources`：已按 `realDomain + type` 复合分组，可作为域名分组参考

## Requirements

### 问题根因索引（每个问题的"具体根因+修复方案+如何避免"三维度）

> 所有问题的深度分析已沉淀到 [issues-found.md](./issues-found.md)，每个 Issue 包含：
> - **具体根因**：精确到文件+行号的代码位置
> - **修复方案**：具体的代码改法
> - **如何避免**：沉淀到哪个子规范的哪条规则

| Issue | 问题 | 具体根因（文件+行号） | 如何避免（沉淀到） |
|-------|------|---------------------|------------------|
| Issue-1 | 数据库升级覆盖安装失败 | migration_95_96 未 DROP+CREATE view | database-migration-safety.md |
| Issue-2 | 高亮规则点+号崩溃（4次FATAL，日志确认） | MaterialButton 需要 Material 主题（dialog_highlight_rule_edit 第89行） | spec-sedimentation-mechanism.md |
| Issue-3 | 播放器菜单丢失 | video_play.xml 缺 menu_rss_refresh/menu_browser_open | global-thinking-checklist.md |
| Issue-4 | 返回按钮不生效 | 双 TitleBar 并存+BaseActivity final 拦截 | spec-sedimentation-mechanism.md |
| Issue-5 | 单源线程数配置缺失 | RssSource 有字段但 UI 未对接 | global-thinking-checklist.md |
| Issue-6 | 弹框样式不搭 | VideoSettingsPanel 硬编码9处颜色 | global-thinking-checklist.md |
| Issue-7 | 校验逻辑没区别 | doCheckSource 串行+权重二元判断 | spec-sedimentation-mechanism.md |
| Issue-8 | lastHost 设计偏差 | 回填点仅3处+分组只按 host | spec-sedimentation-mechanism.md |
| Issue-9 | 真机测试流程未沉淀 | 脚本已有但未沉淀为规范 | real-device-test-reuse.md |
| Issue-10 | 数据库问题未沉淀 | 无子规范+AGENTS.md 未引用 | database-migration-safety.md |
| Issue-11 | 反复犯错缺沉淀机制 | project_memory 未结构化 | spec-sedimentation-mechanism.md |
| Issue-12 | 缺全局思考检查清单 | OpenSpec 步骤1无强制门禁 | global-thinking-checklist.md |
| Issue-13 | 日志文件分析（用户反馈 #8） | 4次FATAL全为MaterialButton崩溃+172次网络异常已被降级处理 | 已分析完成，无新问题 |
| Issue-14 | 复杂需求反复验证可行性未沉淀 | OpenSpec 无3次验证强制环节 | spec-sedimentation-mechanism.md |

### REQ-1: 数据库升级覆盖安装（P0）
- version 提升到 97
- migration_96_97 必须执行 DROP VIEW + CREATE VIEW 重建 book_sources_part
- 覆盖安装（从旧 96 到新 97）必须成功，不丢数据

### REQ-2: 高亮规则崩溃修复（P0）
- dialog_highlight_rule_edit.xml 等 4 个布局的 MaterialButton 改为 AppCompatButton
- 点击+号不再崩溃，能正常打开编辑对话框

### REQ-3: 校验逻辑重构（P1）
- 参考 Debug 模型，校验过程中分步骤收集关键元素获取结果
- 多线程维度并发（受 concurrentRate 约束）
- 权重计算基于关键元素获取程度，而非分组名二元判断
- lastHost 在搜索/发现/详情/正文维度请求时都回填

### REQ-4: lastHost 三层回填（P1）
- 真实使用层：WebBook.searchBook/getBookInfo/getChapterList/getContent 回填
- 调试层：BookSourceDebugActivity/Debug 模型回填
- 校验层：CheckSourceService/CheckRssSourceService 回填（已有）
- 回填策略：变化才写 DB

### REQ-5: 域名分组复合键（P1）
- BookSourceActivity 分组键改为 (getSourceHost(lastHost ?: sourceUrl), bookSourceType)
- RssSourceActivity 补齐域名分组入口
- 分组键：(getSourceHost(lastHost ?: sourceUrl), type)

### REQ-6: 订阅源播放器菜单修复（P1）
- 详情页右上角恢复刷新按钮+三个点菜单
- "浏览器打开"功能恢复

### REQ-7: 订阅源播放器返回按钮修复（P1）
- 顶部左侧返回按钮可正常返回

### REQ-8: 订阅源编辑页单源线程数配置（P1）
- 在 RssSourceEditActivity 添加 parseConcurrency 配置入口
- 配置项保存到 RssSource.parseConcurrency 字段

### REQ-9: 视频浏览器弹框样式修复（P2）
- 弹框样式适配 AppTheme.Light

### REQ-10: 工程规范沉淀机制（P2）
- 新建子规范文件：`docs/project-rules/spec-sedimentation-mechanism.md`
- 内容：错误→沉淀→子规范→主规范引用闭环
- 主规范 AGENTS.md 引用

### REQ-11: 全局思考检查清单（P2）
- 新建子规范文件：`docs/project-rules/global-thinking-checklist.md`
- 内容：前端入口盘点、后端接口影响、数据库改动评估、覆盖安装兼容性
- 主规范 AGENTS.md 引用

## Scenarios

### Scenario 1: 数据库覆盖安装（用户场景）
**Given** 用户已安装 version=96 的有 bug 版本（view 未重建）
**When** 用户覆盖安装 version=97 的新包
**Then** migration_96_97 执行 DROP+CREATE VIEW，schema 校验通过，App 正常启动，书源数据保留

### Scenario 2: 高亮规则点+号（崩溃场景）
**Given** 用户打开书架→小说→高亮规则管理
**When** 点击右上角+号
**Then** 正常打开编辑对话框，不崩溃

### Scenario 3: 校验获取真实域名（功能场景）
**Given** 一个书源 sourceUrl 含 jslib/注释/#规避
**When** 用户执行校验，勾选"域名"CheckBox，选择"解析规则真实请求"
**Then** AnalyzeUrl 解析真实地址，回填 lastHost，域名分组按真实域名+类型合并显示

### Scenario 4: 真实使用时回填 lastHost（闭环场景）
**Given** 用户用书源搜索书籍
**When** WebBook.searchBookAwait 内部 AnalyzeUrl 解析出真实域名
**Then** lastHost 异步回填到 DB，下次域名分组用真实域名而非 sourceUrl 截取

### Scenario 5: 域名分组按类型合并（分组场景）
**Given** 站点A 有文本源(type=0)和音频源(type=1)
**When** 用户开启域名分组
**Then** 显示"站点A [文本]"和"站点A [音频]"两个分组，而非混在一起

### Scenario 6: 订阅源编辑页配置线程数（配置场景）
**Given** 用户打开订阅源编辑页
**When** 找到解析线程数配置项
**Then** 可设置 1-32 范围的并发数，保存到 parseConcurrency 字段

### Scenario 7: 规范沉淀闭环（工程场景）
**Given** 本次修复数据库升级问题
**When** 修复完成后
**Then** 在 spec-sedimentation-mechanism.md 记录"数据库升级必须 DROP+CREATE VIEW"规则，AGENTS.md 引用，下次不再犯
