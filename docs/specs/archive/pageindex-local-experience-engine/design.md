# Design — PageIndex + basic-memory 双引擎经验搜索增强

---

## 1. Technical Approach（技术方法）

### 1.1 整体技术栈

| 层 | 技术 | 用途 | 备注 |
|----|------|------|------|
| **basic-memory MCP** | 现有 | 向量搜索+图谱+元数据+写入 | **保留不动** |
| **PageIndex 树索引** | VectifyAI/PageIndex（MIT） | LLM 树导航+长文档检索 | **新增** |
| **LLM 推理** | llama.cpp | 本地 LLM，OpenAI 兼容端点 | **新增** |
| **LLM 模型** | Qwen2.5-14B-Instruct | 支持 function-calling | **新增** |
| **LLM 统一层** | LiteLLM 1.83.7 | PageIndex 已用依赖 | **新增** |
| **MCP Server** | mcp Python SDK | PageIndex 本地 MCP 包装 | **新增** |
| **数据格式** | JSON | 树索引文件，可 git | **新增** |

### 1.2 核心组件

#### 组件 1：目录树索引生成器（build_tree_index.py）

**职责**：扫描 references/ 目录，生成 PageIndex 兼容的树索引 JSON

**输入**：references/ 目录路径
**输出**：tree-index.json（PageIndex schema）

**核心算法**：
```python
def build_tree(root_dir):
    tree = {
        "id": "references",
        "title": extract_h1(read_md(root_dir / "_INDEX.md")),
        "summary": extract_first_quote(read_md(root_dir / "_INDEX.md")),
        "type": "branch",
        "path": str(root_dir),
        "children": []
    }
    for subdir in sorted_subdirs(root_dir):
        if subdir.name.startswith('.'):
            continue
        child = build_branch_node(subdir)
        tree["children"].append(child)
    for md_file in sorted_md_files(root_dir):
        if md_file.name.startswith('_'):
            continue
        tree["children"].append(build_leaf_node(md_file))
    return tree

def build_leaf_node(md_file):
    content = read_md(md_file)
    return {
        "id": str(md_file.relative_to(references_root)).replace('\\', '/').replace('.md', ''),
        "title": extract_h1(content),
        "summary": extract_first_quote(content),
        "type": "leaf",
        "path": str(md_file),
        "line_range": [1, count_lines(content)],
        "mtime": get_mtime(md_file)
    }
```

**_index.md 解析器**（兼容 3 种格式）：
```python
def extract_summary_from_index(index_md_path):
    content = read_md(index_md_path)
    # 格式1：## 文件名 — 描述（special-scenarios）
    # 格式2：### 文件名\n\n描述（troubleshooting）
    # 格式3：表格 | 文件名 | 用途 |（source-analysis/_INDEX.md）
    for pattern in [FORMAT1_REGEX, FORMAT2_REGEX, TABLE_REGEX]:
        match = pattern.search(content)
        if match:
            return match.group(1)
    return extract_first_quote(content)  # fallback
```

**增量更新**：
```python
def incremental_update(root_dir, old_index_path):
    old_index = json.load(open(old_index_path))
    new_index = build_tree(root_dir)
    merge_summaries(old_index, new_index)  # mtime 对比，复用未变更节点
    return new_index
```

#### 组件 2：retrieve.py 改造（仅 PageIndex 侧，不动 basic-memory）

**原版**（PageIndex 的 `retrieve.py`）：
```python
def _get_md_page_content(doc_info, page_nums):
    # 用 line_num 匹配，返回行号区间内容
    min_line, max_line = min(page_nums), max(page_nums)
    for node in walk_structure(doc_info["structure"]):
        if min_line <= node["line_num"] <= max_line:
            result += node["text"]
    return result
```

**改造版**（新增 `get_file_content` + `get_page_content`）：
```python
def get_file_content(doc_info, file_paths):
    """按文件路径读取完整内容"""
    result = []
    for node in walk_structure(doc_info["structure"]):
        if node.get("file_path") in file_paths:
            content = read_file(node["file_path"])
            result.append({
                "file_path": node["file_path"],
                "title": node["title"],
                "summary": node["summary"],
                "content": content,
                "line_range": node.get("line_range")
            })
    return result

def get_page_content(doc_info, file_path, line_range):
    """按文件路径+行号区间读取章节内容（长文档精准检索）"""
    start_line, end_line = parse_line_range(line_range)  # "200-350" → (200, 350)
    content = read_file_lines(file_path, start_line, end_line)
    return {
        "file_path": file_path,
        "line_range": [start_line, end_line],
        "content": content
    }
```

