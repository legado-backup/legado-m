# Spec — PageIndex + basic-memory 双引擎经验搜索增强

---

## 1. Intent（意图）

### 1.1 为什么做这件事

当前 `legado-source-creator` Skill 使用 `basic-memory` MCP 作为经验引擎（L3 索引层），已在生产中稳定运行，召回率 100%，73 条历史经验已沉淀。但存在三个**单引擎局限**：

1. **发现性搜索弱**：basic-memory 是扁平笔记集合，AI 不知道有什么经验时，无法"按主题目录浏览"
2. **长文档内检索难**：经验文档很长（如 rhino-security.md 555行），basic-memory 返回整篇笔记，AI 需自行扫描定位章节
3. **无目录树视图**：references/ 是天然树结构（58 md、3 层、6 大子目录），但 basic-memory 无目录树概念

### 1.2 解决什么问题

**不是替换 basic-memory**，而是**新增 PageIndex 树导航作为补充引擎**，形成"双引擎协同"架构：

- **basic-memory 保留**：继续负责向量语义搜索、知识图谱、metadata 精确定位、经验写入
- **PageIndex 新增**：负责 LLM 树导航发现、长文档章节检索、目录树浏览
- **双引擎协同**：basic-memory 首选（召回率高），PageIndex 补充（发现性强），Grep 兜底

### 1.3 最终目的

让 AI（自己或其他 agent）在用 skill 开发书源/订阅源时：
1. **快速搜索**：双引擎协同，覆盖语义相似+推理发现两种搜索模式
2. **精准定位**：能精准定位到老经验文档，进行优化修改（basic-memory metadata + PageIndex 树路径）
3. **获取知识**：能获取长文档内具体章节内容（PageIndex get_page_content）

### 1.4 为什么不替换而要结合

| 原因 | 说明 |
|------|------|
| basic-memory 召回率 100% | 已验证 7/7 查询命中，替换会丢失这个优势 |
| basic-memory 有知识图谱 | build_context 关系遍历是 PageIndex 没有的能力 |
| basic-memory 有写入能力 | write_note/edit_note 是 PageIndex 没有的能力 |
| 73 条历史经验已沉淀 | 迁移成本高且有丢失风险，保留原位更稳 |
| PageIndex 有树导航 | basic-memory 没有的发现性搜索能力 |
| PageIndex 有长文档检索 | basic-memory 返回整篇，PageIndex 可章节级定位 |
| 两者互补不冲突 | 一个擅长"已知精确查询"，一个擅长"未知发现探索" |

---

## 2. Scope（范围）

### 2.1 做什么

| 范围 | 说明 |
|------|------|
| **PageIndex 树索引生成器** | 扫描 references/ 目录，生成 PageIndex 兼容的树索引 JSON |
| **retrieve.py 改造** | `line_num` 语义改为 `file_path`，按文件路径读内容 |
| **本地 LLM 接入** | 配置 LiteLLM + llama.cpp OpenAI 兼容端点 |
| **本地 MCP Server** | 自写薄包装层，暴露 PageIndexClient 为 MCP 工具 |
| **双引擎协同封装** | 封装 `search_experience_smart()` 自动路由 basic-memory/PageIndex |
| **Skill 文档增强** | SKILL.md / AI_README.md / auditor / AGENTS.md 新增 PageIndex 流程 |
| **降级路径增强** | 三级降级：basic-memory → PageIndex → Grep |

### 2.2 不做什么

| 排除项 | 原因 |
|--------|------|
| **不替换 basic-memory** | 保留全部功能，73 条经验不迁移 |
| **不修改 basic-memory 调用点** | 现有 search_notes/write_note 调用保持不变 |
| **不实现 PageIndex 写入功能** | PageIndex 仅作只读补充引擎，写入仍由 basic-memory 负责 |
| **不实现 PageIndex 知识图谱** | 关系遍历仍由 basic-memory build_context 负责 |
| **不购买 PageIndex 企业版** | 纯用 Python 包本地模式，零成本 |
| **不使用 PageIndex 官方 MCP** | 官方 MCP 是云端代理，不符合本地化要求 |

### 2.3 影响哪些模块

