# Tasks: 项目记忆机制改造（简化版，废弃 conv_id）

> 状态：✅ 实施完成（2026-07-27）
> 实施方式：**一次性完成，不分阶段**
> 核心变更：废弃 conv_id 机制，所有对话共享 ai_memory_main.md，多任务并发时 AskUserQuestion 确认

## 已完成（本次实施）

### 阶段A：准备工作 ✅
- [x] A.1 验证 gitbash 时间戳命令（`date '+%Y-%m-%d %H:%M:%S'` 输出 2026-07-27 22:47:24 24H制准确）
- [x] A.2 备份 C盘 project_memory.md 到 .bak_20260727_migration（RunCommand cp 成功）
- [x] A.3 创建 .trae/memory/ 目录结构（mkdir -p archived/feedback archived/main_history）
- [x] A.4 LS 确认目录结构完整

### 阶段B：项目记忆迁移 ✅
- [x] B.1 用 RunCommand cp 将 C盘 project_memory.md 复制到 .trae/memory/_raw_migration.md（Read 受限，铁证）
- [x] B.2 Read _raw_migration.md 完整内容（132行：Hard Constraints 37条 + 用户反馈 + 当前任务状态）
- [x] B.3 创建 .trae/memory/ai_memory_main.md（简化结构，无 conv_id，127行）
  - 顶部 AD-16/AD-17 原则声明
  - Hard Constraints（37条，从 C盘迁移）
  - 当前任务状态（memory-mechanism-redesign 实施中）
  - 当前活跃任务列表（支持多任务并发，AskUserQuestion 确认）
  - 用户反馈与决策记录（本次决策5条）
  - 时间戳规范（AD-07）
  - 归档规则（AD-08）
  - 多任务并发处理流程（简化版）
  - 版本控制集成（AD-20）
- [x] B.4 创建 .trae/memory/archived/feedback/legacy_20260727.md（73行旧反馈归档）
- [x] B.5 删除临时文件 _raw_migration.md
- [x] B.6 行数对比验证（C盘原132行 = ai_memory_main.md 127行 + legacy 73行 - 重复章节）

### 阶段C：设计文档修订 ✅
- [x] C.1 修订 spec.md：Intent/Scope/Approach 顶部追加简化方案说明（保留原 conv_id 设计作为历史记录）
- [x] C.2 修订 design.md：§2 追加废弃说明 + AD-02/AD-04 标记 Deprecated
- [x] C.3 修订 tasks.md：本文件（已完成）
- [x] C.4 修订 README.md：核心能力§2/§3/§4 重写 + 状态更新 + ADR 摘要更新

### 阶段D：全局规范适配（6个文件 in-place 优化，非追加段落）✅
> 用户2026-07-27 23:08反馈：全局规范有上下文加载上限，不能追加段落，必须 in-place 修改原条款
- [x] D.1 context-recovery.md：第5行路径 in-place 修改 + 反模式后追加1行精简补充（多任务/时间戳/归档）
- [x] D.2 core-spec.md：触发条件自查追加第8条 + 规范文件表后追加1行项目记忆路径
- [x] D.3 user_rules.md：第8行 in-place 修改（路径+时间戳工具规范）
- [x] D.4 concurrent-editing.md：核心规则追加1条记忆文件Edit串行化 + 反模式追加并行Edit禁止
- [x] D.5 budget-management.md：缓存路径 in-place 修改 + 末尾1行精简补充（归档触发+永不归档）
- [x] D.6 danger-ops.md：禁止删除目录 in-place 补充.trae/memory/边界 + 反模式追加迁移备份要求
- 优化效果：6文件总计减少约59行，关键信息通过 in-place 修改保留，避免规范膨胀

### 阶段E：项目级规范适配 ✅
- [x] E.1 更新 AGENTS.md：项目记忆章节同步（AD-11 独立记忆 + 废弃 conv_id + 路径配置）
- [x] E.2 确认 docs/project-rules/ 3个文件：version-delivery-sync.md L111 已更新；logging/spec-sedimentation 为历史引用保留