#### 组件 3：双引擎协同封装（search_experience_smart.py）— 核心创新

**职责**：统一入口，自动路由 basic-memory / PageIndex / Grep

```python
async def search_experience_smart(query, basic_memory_mcp, pageindex_mcp):
    """双引擎协同搜索：basic-memory 首选 → PageIndex 补充 → Grep 兜底"""
    
    # Step 1: basic-memory 向量语义搜索（首选，召回率 100%）
    try:
        bm_result = await basic_memory_mcp.search_notes(
            query=query,
            search_type="hybrid",
            project="legado",
            page_size=10
        )
        if bm_result and len(bm_result) >= 3:  # 召回率足够
            return deduplicate_and_rank(bm_result, source="basic-memory")
    except Exception as e:
        log(f"basic-memory 不可用: {e}, 降级到 PageIndex")
        bm_result = []
    
    # Step 2: PageIndex 树导航（补充，发现性探索）
    try:
        pi_result = await pageindex_mcp.search_experience(query)
        if pi_result and pi_result.get("hits"):
            # 合并 basic-memory 和 PageIndex 结果，去重
            merged = merge_results(bm_result, pi_result["hits"])
            return deduplicate_and_rank(merged, source="dual-engine")
    except Exception as e:
        log(f"PageIndex 不可用: {e}, 降级到 Grep")
    
    # Step 3: Grep references/ 兜底
    grep_result = grep_references(query)
    return grep_result

def merge_results(bm_results, pi_results):
    """合并双引擎结果，按 file_path 去重"""
    merged = {}
    for r in bm_results:
        fp = r.get("source_doc") or r.get("file_path")
        if fp and fp not in merged:
            merged[fp] = {**r, "source": "basic-memory"}
    for r in pi_results:
        fp = r.get("file_path")
        if fp and fp not in merged:
            merged[fp] = {**r, "source": "pageindex"}
        elif fp:
            # 双引擎都命中，标记高可信
            merged[fp]["source"] = "dual-engine-high-confidence"
    return list(merged.values())
```

#### 组件 4：PageIndex LLM 树导航搜索（search_experience.py）

**算法**：复用 PageIndex 官方 Agent 模式

```python
async def search_experience(query, tree_index_path, llm_config):
    client = PageIndexClient(workspace=workspace_dir)
    doc_id = "references"
    
    system_prompt = f"""你是 Legado 书源经验搜索引擎。
可用工具：
- get_document_structure(): 返回经验树结构（目录+文件+摘要）
- get_file_content(file_paths): 按路径读取经验文件内容

任务：根据用户查询，先调用 get_document_structure 查看树结构，
推理出最相关的文件，再调用 get_file_content 读取内容。
返回 JSON：{{"hits": [{{"file_path": "...", "reason": "...", "snippet": "..."}}]}}

用户查询：{query}"""
    
    agent = Agent(
        name="experience_searcher",
        instructions=system_prompt,
        tools=[get_document_structure_tool, get_file_content_tool],
        model=llm_config["model"]
    )
    result = await Runner.run(agent, query)
    return parse_search_result(result.final_output)
```

**降级算法**（function-calling 不可用时）：
```python
async def search_experience_fallback(query, tree_index, llm_config):
    """顶层向下逐层选择（非 Agent 模式）"""
    current_nodes = [tree_index]
    while current_nodes:
        prompt = build_selection_prompt(query, current_nodes)
        selected = await llm_complete(prompt, llm_config)
        current_nodes = [n for n in current_nodes if n["id"] in selected]
        leaves = [n for n in current_nodes if n["type"] == "leaf"]
        if leaves:
            return leaves
        current_nodes = [child for n in current_nodes for child in n.get("children", [])]
    return []
```

#### 组件 5：本地 MCP Server（pageindex_mcp_server.py）

**职责**：将 PageIndexClient 暴露为 MCP 工具

```python
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_experience",
            description="PageIndex 树导航搜索（发现性探索，补充 basic-memory）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_experience_detail",
            description="长文档章节精准检索（按 file_path + line_range）",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "line_range": {"type": "string", "description": "如 '200-350'"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="list_experience_directory",
            description="列出经验目录树结构",
            inputSchema={"type": "object", "properties": {"directory": {"type": "string"}}}
        ),
        Tool(
            name="update_tree_index",
            description="增量更新树索引（Phase 5 经验反哺后调用）",
            inputSchema={"type": "object", "properties": {}}
        )
    ]
```

### 1.3 LLM 接入配置

