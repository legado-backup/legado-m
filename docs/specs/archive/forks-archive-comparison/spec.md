# Spec — 阅读 Archive 私仓深度对比与借鉴分析

---

## Intent（意图）

用户获得阅读 Archive 作者开放的私仓权限后，要求：
1. 下载私仓到 `temp/forks-comparison/legado-archive/`
2. 文档体系补全（生成 OpenSpec 四文档）
3. 深度分析私仓与当前项目（阅读 Sigma fork）的差异
4. 提炼可借鉴点，输出借鉴决策

**核心问题**：阅读 Archive 私仓（armv8-release 分支）相对于本项目有哪些值得学习借鉴的差异？哪些应该借鉴、哪些不应该、为什么？

---

## Scope（范围）

### In Scope（本次任务做）
- 私仓克隆与结构扫描
- 七大维度模块对比（主题 / EPUB / AI / 发现页 / 订阅源 / 视频 / 构建依赖）
- 差异识别 + 价值评估 + 借鉴决策表
- 输出分析报告与决策表文档
- 更新 `docs/INDEX.md` 和 `forks-reference.md`

### Out of Scope（本次任务不做）
- **不修改本项目任何源码**（借鉴应用是后续独立 OpenSpec 任务）
- 不深度对比 armv8 native 优化（源码不可见，仅在 CI 工作流层）
- 不对比 git 历史变更轨迹（浅克隆限制）
- 不评估"借鉴后如何实现"的具体方案（决策表只给方向，实现是后续任务）
- 不对比非主线模块（如 SourceMRssHelp 等小特性，仅在差异点超 5 个时才纳入）

---

## Approach（方案）

### Selected Approach：五阶段对比流程 + 子代理并行编排

依据 `docs/project-rules/forks-reference.md` 五阶段流程：
1. **Phase 1 准备**：浅克隆 + 关键文件初扫（已完成）
2. **Phase 2 分类对比**：按 7 大模块维度拆分，子代理并行分析（单代理 ≤12 文件）
3. **Phase 3 差异识别**：逐项列出"A 有 B 无 / A 优于 B / A 劣于 B / 仅实现差异"
4. **Phase 4 价值评估**：每项差异附 1-5 分收益 + 1-5 分风险 + 借鉴成本（低/中/高）
5. **Phase 5 借鉴决策**：输出三态决策表（借鉴 / 不借鉴 / 待评估），附理由与后续任务链接

**理由**：
- forks-reference 方法论已沉淀，复用降低风险
- 子代理并行规避主代理上下文上限，符合 `sub-agent-quality-management.md` 低风险强制子代理策略
- 七大维度覆盖用户关注的"差异 + 借鉴"全链路
- 三态决策表避免"全借鉴或不借鉴"的极端，给后续任务留弹性

### Alternatives Considered（考虑过的替代方案）

| # | 替代方案 | 否决理由 |
|---|---------|---------|
| B | 只读 README/CHANGELOG，不深度对比源码 | 信息密度不足；README 只列高层特性，无法判断实现质量。forks-reference 已警示"以 README 为准会漏掉 WebView 优化等关键差异" |
| C | `git diff` 两边源码做整体对比 | 项目演进已大幅分叉，diff 噪声极大；不同包名/类名导致 diff 失效；无法按模块维度归类 |
| D | AI 长上下文一次性吃下全部源码做分析 | 主代理上下文上限风险高；难以保证 7 大维度全覆盖；不符合 `sub-agent-quality-management.md` 子代理编排规范 |
| E | 只对比 build.gradle + libs.versions.toml 看依赖差异 | 依赖差异只是表象，无法看出"主题重做"等功能层差异；用户明确要"深度分析" |
| F | 深克隆 + git log 对比每个提交 | 浅克隆已满足"当前状态差异"分析需求；深克隆耗时长且历史提交对"借鉴决策"价值边际递减；forks-reference 明确警示"GitHub git trees API 有缓存错误，以 clone 实测为准" |

### Drawbacks（已知缺点）

| # | 缺点 | 接受理由 |
|---|------|---------|
| D1 | 浅克隆无法看历史变更轨迹，无法判断"某特性何时引入、为何引入" | 当前状态差异已足够支撑借鉴决策；历史轨迹对决策影响小 |
| D2 | armv8 native 优化在 CI 层（`private-armv8-release.yml`），源码层不可见 | CI 工作流文件本身已可分析（增量缓存/单架构构建/签名验证），native 优化细节对 Java/Kotlin 层借鉴价值低 |
| D3 | 7 大模块对比需要约 7 个子代理，编排成本高 | 子代理独立预算不额外收费；并行执行总时长远低于串行 |
| D4 | 三态决策表（借鉴/不借鉴/待评估）可能产生过多"待评估"项 | "待评估"是合理中间态，避免强行二选一导致误判；后续任务可逐项消化 |
| D5 | 私仓 tag `3.26.07071245`（7-07）比本项目 `3.26.071720`（7-17）早 10 天，可能漏掉 Archive 最新进展 | 10 天差异在长周期演进中可忽略；用户已明确"作者给开权限就现在做" |

### Prior Art（参考工作）

- `docs/project-rules/forks-reference.md`：27+ 延伸版本清单 + 五阶段对比流程
- `docs/specs/sigma-sync-202607/`：本项目与阅读 Sigma 同步对比的实施案例
- `docs/project-rules/sub-agent-quality-management.md`：子代理编排规范
- `docs/project-rules/complex-task-pipeline.md`：五阶段流水线（50+ 文件时启用）