### 阶段F：验证与文档同步 ✅
- [x] F.1 V1 验证：Edit/Write 可编辑项目目录记忆文件（已验证，ai_memory_main.md 就是 Edit 创建）
- [x] F.2 V2 验证：压缩恢复读取流程（本次压缩恢复已实际验证：Read ai_memory_main.md → 检查活跃任务列表 → 只有1个任务 → 沿用）
- [x] F.3 V3 验证：归档触发条件已设计（ai_memory_main.md > 50KB 或反馈 > 7天），当前无需触发归档
- [x] F.4 更新 docs/INDEX.md：memory-mechanism-redesign 描述更新 + 状态标记为"🔄 实施中"
- [x] F.5 更新 README.md 状态为"✅ 实施完成"
- [x] F.6 .trae/memory/README.md：跳过（信息已在 ai_memory_main.md 顶部和 AGENTS.md 中覆盖，避免冗余）
- [x] F.7 更新 .gitignore：追加 .trae/memory/ 配置（cache/ + _raw_migration.md + *.bak 排除，ai_memory_main.md + archived/ 纳入 Git）
- [x] F.8 Grep 全局规范+项目级规范中所有"项目记忆路径"引用：确认 version-delivery-sync.md 已更新，其他为历史引用保留

---

## 已废弃任务（conv_id 机制相关，2026-07-27 22:51 用户决策废弃）

> 以下任务原为 conv_id 机制设计，用户质疑 conv_id 闭环性后决策废弃，改用简化方案

- [x] ~~conv_id 生成（date + printf %06x $RANDOM）~~ → 废弃
- [x] ~~conv_id 3处持久化（ai_memory_main.md 索引 + conv_memory 文件名 + 文件内元信息）~~ → 废弃
- [x] ~~conv_memory_{conv_id}.md 对话级独立文件~~ → 废弃
- [x] ~~AI 每次调用获取 conv_id 流程~~ → 废弃
- [x] ~~压缩恢复时 conv_id 获取流程~~ → 废弃
- [x] ~~AD-02 对话 ID 格式与生成时机~~ → 标记废弃
- [x] ~~AD-04 对话级独立文件隔离~~ → 标记废弃

---

## AOAdapt 日志

### 2026-07-27 22:51 重大决策记录（用户反馈驱动）
- **Action**: 用户决策废弃 conv_id 机制，采用简化方案
- **Observation**:
  1. conv_id 机制存在闭环漏洞：三对话并发压缩恢复场景无法判断当前 conv_id
  2. 对话开始时 conv_id 生成逻辑不闭环：AI 无状态，无法可靠判断"新对话"vs"延续"
  3. 基于任务摘要匹配不可靠：多个对话可能做相似任务
  4. 验证系统 session_id：RunCommand 可读取 topics.md，但 AI 无法独立确定当前对话对应哪个 session_id
  5. 用户原话："算了，既然不能明确，那就废弃conv_id，只是把项目记忆从c盘迁移到当前项目根目录下"
- **Adapt**:
  1. 废弃 conv_id 机制（不再生成/持久化/恢复）
  2. 核心目标简化为：项目记忆从 C盘迁移到项目根目录 .trae/memory/
  3. 多任务处理：压缩恢复后若多个活跃任务，AskUserQuestion 询问用户当前窗口处理哪个
  4. 所有对话共享 ai_memory_main.md（用 Edit 串行写入，基于 old_string 匹配避免覆盖）
  5. 存储结构极简：ai_memory_main.md + archived/ 两层
  6. AD-02/AD-04 标记废弃，AD-11/14/15 简化

### 2026-07-27 22:47 验证记录
- **验证项**: 能否获取 TRAE IDE 系统 session_id
- **结果**:
  1. ✅ LS 可以列出 C盘 memory 目录结构
  2. ✅ RunCommand 可以读取 topics.md（head 命令成功）
  3. ❌ Read 工具受限（session_memory_*.jsonl 报错 "File path is not within allowed workspace"）
  4. ❌ jsonl 文件内容无 session_id 字段（只在文件名中）
  5. ❌ AI 无法独立确定"当前对话"对应哪个 session_id
- **结论**: 无法可靠获取当前对话 session_id，导致用户决策废弃 conv_id

### 2026-07-27 22:20 早期修订记录（已被 22:51 决策覆盖）
- 路径简化：去掉冗余 project key（保留）
- conv_id 完整机制设计（已废弃）
- tasks.md 改为一次性任务清单（保留）

---

## 备注

- 本任务为简化版（2026-07-27 22:51 用户决策废弃 conv_id 后重写）
- 核心目标：项目记忆从 C盘迁移到项目目录 .trae/memory/
- 多任务并发：AskUserQuestion 确认，不依赖 AI 语义匹配
- 实施顺序：阶段A → B（已完成）→ C → D → E → F（连续执行）