| 模块 | 影响 | 性质 |
|------|------|------|
| `.trae/skills/legado-source-creator/SKILL.md` | 中改（~15 处）：新增 PageIndex 补充搜索流程、双引擎协同说明 | **增强**（非替换） |
| `.trae/skills/legado-source-creator/AI_README.md` | 小改（~8 处）：新增 PageIndex 操作指南 | **增强** |
| `.trae/skills/legado-workflow-auditor/SKILL.md` | 小改（~5 处）：新增 PageIndex 补充搜索步骤 | **增强** |
| `AGENTS.md` | 小改（~3 处）：Phase 完成标志新增 PageIndex 状态 | **增强** |
| `.trae/skills/legado-source-creator/scripts/` | 新增：`pageindex-engine/` 目录 | **新增** |
| `docs/INDEX.md` | 小改：状态更新 | **更新** |
| **basic-memory 相关** | **无改动** | **保留** |

---

## 3. Approach（方法）

### 3.1 技术方向

**双引擎协同**：basic-memory（向量+图谱+元数据）+ PageIndex（树导航+长文档检索）

```
查询 query
    │
    ├─ search_experience_smart(query)  ← 统一封装入口
    │   │
    │   ├─ Step 1: basic-memory search_notes(hybrid)  ← 首选，召回率 100%
    │   │   └─ 命中 → 返回
    │   │
    │   ├─ Step 2: PageIndex search_experience(query)  ← 补充，发现性
    │   │   └─ LLM 树导航 → 命中 → 返回
    │   │
    │   └─ Step 3: Grep references/  ← 兜底
    │
    └─ get_experience_detail(file_path, line_range)  ← 长文档章节检索
        └─ PageIndex get_page_content(file_path, line_range)
```

### 3.2 方案选择

| 决策 | 选择 | 备选 | 理由 |
|------|------|------|------|
| PageIndex 定位 | **补充引擎** | 替换引擎 | 保留 basic-memory 优势，互补增强 |
| 双引擎协同方式 | **basic-memory 首选 + PageIndex 补充** | 并行查询 | 避免重复结果，basic-memory 召回率高优先 |
| 树索引生成方式 | **手动构造**（扫描目录） | PageIndex md_to_tree | references/ 是多文件目录树，_index.md 已有摘要 |
| 搜索算法 | **LLM Agent 工具调用** | 逐层选择 | 复用 PageIndex 官方 Agent 模式 |
| LLM 接入 | **LiteLLM + llama.cpp** | 直接 OpenAI SDK | LiteLLM 是 PageIndex 已用依赖 |
| 部署形态 | **本地 Python + 本地 MCP** | 仅命令行 | MCP 形态对齐 basic-memory |
| 数据存储 | **JSON 文件 + git** | SQLite | JSON 可 git 版本管理 |
| basic-memory 数据 | **完全保留不迁移** | 导出合并 | 避免迁移风险，保留存量价值 |

### 3.3 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│  references/ 目录（权威源，markdown 文件）                    │
│  ├── _INDEX.md  ├── troubleshooting/  ├── js-extensions/ ...│
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│  basic-memory（保留）    │  │  PageIndex 树索引生成器       │
│  • 73条历史经验          │  │  build_tree_index.py         │
│  • 向量索引              │  │  → tree-index.json           │
│  • 知识图谱              │  │  → 扫描 references/ 目录      │
└───────────┬─────────────┘  └──────────────┬──────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│  basic-memory MCP       │  │  PageIndex MCP Server        │
│  • search_notes          │  │  • search_experience         │
│  • write_note           │  │  • get_experience_detail      │
│  • build_context        │  │  • list_experience_directory │
│  • edit_note            │  │  • update_tree_index         │
└───────────┬─────────────┘  └──────────────┬──────────────┘
            │                               │
            └───────────────┬───────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  双引擎协同封装（search_experience_smart）                    │
│  • 自动路由：basic-memory 首选 → PageIndex 补充 → Grep 兜底  │
│  • 结果合并：去重 + 排序                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Skill 调用（SKILL.md Phase 1/3/5）                         │
│  • Phase 1: search_experience_smart(query)                  │
│  • Phase 5: edit_note + update_tree_index                   │
│  • 审计: search_notes(tags) + search_experience             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  llama.cpp（本地 LLM，OpenAI 兼容端点）                       │
│  模型：Qwen2.5-14B-Instruct（支持 function-calling）          │
│  端点：http://localhost:8080/v1                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Requirements（需求）

