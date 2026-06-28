# Tasks — PageIndex + basic-memory 双引擎经验搜索增强

> **状态**：🔄 设计中（待用户审核）
> **创建日期**：2026-06-18

---

## 1. 准备工作

- [ ] 1.1 用户审核 OpenSpec 四文档并确认设计方案
- [ ] 1.2 确认 6 个关键决策点（README.md §关键决策点）
- [ ] 1.3 确认本地 llama.cpp 端点地址（默认 http://localhost:8080/v1）
- [ ] 1.4 确认本地 LLM 模型（推荐 Qwen2.5-14B-Instruct，需支持 function-calling）
- [ ] 1.5 克隆 VectifyAI/pageindex 仓库到本地，确认 Python 包可用
- [ ] 1.6 **确认 basic-memory MCP 服务正常运行**（本方案不改动 basic-memory）

---

## 2. PageIndex 树索引生成器（R1, R2）

- [ ] 2.1 创建 `.trae/skills/legado-source-creator/scripts/pageindex-engine/` 目录
- [ ] 2.2 编写 `build_tree_index.py` 主框架（~30 行：argparse + 入口）
- [ ] 2.3 实现目录遍历逻辑（~30 行：os.walk，区分 md/html/json，跳过隐藏文件）
- [ ] 2.4 实现 _index.md 解析器（~60 行：3 种格式 fallback 正则）
  - [ ] 2.4.1 格式1：`## 文件名 — 描述`（special-scenarios 用）
  - [ ] 2.4.2 格式2：`### 文件名\n\n描述`（troubleshooting 用）
  - [ ] 2.4.3 格式3：表格 `| 文件名 | 用途 |`（source-analysis/_INDEX.md 用）
  - [ ] 2.4.4 fallback：首段 `>` 引用块
- [ ] 2.5 实现 md 文件解析器（~40 行：H1 标题 + 首段引用块 + 行数）
- [ ] 2.6 实现树构造 + JSON 输出（~30 行：拼装节点树，json.dumps）
- [ ] 2.7 实现增量更新逻辑（~20 行：mtime 对比，复用未变更节点 summary）
- [ ] 2.8 运行生成 tree-index.json，验证覆盖 58 个 md 文件
- [ ] 2.9 验证 _index.md 摘要提取覆盖率 ≥90%
- [ ] 2.10 编写 `requirements.txt`（litellm==1.83.7, mcp, python-dotenv, pyyaml）

---

## 3. retrieve.py 改造（R3，仅 PageIndex 侧）

- [ ] 3.1 复制 PageIndex 的 `retrieve.py` 为 `retrieve_patched.py`
- [ ] 3.2 改造节点 schema：`line_num` → `file_path` + `line_range`
- [ ] 3.3 重写 `_get_md_page_content` 为 `get_file_content`（按 file_path 读文件，~50 行）
- [ ] 3.4 新增 `get_page_content(file_path, line_range)`（长文档章节检索，~30 行）
- [ ] 3.5 改造 `get_document_structure`：返回树结构时保留 `file_path` 字段
- [ ] 3.6 单元测试：手动构造 3 节点树 JSON，验证 `get_file_content` 和 `get_page_content` 正确返回

---

## 4. 本地 LLM 接入（R4）

- [ ] 4.1 创建 `.env.example` 文件（OPENAI_API_BASE, OPENAI_API_KEY, PAGEINDEX_MODEL）
- [ ] 4.2 创建 `config.yaml`（model: openai/qwen2.5-14b-instruct, api_base, timeout）
- [ ] 4.3 编写 LLM 连通性测试脚本（~20 行：调用一次 chat completion 验证端点）
- [ ] 4.4 验证 llama.cpp 端点可达：`curl http://localhost:8080/v1/models`
- [ ] 4.5 验证 function-calling 能力：构造简单工具调用测试
- [ ] 4.6 若 function-calling 不支持，配置降级算法参数

---

## 5. PageIndex LLM 树导航搜索（R5, R8）

- [ ] 5.1 编写 `search_experience.py` 主框架（~30 行：入口 + 配置加载）
- [ ] 5.2 实现 Agent 模式搜索（~60 行：system_prompt + Agent 循环 + 结果解析）
  - [ ] 5.2.1 构造 system_prompt（经验搜索专用）
  - [ ] 5.2.2 注册 tools: get_document_structure, get_file_content
  - [ ] 5.2.3 实现 Agent 循环（调用 LLM + 工具）
  - [ ] 5.2.4 解析 Agent 输出为标准 JSON 结果
