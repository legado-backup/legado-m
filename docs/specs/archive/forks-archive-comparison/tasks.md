# 任务清单 — 阅读 Archive 私仓深度对比与借鉴分析

> 任务执行顺序：按章节顺序，不可跳过中间任务。每完成一项标记 ✅，遇到问题标记 ⚠️ 并附 AOAdapt 日志。

---

## 1. 准备工作

- [x] 1.1 克隆阅读 Archive 私仓到 `temp/forks-comparison/legado-archive/`
  - Action: `git clone --depth 1 https://github.com/Rimchars/legado-private-armv8-release.git legado-archive`
  - Observation: 成功克隆 2418 个文件，最新 tag `private-armv8-3.26.07071245`，最新提交 `6952bc6`（修复日记主题分离遗留问题与字体撞色防护）
  - Adapt: 无需调整，浅克隆已满足对比需求
- [x] 1.2 扫描仓库结构与关键文件
  - Action: Read README.md / CHANGELOG.md / app/build.gradle / .github/workflows/private-armv8-release.yml
  - Observation: 确认为源码仓库（非 release 产物），已识别 Compose/liquidglass/miuix/sora-editor 等新依赖与 armv8 单架构 CI
  - Adapt: 无需调整

## 2. 文件结构对比

- [x] 2.1 对比顶层目录结构（根目录 + app/ + modules/）✅ Level 2
- [x] 2.2 对比 Java/Kotlin 源码包结构（`io/legado/app/` 子目录差异）✅ Level 2
  - 发现：Archive 独有 help/ai/（30+文件）、help/config/ 扩展（8 文件）、help/book/library/ 等
  - 发现：本项目独有 lib/（aliyun/cronet/mobi/icu4j/theme/webdav）、help/Highlight*（10 文件）、CoverGallery、AutoTask 等
- [x] 2.3 对比 res 资源（drawable/layout/menu/values/anim）✅ Level 1（未深入对比，聚焦 java 层）
- [x] 2.4 对比 assets（defaultData/web/help/bg/font/textmate）✅ Level 1（EPUB assets 在 SA-2 中对比）

## 3. 关键模块对比（子代理并行）

> 单子代理 ≤ 12 文件，并行批次启动，交叉验证

- [x] 3.1 主题管理模块对比 ✅ Level 2（SA-1 子代理，9 个 Archive 新文件识别）
- [x] 3.2 EPUB 阅读模块对比 ✅ Level 2（SA-2 子代理，3 项差异）
- [x] 3.3 AI 助手模块对比 ✅ Level 2（SA-3 子代理，6 项差异 + 30+ 文件清单）
- [x] 3.4 发现页与订阅源对比 ✅ Level 2（SA-4 子代理，6 项差异）
- [x] 3.5 视频播放对比 ✅ Level 2（SA-5 子代理，8 项差异）
- [x] 3.6 构建配置对比 ✅ Level 2（SA-6 子代理，9 项差异 + 修正 Compose 认知）
- [x] 3.7 依赖库对比 ✅ Level 2（SA-7 子代理 + SA-6 交叉验证）

## 4. 差异识别与价值评估

- [x] 4.1 汇总所有差异点（按模块归类）✅ 47 项差异汇总到 analysis-report.md
- [x] 4.2 价值评估（每项差异附 1-5 分收益 + 1-5 分风险 + 借鉴成本）✅ 已附评分

## 5. 借鉴决策表输出

- [x] 5.1 输出 `borrow-decisions.md`（三态决策表：借鉴 12 / 不借鉴 8 / 待评估 9）✅
- [x] 5.2 输出 `analysis-report.md`（差异分析报告，含 mermaid 图）✅

## 6. 验证与文档同步

- [x] 6.1 交叉验证：主代理 Read 子代理产出 + 抽样核对源码 ✅
  - 修正认知：本项目也启用了 Compose（非 Archive 独有）
  - 修正认知：本项目也有 BiliDanmukuParser（非 Archive 独有）
  - 修正认知：本项目 minSdk 23 比 Archive 21 更高，不需降级
- [x] 6.2 更新 `docs/INDEX.md`（状态：🔄 设计中 → 🔄 开发中 → 待验收）✅
- [ ] 6.3 更新 `docs/project-rules/forks-reference.md`（补充阅读 Archive 私仓地址与对比结论索引）⏳ 待检查点3后执行
- [ ] 6.4 沉淀经验：本次对比方法论是否有可复用模式（写入 project_memory）⏳ 待检查点3后执行

---

## AOAdapt 日志（汇总）

| 任务 | Action | Observation | Adapt |
|------|--------|-------------|-------|
| 1.1 | 浅克隆私仓 | 2418 文件成功克隆 | 无 |
| 1.2 | Read 关键文件 | 确认源码仓库 + 识别新依赖 | 无 |
| 2.2 | LS 两边 java 包 | 发现 Archive 独有 help/ai/ 30+文件 | 启动 SA-3 子代理深度分析 |
| 3.6 | SA-6 子代理对比构建 | 发现本项目也启用 Compose（修正认知） | 在 analysis-report.md 中修正 S1 场景 |
| 3.5 | SA-5 子代理对比视频 | 发现两边都有 BiliDanmukuParser | 在决策表中标记"已有" |
| 5.1 | 写 borrow-decisions.md | 汇总 29 项决策 | 按 P0/P1/P2/P3 优先级排序 |
| 6.1 | 交叉验证 | 3 项认知修正 | 已在 analysis-report.md §4.1 记录 |

---

## 完成级别

- **Level 1 代码完成**：✅ 6.2 INDEX.md 已更新
- **Level 2 功能验证**：✅ analysis-report.md + borrow-decisions.md 已生成，含 7 模块对比 + 29 项决策
- **Level 3 场景验证**：⏳ 待检查点2用户审核 + 检查点3最终验收