### 4.1 功能需求

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| R1 | PageIndex 树索引生成器 | P0 | 扫描 references/ 生成 tree-index.json，覆盖 58 个 md 文件 |
| R2 | _index.md 解析器 | P0 | 解析 6 个 _index.md，提取"一句话描述"+"触发关键词"，覆盖率 ≥90% |
| R3 | retrieve.py 改造 | P0 | `line_num` 语义改为 `file_path`，新增 `get_file_content()` 函数 |
| R4 | 本地 LLM 接入 | P0 | 配置 LiteLLM + llama.cpp，OPENAI_API_BASE 指向本地端点 |
| R5 | PageIndex LLM 树导航搜索 | P0 | 输入 query → LLM 推理导航 → 返回命中文件路径+内容 |
| R6 | 长文档章节检索 | P1 | get_page_content(file_path, line_range) 返回指定行号区间内容 |
| R7 | 增量更新 | P1 | 文件 mtime 对比，仅更新变更节点 |
| R8 | 本地 MCP Server | P0 | 暴露 search_experience 等工具 |
| R9 | 双引擎协同封装 | P0 | search_experience_smart() 自动路由 basic-memory/PageIndex/Grep |
| R10 | 三级降级路径 | P0 | basic-memory → PageIndex → Grep |
| R11 | Skill 文档增强 | P0 | SKILL.md/AI_README.md/auditor/AGENTS.md 新增 PageIndex 流程 |
| R12 | basic-memory 保留 | P0 | 现有 basic-memory 调用点全部保留，不修改 |

### 4.2 非功能需求

| ID | 需求 | 指标 |
|----|------|------|
| NF1 | 双引擎协同召回率 | ≥95%（basic-memory 100% + PageIndex 补充） |
| NF2 | PageIndex 搜索延迟 | ≤15 秒（3-5 次 LLM 调用） |
| NF3 | 树索引生成耗时 | ≤5 秒（58 个文件，无 LLM 摘要） |
| NF4 | 增量更新耗时 | ≤1 秒（mtime 对比） |
| NF5 | PageIndex 本地化 | 零云端依赖（除 llama.cpp 模型文件） |
| NF6 | basic-memory 兼容性 | 现有调用点 100% 兼容，零改动 |
| NF7 | 数据版本化 | tree-index.json 可纳入 git |

---

## 5. Scenarios（场景）

### 5.1 正常流程

**场景 1：Phase 1 经验搜索（双引擎协同）**

```
用户创建书源 → Skill 执行 Phase 1
→ 调用 search_experience_smart(query="maccms 视频站选择器")
→ Step 1: basic-memory search_notes(hybrid)
   → 命中 js-patterns/auto-video-player.md（向量相似）
   → 召回率 ≥85%，返回结果
→ [若 basic-memory 未命中] Step 2: PageIndex search_experience
   → LLM 读取 tree-index.json
   → 推理导航：troubleshooting/ → js-patterns/ → auto-video-player.md
   → 返回命中文件路径+内容片段
→ [若 PageIndex 未命中] Step 3: Grep references/
   → 关键词匹配兜底
→ Skill 基于经验编写书源规则
→ [PHASE1_COMPLETE] basic-memory搜索:命中, pageindex补充:未触发/命中, 陷阱检查:已检查
```

**场景 2：长文档章节精准检索**

```
AI 需要查看 rhino-security.md 的"安全策略"章节（555行文档）
→ 调用 mcp_pageindex_get_experience_detail(
    file_path="source-analysis/rhino-security.md",
    line_range="200-350"
  )
→ PageIndex get_page_content 按行号区间读取
→ 返回第 200-350 行内容（"安全策略"章节）
→ AI 基于章节内容编写书源规则
```

**场景 3：Phase 5 经验反哺（精准定位老文档优化）**