---

## Requirements（需求）

### R1 文件结构对比
- **R1.1** 对比顶层目录（根 + app + modules + docs + .github）
- **R1.2** 对比 `app/src/main/java/io/legado/app/` 子包结构（api/base/constant/data/help/lib/model/service/ui/utils/web）
- **R1.3** 对比 `app/src/main/res/`（drawable/layout/menu/values/anim/color/xml）
- **R1.4** 对比 `app/src/main/assets/`（defaultData/web/help/bg/font/textmate）
- **R1.5** 输出文件结构差异表（A 独有 / B 独有 / 共有但内容差异）

### R2 关键模块对比（7 大维度）
- **R2.1** 主题管理：Theme.kt / ThemeConfig / 主题 Activity / 主题导入导出 / 云端同步
- **R2.2** EPUB 阅读：epub 解析 / 注解 / 分页缓存 / 复杂样式 / 大文件导入
- **R2.3** AI 助手：工具调用 / 书源搜索 / 章节读取 / 阅读记录查询 / 联网搜索
- **R2.4** 发现页与订阅源：统一源选择 / 订阅内容搜索 / 纯 URL 订阅源 / 合并入口
- **R2.5** 视频播放：直达播放页 / 详情目录展示 / 漫画阅读控件
- **R2.6** 构建配置：build.gradle / flavors / signingConfigs / CI workflows / abiFilters
- **R2.7** 依赖库：libs.versions.toml / 新增依赖 / 锁定依赖差异（jsoup/rhino/hutool）

### R3 差异识别与价值评估
- **R3.1** 每个模块输出差异清单（条目数 ≥ 3 才纳入，避免噪声）
- **R3.2** 每项差异附：差异类型（独有/优于/劣于/实现差异）+ 收益分（1-5）+ 风险分（1-5）+ 借鉴成本（低/中/高）
- **R3.3** 收益/风险评分必须有源码依据，禁止凭直觉打分

### R4 借鉴决策表
- **R4.1** 三态决策：借鉴 / 不借鉴 / 待评估
- **R4.2** 每项决策附理由（≤2 句话）
- **R4.3** "借鉴"项附后续任务建议（独立 OpenSpec spec 名）
- **R4.4** "不借鉴"项附否决理由（如与本项目架构冲突 / 已有更好方案 / 锁定依赖不允许）

### R5 文档产出
- **R5.1** `analysis-report.md`：差异分析报告，含 mermaid 架构图与对比表
- **R5.2** `borrow-decisions.md`：借鉴决策表
- **R5.3** 更新 `docs/INDEX.md` 状态
- **R5.4** 更新 `docs/project-rules/forks-reference.md` 补充私仓地址与结论索引

---

## Scenarios（场景）

### S1：发现 Compose 引入
- **触发**：build.gradle 初扫发现 `androidx.compose.bom` / `compose.ui` / `compose.material3`
- **分析**：本项目为纯 View 体系，Archive 已部分引入 Compose
- **决策路径**：收益（现代化 UI） vs 风险（双 UI 系统维护成本） → 待评估（需看 Compose 用在哪些页面）

### S2：发现 AI 助手
- **触发**：README 提及"工具调用、书源搜索、章节读取、阅读记录查询、联网搜索"
- **分析**：本项目无 AI 助手模块，Archive 是核心增量
- **决策路径**：收益（差异化能力） vs 风险（依赖外部 AI 服务 + 隐私合规） → 借鉴（独立 spec 落地）

### S3：发现主题管理重做
- **触发**：README 提及"重做主题管理，支持日间/夜间/背景图、界面颜色、导入导出、云端同步"
- **分析**：本项目有 `builtin-themes` spec（8 个内置主题），但未做"主题管理重做"
- **决策路径**：收益（与 builtin-themes 互补） vs 风险（与现有主题系统冲突） → 借鉴（独立 spec 落地，需先评估冲突）

### S4：发现 armv8 单架构构建
- **触发**：`private-armv8-release.yml` 工作流 `-Pabi=arm64-v8a`
- **分析**：本项目 build.gradle 已支持 `abi` 参数，但无对应 CI 工作流
- **决策路径**：收益（APK 体积减小 + armv8 设备性能优化） vs 风险（丢失 x86/mips 设备支持） → 借鉴（CI 工作流模板可复用）

### S5：发现 libarchive 替代 ZipFile
- **触发**：build.gradle 引入 `libs.libarchive`
- **分析**：本项目 EPUB/压缩解压可能用 ZipFile 或其他库
- **决策路径**：收益（支持更多格式 7z/rar/tar.gz） vs 风险（新增 native 依赖体积） → 待评估（需看实际使用范围）

### S6：发现 sora-editor 代码编辑器
- **触发**：build.gradle 引入 `soraEditor.bom/core/language.textmate`
- **分析**：本项目书源编辑可能用 CodeView 或简单 EditText
- **决策路径**：收益（语法高亮 + 自动补全 + 代码折叠） vs 风险（依赖体积 + 学习成本） → 借鉴（书源编辑体验大幅提升）

### S7：发现 liquidglass / miuix UI 库
- **触发**：build.gradle 引入 `liquidglass` + `miuix.android`
- **分析**：本项目无这两个 UI 库
- **决策路径**：收益（iOS 玻璃效果 + 小米 UI 风格） vs 风险（设计语言不一致 + 依赖维护风险） → 不借鉴（与本项目 Material Design 体系冲突）