**.env 文件**：
```bash
# llama.cpp OpenAI 兼容端点
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_KEY=dummy

# LiteLLM 模型配置
PAGEINDEX_MODEL=openai/qwen2.5-14b-instruct
```

**llama.cpp 启动命令**（参考）：
```bash
./server -m qwen2.5-14b-instruct-q4_k_m.gguf \
         --host 0.0.0.0 --port 8080 \
         --ctx-size 8192 \
         --chat-function-call
```

---

## 2. Architecture Decisions（架构决策）

### AD1：PageIndex 定位 — 补充引擎 vs 替换引擎

| 维度 | 补充引擎（选） | 替换引擎 |
|------|--------------|---------|
| basic-memory | 保留 | 废弃 |
| 73 条历史经验 | 保留原位 | 迁移 |
| 召回率 | 100%（basic-memory）+ 补充 | 85-95%（PageIndex） |
| 知识图谱 | 保留 | 丢失 |
| 写入能力 | 保留 | 丢失 |
| 改造风险 | 低（新增不改旧） | 高（迁移+重构） |

**决策**：补充引擎。保留 basic-memory 全部优势，PageIndex 仅作发现性搜索+长文档检索补充。

### AD2：双引擎协同方式 — 首选+补充 vs 并行查询

| 维度 | 首选+补充（选） | 并行查询 |
|------|--------------|---------|
| 调用次数 | 1-2 次（basic-memory 命中则不调 PageIndex） | 2 次（总是都调） |
| 延迟 | 低（basic-memory 快） | 高（等两个都返回） |
| 结果重复 | 少（首选命中就不调补充） | 多（需去重） |
| 资源占用 | 低 | 高 |

**决策**：首选+补充。basic-memory 召回率 100%，命中则不调 PageIndex，节省 LLM 调用。

### AD3：树索引生成方式 — 手动构造 vs PageIndex md_to_tree

| 维度 | 手动构造（选） | md_to_tree |
|------|--------------|-----------|
| 输入 | references/ 目录树 | 单个 md 文件 |
| 摘要来源 | _index.md 已有（覆盖率 90%） | LLM 生成 |
| LLM 依赖 | 无 | 有 |
| 多文件支持 | ✅ | ❌ |

**决策**：手动构造。references/ 是多文件目录树，_index.md 已有高质量摘要。

### AD4：数据存储 — JSON + git vs SQLite

**决策**：JSON + git。数据量小（58 节点约 30-50KB），版本管理价值高。basic-memory 的 SQLite 保留不动。

### AD5：basic-memory 数据处理 — 完全保留 vs 迁移合并

| 维度 | 完全保留（选） | 迁移合并 |
|------|--------------|---------|
| 风险 | 零 | 迁移丢失风险 |
| 双引擎协同 | basic-memory 搜索 + PageIndex 补充 | 仅 PageIndex |
| 工作量 | 零 | 高（73 条迁移） |

**决策**：完全保留不迁移。basic-memory 73 条经验保留原位，PageIndex 树索引指向 references/。

---

## 3. 双引擎分工矩阵（核心设计）

### 3.1 搜索场景分工

| 搜索场景 | 首选引擎 | 补充引擎 | 兜底 | 理由 |
|---------|---------|---------|------|------|
| **语义相似搜索**（"类似 maccms 的视频站"） | basic-memory hybrid | PageIndex | Grep | basic-memory 向量召回率 100% |
| **发现性探索**（"有什么加密相关经验"） | PageIndex 树导航 | basic-memory | Grep | PageIndex 目录树导航适合发现 |
| **精准定位老文档**（"找 maccms 那条经验"） | basic-memory metadata | PageIndex | Grep | basic-memory tags+metadata 精确 |
| **长文档章节检索**（"rhino-security.md 安全策略章节"） | PageIndex get_page_content | - | - | basic-memory 无章节检索能力 |
| **关系遍历**（"和 AES 加密关联的经验"） | basic-memory build_context | - | - | PageIndex 无图谱能力 |
| **执行证据查询**（"91dasj 的执行日志"） | basic-memory metadata | PageIndex | Grep | basic-memory tags 精确 |

### 3.2 写入场景分工

| 写入场景 | 引擎 | 理由 |
|---------|------|------|
| **新经验写入** | basic-memory write_note + references/ 编辑 | PageIndex 无写入能力 |
| **老经验优化** | basic-memory edit_note + references/ 编辑 | PageIndex 无写入能力 |
| **树索引更新** | PageIndex update_tree_index | references/ 变更后同步树索引 |

### 3.3 Phase 流程分工