```
书源创建完成 → Skill 执行 Phase 5
→ Step 1: 精准定位老文档
   → basic-memory search_notes(tags=["maccms","video"], project="legado")
   → 命中已有经验笔记 + source_doc 指针指向 references/js-patterns/auto-video-player.md
→ Step 2: 优化修改老文档
   → 编辑 references/js-patterns/auto-video-player.md（追加新经验）
   → basic-memory edit_note 同步更新索引层
   → PageIndex update_tree_index 增量更新树索引（mtime 变更）
→ Step 3: 新经验写入（如果是新经验）
   → references/ 新建 md
   → basic-memory write_note 写入索引层
   → PageIndex update_tree_index 增量更新
→ [PHASE5_COMPLETE] 双写:完成(basic-memory+references), PageIndex索引:已更新, Schema验证:通过
```

**场景 4：审计者双引擎搜索执行证据**

```
legado-workflow-auditor Skill 执行审计
→ Step 1: basic-memory 精确查询（首选）
   → search_notes(tags=["execution-log"], metadata_filters={source_name: "91dasj"})
   → 精确命中执行证据
→ [若未命中] Step 2: PageIndex 树导航（补充）
   → search_experience("执行证据: 91dasj")
   → LLM 导航到 execution-logs/ 目录
→ 审计者基于证据生成审计报告
```

### 5.2 异常流程

**场景 5：basic-memory 不可用，PageIndex 接管**

```
basic-memory MCP 服务未启动
→ search_experience_smart 检测 basic-memory 不可用
→ 自动跳过 Step 1，直接进入 Step 2: PageIndex 树导航
→ LLM 推理导航返回结果
→ [PHASE1_COMPLETE] basic-memory搜索:降级, pageindex补充:命中, 陷阱检查:已检查
```

**场景 6：PageIndex LLM 不可用**

```
llama.cpp 服务未启动
→ PageIndex search_experience 调用 LLM 失败
→ 自动降级 Step 3: Grep references/
→ 返回 Grep 结果
→ [PHASE1_COMPLETE] basic-memory搜索:命中, pageindex补充:降级Grep, 陷阱检查:已检查
```

**场景 7：function-calling 模型能力不足**

```
Qwen2.5-14B 工具调用失败
→ PageIndex 降级为"顶层向下逐层选择"算法（非 Agent 模式）
→ 逐层让 LLM 选择最相关子节点
→ 返回命中叶子节点
```

### 5.3 边界条件

| 边界条件 | 处理 |
|---------|------|
| references/ 目录为空 | PageIndex 返回空，basic-memory 正常 |
| 查询 query 为空 | 返回根节点 summary（_INDEX.md 内容） |
| 双引擎都未命中 | 返回"未命中"，建议查源码 |
| 树索引过期（文件变更未更新） | mtime 对比检测，自动增量更新 |
| basic-memory 和 PageIndex 结果重复 | 去重（按 file_path 合并） |
| cms-samples 目录（非 md 内容） | PageIndex 仅索引 _INDEX.md |
| 超长 query（>500 字符） | 截断 + 提示 |

---

## 6. 验收标准

### 6.1 功能验收

- [ ] `build_tree_index.py` 生成 tree-index.json，覆盖 58 个 md 文件
- [ ] `search_experience_smart("maccms")` 优先 basic-memory，命中返回
- [ ] `search_experience_smart("rhino 陷阱")` basic-memory 未命中时 PageIndex 补充
- [ ] `get_experience_detail(file_path, line_range)` 返回指定行号区间内容
- [ ] 增量更新：修改 1 个 md 后，仅该节点更新
- [ ] 三级降级：basic-memory → PageIndex → Grep
- [ ] basic-memory 现有调用点 100% 兼容，零改动

### 6.2 性能验收

- [ ] 树索引生成 ≤5 秒
- [ ] 增量更新 ≤1 秒
- [ ] PageIndex 搜索延迟 ≤15 秒
- [ ] 双引擎协同召回率 ≥95%

### 6.3 文档验收

- [ ] SKILL.md 新增 PageIndex 补充搜索流程（不替换 basic-memory）
- [ ] AI_README.md 新增 PageIndex 操作指南
- [ ] legado-workflow-auditor/SKILL.md 新增 PageIndex 补充步骤
- [ ] AGENTS.md Phase 完成标志新增 PageIndex 状态