- [ ] 5.3 实现降级算法：逐层选择（~40 行，function-calling 不可用时）
- [ ] 5.4 实现 7 个标准测试 query 验证召回率
  - [ ] 5.4.1 "maccms 视频站选择器" → 期望命中 js-patterns/auto-video-player.md
  - [ ] 5.4.2 "rhino ES5 陷阱" → 期望命中 troubleshooting/rhino-js-traps.md
  - [ ] 5.4.3 "加密图片解密" → 期望命中 special-scenarios/encrypted-images.md
  - [ ] 5.4.4 "CloudFlare 绕过" → 期望命中 special-scenarios/cf-bypass.md
  - [ ] 5.4.5 "RSS 订阅源字段" → 期望命中 source-analysis/rss-source-entity.md
  - [ ] 5.4.6 "AES 加密函数" → 期望命中 js-extensions/crypto-encoding.md
  - [ ] 5.4.7 "HLS 视频播放" → 期望命中 js-patterns/hls-player.md
- [ ] 5.5 验证 PageIndex 单引擎召回率 ≥85%（7 个 query 至少命中 6 个）
- [ ] 5.6 验证搜索延迟 ≤15 秒

---

## 6. 双引擎协同封装（R9, R10）— 核心创新

- [ ] 6.1 编写 `search_experience_smart.py` 主框架（~30 行：入口 + 配置）
- [ ] 6.2 实现 Step 1：basic-memory search_notes 调用（~20 行）
  - [ ] 6.2.1 检测 basic-memory MCP 可用性
  - [ ] 6.2.2 调用 search_notes(hybrid, project="legado")
  - [ ] 6.2.3 判断召回率（命中数 ≥3 视为足够）
- [ ] 6.3 实现 Step 2：PageIndex search_experience 调用（~20 行）
  - [ ] 6.3.1 检测 PageIndex MCP 可用性
  - [ ] 6.3.2 调用 search_experience(query)
  - [ ] 6.3.3 合并 basic-memory 和 PageIndex 结果
- [ ] 6.4 实现 Step 3：Grep references/ 兜底（~20 行）
- [ ] 6.5 实现结果合并去重逻辑（~20 行：按 file_path 去重，标记来源）
  - [ ] 6.5.1 basic-memory 单独命中 → source="basic-memory"
  - [ ] 6.5.2 PageIndex 单独命中 → source="pageindex"
  - [ ] 6.5.3 双引擎都命中 → source="dual-engine-high-confidence"
- [ ] 6.6 实现三级降级自动路由（~10 行）
- [ ] 6.7 集成测试：7 个标准 query 验证双引擎协同召回率 ≥95%

---

## 7. 本地 MCP Server（R8）

- [ ] 7.1 编写 `pageindex_mcp_server.py` 主框架（~30 行：Server 初始化）
- [ ] 7.2 实现 `search_experience` 工具（~20 行：调用 search_experience.py）
- [ ] 7.3 实现 `get_experience_detail` 工具（~15 行：按 file_path + line_range 读文件）
- [ ] 7.4 实现 `list_experience_directory` 工具（~15 行：列目录树）
- [ ] 7.5 实现 `update_tree_index` 工具（~10 行：调用 build_tree_index.py --incremental）
- [ ] 7.6 实现 `search_experience_smart` 工具（~15 行：调用双引擎协同封装）
- [ ] 7.7 本地启动 MCP Server，验证 stdio 通信
- [ ] 7.8 用 MCP inspector 工具测试 5 个工具调用

---

## 8. Skill 文档增强（R11，不替换 basic-memory）

### 8.1 SKILL.md 增强

- [ ] 8.1.1 新增"双引擎协同经验搜索"章节（不替换 L3 经验引擎章节）
- [ ] 8.1.2 新增 PageIndex MCP 工具调用规范表（与 basic-memory 并列）
- [ ] 8.1.3 增强 Phase 1 检查清单：新增 PageIndex 补充搜索步骤
- [ ] 8.1.4 增强 Phase 3 检查清单：新增 update_tree_index 步骤
- [ ] 8.1.5 增强 Phase 5 检查清单：新增 update_tree_index 步骤
- [ ] 8.1.6 新增长文档章节检索用法说明（get_experience_detail）
- [ ] 8.1.7 新增三级降级路径说明（basic-memory → PageIndex → Grep）
- [ ] 8.1.8 更新 Phase 完成标志格式：新增 pageindex 状态

