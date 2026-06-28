# PageIndex + basic-memory 双引擎经验搜索增强

> **状态**：🔄 设计中
> **创建日期**：2026-06-18
> **最后更新**：2026-06-18
> **优先级**：P1

***

## 功能概述

在 `legado-source-creator` Skill 现有 basic-memory 经验引擎基础上，**新增 PageIndex 树导航作为补充引擎**，形成"双引擎协同"架构，让 AI 在开发书源/订阅源时能**快速、精准**搜索经验文档，且能**精准定位老文档进行优化修改**。

**核心定位：补充而非替换，协同而非替代**

```
┌─────────────────────────────────────────────────────────┐
│              双引擎协同经验搜索架构                        │
├─────────────────────────────────────────────────────────┤
│  basic-memory（保留）     +    PageIndex（新增）          │
│  ─────────────────       ──────────────────              │
│  • 向量语义搜索（hybrid）  • LLM 树导航（发现性探索）       │
│  • 知识图谱关系遍历       • 长文档内章节精准检索            │
│  • metadata 精确定位     • 目录层级浏览                   │
│  • 73条历史经验存量       • MIT 协议、本地化               │
│  • 经验写入+索引          • 树索引 JSON 可 git            │
└─────────────────────────────────────────────────────────┘
```

**不是替换 basic-memory**，而是：

* ✅ **保留**：basic-memory 全部功能（搜索/写入/图谱/元数据）

* ✅ **新增**：PageIndex 树导航作为"发现性搜索"补充

* ✅ **增强**：双引擎协同，覆盖更多搜索场景

* ✅ **不迁移**：basic-memory 73 条历史经验保留原位

***

## 背景与动机

### 当前痛点（单引擎 basic-memory 的局限）

| 痛点            | 场景                                       | 影响                           |
| ------------- | ---------------------------------------- | ---------------------------- |
| **发现性搜索弱**    | AI 不知道有什么经验，需"按主题浏览"                     | basic-memory 是扁平笔记集合，无目录层级导航 |
| **长文档内检索难**   | 经验文档很长（如 rhino-security.md 555行），需定位具体章节 | basic-memory 返回整篇笔记，AI 需自行扫描 |
| **无目录树视图**    | AI 想看 references/ 整体结构，按目录层级探索           | basic-memory 无目录树概念          |
| **AGPL 协议隐患** | 商用场景受限                                   | basic-memory 是 AGPL-3.0      |

### PageIndex 的补充价值

| 补充点          | 说明                                                               |
| ------------ | ---------------------------------------------------------------- |
| **目录树导航**    | references/ 是天然树结构（58 md、3 层、6 大子目录），PageIndex LLM 推理导航适合"发现性探索" |
| **长文档章节检索**  | PageIndex 的 `get_page_content` 可精准定位文档内行号区间                      |
| **MIT 协议**   | 商用友好，作为补充工具无合规风险                                                 |
| **本地化**      | Python + llama.cpp，无云端依赖                                         |
| **树索引可 git** | JSON 文件可纳入版本管理                                                   |

### 两者各自优势（不冲突，互补）

| 维度    | basic-memory 优势  | PageIndex 优势 |
| ----- | ---------------- | ------------ |
| 搜索类型  | 语义相似（向量）         | 推理发现（树导航）    |
| 定位精度  | tags+metadata 精确 | 目录路径+行号精确    |
| 关联发现  | 知识图谱关系遍历         | 目录层级关联       |
| 文档内检索 | ❌ 返回整篇           | ✅ 章节级定位      |
| 写入能力  | ✅ write\_note    | ❌ 仅读         |
| 协议    | AGPL-3.0         | MIT          |

***

## 核心能力

| 能力                | 引擎           | 说明                               |
| ----------------- | ------------ | -------------------------------- |
| **向量语义搜索**        | basic-memory | search\_notes(hybrid) 召回率 100%   |
| **知识图谱遍历**        | basic-memory | build\_context 关系发现              |
| **metadata 精确定位** | basic-memory | tags+metadata\_filters 查询已知文档    |
| **经验写入+索引**       | basic-memory | write\_note + edit\_note 双写      |
| **LLM 树导航搜索**     | PageIndex    | LLM 在目录树上推理发现相关文档                |
| **长文档章节检索**       | PageIndex    | get\_page\_content 精准定位文档内行号区间   |
| **目录树浏览**         | PageIndex    | get\_document\_structure 返回整体目录树 |
| **双引擎协同**         | 两者           | 分工协作，覆盖全场景                       |

***