| Phase | basic-memory 职责 | PageIndex 职责 |
|-------|------------------|---------------|
| **Phase 1 经验搜索** | search_notes(hybrid) 首选 | search_experience 补充 |
| **Phase 3 测试验证** | write_note 执行证据 | update_tree_index（如有新经验） |
| **Phase 5 经验反哺** | write_note/edit_note 索引层 | update_tree_index 树索引 |
| **审计** | search_notes(tags) 精确查询 | search_experience 补充 |

---

## 4. Data Flow（数据流）

### 4.1 双引擎协同搜索流（Phase 1）

```
Skill Phase 1 调用 search_experience_smart(query)
    │
    ├─ Step 1: basic-memory search_notes(hybrid)
    │   ├─ 查询 basic-memory 向量索引
    │   ├─ 命中（召回率 ≥85%）→ 返回结果
    │   └─ 未命中或召回率低 → 进入 Step 2
    │
    ├─ Step 2: PageIndex search_experience
    │   ├─ 加载 tree-index.json
    │   ├─ LLM Agent 读取树结构
    │   ├─ 推理导航到相关节点
    │   ├─ 调用 get_file_content 读取内容
    │   ├─ 命中 → 合并 basic-memory 结果（去重）→ 返回
    │   └─ 仍未命中 → 进入 Step 3
    │
    └─ Step 3: Grep references/ 兜底
        └─ 关键词匹配，返回结果
```

### 4.2 长文档章节检索流

```
AI 需要查看长文档具体章节
    │
    ├─ 调用 mcp_pageindex_get_experience_detail(file_path, line_range)
    │
    ▼
PageIndex MCP Server
    │
    ├─ get_page_content(file_path, line_range)
    ├─ 按行号区间读取文件内容
    │
    ▼
返回指定章节内容（非整篇文档）
```

### 4.3 经验反哺流（Phase 5，精准定位老文档优化）

```
书源创建完成 → Skill 执行 Phase 5
    │
    ├─ Step 1: 精准定位老文档
    │   ├─ basic-memory search_notes(tags=["xxx"], metadata_filters={...})
    │   │   → 精确命中已知经验笔记
    │   └─ 获取 source_doc 指针 → references/ 对应 md 文件
    │
    ├─ Step 2: 优化修改老文档
    │   ├─ 编辑 references/ 对应 md 文件（权威源）
    │   ├─ basic-memory edit_note 同步更新索引层
    │   └─ PageIndex update_tree_index 增量更新树索引
    │
    └─ Step 3: 新经验写入（如果是新经验）
        ├─ references/ 新建 md 文件
        ├─ basic-memory write_note 写入索引层
        └─ PageIndex update_tree_index 增量更新
```

### 4.4 三级降级流

```
search_experience_smart 调用
    │
    ├─ basic-memory 可用？
    │   ├─ 否 → 跳过 Step 1，进入 PageIndex
    │   └─ 是 → 执行 search_notes
    │
    ├─ PageIndex LLM 可用？
    │   ├─ 否 → 跳过 Step 2，进入 Grep
    │   └─ 是 → 执行 search_experience
    │
    └─ Grep 兜底
        └─ 关键词匹配 references/
```

---

## 5. File Changes（文件变更）

### 5.1 新增文件