### 8.2 AI_README.md 增强

- [ ] 8.2.1 新增 PageIndex 操作指南（与 basic-memory 并列）
- [ ] 8.2.2 新增双引擎协同使用说明
- [ ] 8.2.3 新增长文档章节检索示例
- [ ] 8.2.4 更新工作流程图（新增 PageIndex 补充步骤）

### 8.3 legado-workflow-auditor/SKILL.md 增强

- [ ] 8.3.1 新增审计步骤：PageIndex 补充搜索执行证据
- [ ] 8.3.2 新增双引擎协同审计说明
- [ ] 8.3.3 更新降级路径（新增 PageIndex）

### 8.4 AGENTS.md 增强

- [ ] 8.4.1 更新 Phase 完成标志格式：新增 pageindex 状态
- [ ] 8.4.2 新增双引擎经验引擎说明（不替换 basic-memory 章节）
- [ ] 8.4.3 更新降级路径：三级降级

### 8.5 docs/INDEX.md 更新

- [ ] 8.5.1 更新 pageindex-local-experience-engine 状态

---

## 9. 集成测试

- [ ] 9.1 端到端测试：模拟 Phase 1 双引擎协同搜索（basic-memory 命中 + PageIndex 补充）
- [ ] 9.2 端到端测试：模拟 Phase 5 精准定位老文档优化（basic-memory metadata + PageIndex update_tree_index）
- [ ] 9.3 端到端测试：长文档章节检索（get_experience_detail）
- [ ] 9.4 端到端测试：审计者双引擎搜索执行证据
- [ ] 9.5 降级测试：停止 basic-memory，验证 PageIndex 接管
- [ ] 9.6 降级测试：停止 llama.cpp，验证降级 Grep
- [ ] 9.7 降级测试：function-calling 失败，验证降级逐层选择
- [ ] 9.8 性能测试：树索引生成 ≤5 秒
- [ ] 9.9 性能测试：增量更新 ≤1 秒
- [ ] 9.10 性能测试：PageIndex 搜索延迟 ≤15 秒
- [ ] 9.11 召回率测试：7 个标准 query 验证双引擎协同 ≥95%
- [ ] 9.12 兼容性测试：basic-memory 现有调用点 100% 正常工作

---

## 10. 文档同步与归档

- [ ] 10.1 编写 `.trae/skills/legado-source-creator/scripts/pageindex-engine/README.md` 使用说明
- [ ] 10.2 更新 `docs/INDEX.md`：移动到"已完成"列表
- [ ] 10.3 更新 README.md 状态为"✅ 已完成"
- [ ] 10.4 tasks.md 全部标记 ✅ YYYY-MM-DD
- [ ] 10.5 清理临时文件和调试代码
- [ ] 10.6 用户最终验收（检查点3）

---

## 验收检查清单

### 功能验收
- [ ] build_tree_index.py 生成 tree-index.json，覆盖 58+ md 文件
- [ ] search_experience_smart("maccms") 优先 basic-memory，命中返回
- [ ] search_experience_smart("rhino 陷阱") basic-memory 未命中时 PageIndex 补充
- [ ] get_experience_detail(file_path, line_range) 返回指定行号区间内容
- [ ] 增量更新：修改 1 个 md 后，仅该节点更新
- [ ] 三级降级：basic-memory → PageIndex → Grep
- [ ] **basic-memory 现有调用点 100% 兼容，零改动**

### 性能验收
- [ ] 树索引生成 ≤5 秒
- [ ] 增量更新 ≤1 秒
- [ ] PageIndex 搜索延迟 ≤15 秒
- [ ] 双引擎协同召回率 ≥95%

### 文档验收
- [ ] SKILL.md 新增 PageIndex 补充搜索流程（不替换 basic-memory）
- [ ] AI_README.md 新增 PageIndex 操作指南
- [ ] legado-workflow-auditor/SKILL.md 新增 PageIndex 补充步骤
- [ ] AGENTS.md Phase 完成标志新增 PageIndex 状态
- [ ] pageindex-engine/README.md 使用说明完整

### 兼容性验收（核心）
- [ ] basic-memory MCP 配置未修改
- [ ] basic-memory project=legado 数据未迁移
- [ ] basic-memory 现有 search_notes/write_note/edit_note 调用全部正常
- [ ] references/ 现有 md 文件未被破坏性修改
