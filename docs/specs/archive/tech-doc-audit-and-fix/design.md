# Tasks

* [x] Task 1: 重写 openspec-workflow\.md — 核心结构升级 ✅ 2026-06-22

  * [x] SubTask 1.1: 新增「三级文档规模」章节（Full/Standard/Minimal 定义 + 适用场景表 + 升级规则） ✅ 2026-06-22

  * [x] SubTask 1.2: 修改「文档结构」章节 — spec.md 增加 Alternatives Considered / Drawbacks / Prior Art 子章节定义 ✅ 2026-06-22

  * [x] SubTask 1.3: 修改「文档结构」章节 — design.md Architecture Decisions 改为 ADR Y-Statement 模板 ✅ 2026-06-22

  * [x] SubTask 1.4: 修改「文档结构」章节 — tasks.md 增加 AOAdapt 日志格式定义 ✅ 2026-06-22

  * [ ] SubTask 1.5: 修改「文档结构」章节 — 文档目录统一为 `docs/specs/{功能名称}/`（原任务描述为`.trae/specs/{change-id}/`，用户要求必须使用`docs/specs/`，需修正任务描述并确认实现）

* [x] Task 2: 重写 openspec-workflow\.md — 工作流程升级 ✅ 2026-06-22

  * [x] SubTask 2.1: 修改「完整工作流程」— 步骤2 需求分析增加「评估文档规模级别」 ✅ 2026-06-22

  * [x] SubTask 2.2: 修改「完整工作流程」— 步骤3 生成文档改为「按评估级别生成对应文档」 ✅ 2026-06-22

  * [x] SubTask 2.3: 修改「完整工作流程」— 步骤5 增加任务级 AOAdapt 日志记录要求 ✅ 2026-06-22

  * [x] SubTask 2.4: 修改「完整工作流程」— 检查点2 增加「任务级审查」可选模式 ✅ 2026-06-22

* [x] Task 3: 重写 openspec-workflow\.md — 辅助章节升级 ✅ 2026-06-22

  * [x] SubTask 3.1: 更新「强制检查点」章节 — 增加检查点2 的可跳过条件（Minimal 级别合并到检查点3） ✅ 2026-06-22

  * [x] SubTask 3.2: 更新「AI Agent OpenSpec 检查清单」— 增加规模级别确认、Alternatives/Drawbacks 确认、ADR 格式确认 ✅ 2026-06-22

  * [x] SubTask 3.3: 更新「正确示例 vs 错误示例」— 补充 Standard/Minimal 级别的示例 ✅ 2026-06-22

  * [x] SubTask 3.4: 更新「文档状态流转」— 增加规模级别标记 ✅ 2026-06-22

* [x] Task 4: 同步更新 AGENTS.md 中的 OpenSpec 章节 ✅ 2026-06-22

  * [x] SubTask 4.1: 更新 AGENTS.md 中 OpenSpec 章节的四文档描述为三级文档规模 ✅ 2026-06-22

  * [x] SubTask 4.2: 更新 AGENTS.md 中 OpenSpec 章节的检查点描述（增加 Minimal 级别灵活性） ✅ 2026-06-22

  * [ ] SubTask 4.3: 更新 AGENTS.md 中 OpenSpec 章节的文档目录为 `docs/specs/{功能名称}/`（原任务描述为`.trae/specs/`，用户要求必须使用`docs/specs/`，需修正任务描述并确认实现）

* [ ] Task 5: 验证与回归（SubTask 1.5 和 4.3 未完成，验证未通过）

  * [ ] SubTask 5.1: 通读重写后的 openspec-workflow\.md，确认无内部矛盾

  * [ ] SubTask 5.2: 确认 AGENTS.md 与 openspec-workflow\.md 描述一致

  * [ ] SubTask 5.3: 确认文档目录路径为 `docs/specs/{功能名称}/`（非 `.trae/specs/`）

# Task Dependencies

* Task 2 depends on Task 1（工作流程引用文档结构定义）

* Task 3 depends on Task 1 + Task 2（辅助章节引用核心结构和工作流程）

* Task 4 depends on Task 1 + Task 2 + Task 3（AGENTS.md 同步需要核心内容完成）

* Task 5 depends on Task 4（验证需要所有文档完成）