| 文件路径 | 行数预估 | 用途 |
|---------|---------|------|
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/build_tree_index.py` | ~200 | 目录树索引生成器 |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/retrieve_patched.py` | ~150 | 改造版 retrieve.py |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/search_experience.py` | ~120 | PageIndex LLM 树导航搜索 |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/search_experience_smart.py` | ~100 | 双引擎协同封装（核心创新） |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/pageindex_mcp_server.py` | ~100 | 本地 MCP Server |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/config.yaml` | ~30 | LLM + 索引配置 |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/.env.example` | ~10 | 环境变量示例 |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/tree-index.json` | ~自动生成 | 树索引数据 |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/requirements.txt` | ~10 | Python 依赖 |
| `.trae/skills/legado-source-creator/scripts/pageindex-engine/README.md` | ~80 | 引擎使用说明 |

### 5.2 修改文件（增强，非替换）

| 文件路径 | 修改量 | 修改内容 | 性质 |
|---------|--------|---------|------|
| `.trae/skills/legado-source-creator/SKILL.md` | 中（~15 处） | 新增 PageIndex 补充搜索流程、双引擎协同说明、长文档检索用法 | **增强** |
| `.trae/skills/legado-source-creator/AI_README.md` | 小（~8 处） | 新增 PageIndex 操作指南 | **增强** |
| `.trae/skills/legado-workflow-auditor/SKILL.md` | 小（~5 处） | 新增 PageIndex 补充搜索步骤 | **增强** |
| `AGENTS.md` | 小（~3 处） | Phase 完成标志新增 PageIndex 状态 | **增强** |
| `docs/INDEX.md` | 小（~1 处） | 状态更新 | **更新** |

### 5.3 不修改的文件（保留）

| 文件路径 | 说明 |
|---------|------|
| **basic-memory MCP 配置** | 完全保留，不修改 |
| **basic-memory project=legado 数据** | 73 条经验保留原位，不迁移 |
| **references/ 现有 md 文件** | 权威源不变，仅可能新增内容 |
| **现有 basic-memory 调用点** | search_notes/write_note/edit_note 全部保留 |

---

## 6. 对比分析：单引擎 vs 双引擎

### 6.1 功能维度对比

| 功能 | 单引擎（basic-memory） | 双引擎（basic-memory + PageIndex） | 评估 |
|------|---------------------|--------------------------------|------|
| **向量语义搜索** | ✅ hybrid 召回率 100% | ✅ 保留 | 持平 |
| **知识图谱** | ✅ build_context | ✅ 保留 | 持平 |
| **metadata 精确定位** | ✅ tags+metadata_filters | ✅ 保留 | 持平 |
| **经验写入** | ✅ write_note/edit_note | ✅ 保留 | 持平 |
| **发现性搜索** | ❌ 弱（扁平笔记） | ✅ PageIndex 树导航 | **增强** |
| **长文档章节检索** | ❌ 返回整篇 | ✅ get_page_content | **增强** |
| **目录树浏览** | ❌ 无 | ✅ get_document_structure | **增强** |
| **降级路径** | 二级（basic-memory → Grep） | 三级（basic-memory → PageIndex → Grep） | **增强** |

### 6.2 非功能维度对比

| 维度 | 单引擎 | 双引擎 | 评估 |
|------|--------|--------|------|
| **召回率** | 100% | ≥95%（双引擎协同） | 持平 |
| **发现性搜索** | 弱 | 强 | **增强** |
| **长文档检索** | 无 | 有 | **增强** |
| **协议合规** | AGPL-3.0 | AGPL + MIT 混合 | **改善** |
| **本地化** | 部分（需 MCP 服务端） | 增强（PageIndex 完全本地） | **增强** |
| **部署复杂度** | 中（1 个 MCP） | 高（2 个 MCP） | ⚠️ 略增 |
| **调用复杂度** | 低（直接调） | 中（需协同封装） | ⚠️ 略增 |

### 6.3 综合评估

**双引擎方案优势**：
1. ✅ 保留 basic-memory 全部优势（召回率 100%、图谱、写入）
2. ✅ 新增 PageIndex 发现性搜索能力
3. ✅ 新增长文档章节检索能力
4. ✅ 三级降级路径更健壮
5. ✅ 协议合规改善（MIT 补充）
6. ✅ 本地化增强

**双引擎方案代价**：
1. ⚠️ 部署复杂度增加（2 个 MCP 服务）
2. ⚠️ 调用复杂度增加（需协同封装）
3. ⚠️ 需维护两套索引（basic-memory SQLite + PageIndex JSON）

**结论**：双引擎方案在**功能覆盖、降级健壮性、协议合规**维度全面优于单引擎；在**部署/调用复杂度**维度略增代价。整体适合"功能优先、覆盖全场景"的需求。

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 双引擎调用复杂度增加 | 中 | 中 | 封装 search_experience_smart() 统一入口，自动路由 |
| PageIndex 树导航召回率不稳定 | 中 | 低 | basic-memory 兜底，双引擎互补 |
| function-calling 模型能力不足 | 中 | 中 | Qwen2.5-14B 已验证；降级逐层选择 |
| 两套索引一致性 | 中 | 中 | references/ 为权威源，basic-memory 和 PageIndex 都指向它 |
| llama.cpp 服务未启动 | 中 | 低 | 自动降级 Grep，basic-memory 仍可用 |

---

## 8. 回滚方案

若双引擎方案验证失败，回滚步骤：

1. **basic-memory 完全保留**：双引擎期间 basic-memory 调用点零改动
2. **回滚触发条件**：
   - PageIndex 树导航召回率 <70%
   - 双引擎协同封装有严重 bug
   - llama.cpp 资源占用过高
3. **回滚操作**：
   - 删除 `pageindex-engine/` 目录
   - 恢复 SKILL.md 中 PageIndex 相关新增内容（git revert）
   - basic-memory 配置和数据未改动，直接可用