## 双引擎协同工作流（核心设计）

### Phase 1 经验搜索（增强版）

```
AI 执行 Phase 1 经验搜索
│
├─ Step 1: basic-memory 向量语义搜索（首选，召回率高）
│   └─ search_notes(query, search_type="hybrid", project="legado")
│       ├─ 命中（召回率 ≥85%）→ 返回结果，结束
│       └─ 未命中或召回率低 → 进入 Step 2
│
├─ Step 2: PageIndex 树导航（补充，发现性探索）
│   └─ search_experience(query)
│       ├─ LLM 读取 references/ 目录树
│       ├─ 推理导航到相关目录/文件
│       ├─ 命中 → 返回文件路径+内容片段，结束
│       └─ 仍未命中 → 进入 Step 3
│
└─ Step 3: Grep references/ 兜底（最终降级）
    └─ 关键词匹配，返回结果
```

### Phase 5 经验反哺（增强版，精准定位老文档）

```
AI 执行 Phase 5 经验反哺
│
├─ Step 1: 精准定位老文档（要优化修改）
│   ├─ basic-memory search_notes(tags=["xxx"], metadata_filters={...})
│   │   → 精确命中已知经验文档
│   └─ 或 PageIndex 树导航定位到具体文件
│       → 按目录路径定位
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

### 审计者搜索执行证据（增强版）

```
legado-workflow-auditor Skill 执行审计
│
├─ Step 1: basic-memory 精确查询（首选）
│   └─ search_notes(tags=["execution-log"], metadata_filters={source_name: "xxx"})
│       → 精确命中执行证据
│
└─ Step 2: PageIndex 树导航（补充）
    └─ search_experience("执行证据: xxx")
        → LLM 导航到 execution-logs/ 目录
```

***

## 文档索引

| 文档                       | 内容                                           |
| ------------------------ | -------------------------------------------- |
| [spec.md](./spec.md)     | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 双引擎协同架构/分工矩阵/数据流/File Changes/对比分析           |
| [tasks.md](./tasks.md)   | 分组任务清单                                       |

***

## 关键决策点（待用户审核确认）

| # | 决策点               | 推荐方案                                      | 备选         |
| - | ----------------- | ----------------------------------------- | ---------- |
| 1 | PageIndex 定位      | 补充引擎（发现性搜索+长文档检索）                         | 独立引擎       |
| 2 | 双引擎协同方式           | basic-memory 首选 + PageIndex 补充            | 并行查询       |
| 3 | 数据存储              | references/ 权威源不变，PageIndex 树索引 JSON 新增   | -          |
| 4 | 本地 LLM 模型         | Qwen2.5-14B-Instruct（支持 function-calling） | Qwen2.5-7B |
| 5 | PageIndex 部署形态    | 本地 Python + 本地 MCP Server                 | 仅命令行       |
| 6 | basic-memory 是否保留 | ✅ 完全保留，不迁移数据                              | -          |

***

## 预期收益

| 指标      | 当前（单引擎）            | 目标（双引擎）                       | 改善      |
| ------- | ------------------ | ----------------------------- | ------- |
| 经验搜索召回率 | 100%（basic-memory） | ≥95%（双引擎协同）                   | ✅ 持平或略增 |
| 发现性搜索能力 | ❌ 弱（扁平笔记）          | ✅ 强（树导航）                      | ✅ 新增    |
| 长文档章节检索 | ❌ 无                | ✅ 有（get\_page\_content）       | ✅ 新增    |
| 目录树浏览   | ❌ 无                | ✅ 有（get\_document\_structure） | ✅ 新增    |
| 精准定位老文档 | ✅ 有（metadata）      | ✅ 有（metadata + 树路径）           | ✅ 增强    |
| 协议合规    | AGPL-3.0           | AGPL + MIT 混合                 | ✅ 改善    |
| 本地化     | 部分（需 MCP 服务端）      | 增强（PageIndex 完全本地）            | ✅ 增强    |

***

## 风险摘要

| 风险                    | 严重度  | 缓解措施                                  |
| --------------------- | ---- | ------------------------------------- |
| 双引擎调用复杂度增加            | 🟡 中 | 封装统一 search\_experience\_smart() 自动路由 |
| PageIndex 树导航召回率不稳定   | 🟡 中 | basic-memory 兜底，双引擎互补                 |
| function-calling 模型要求 | 🟡 中 | Qwen2.5-14B 已验证；降级逐层选择                |
| 改造工作量 \~250 行代码       | 🟢 低 | 仅新增 PageIndex 引擎，不改 basic-memory      |

