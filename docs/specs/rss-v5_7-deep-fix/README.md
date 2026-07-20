# RSS订阅源 V5.7 深度修复

> **OpenSpec 设计文档** — V5.6 交付后的真机验证发现严重问题，需在 V5.7 阶段彻底修复 13 个启用源的字段规则，并尝试恢复部分禁用源。

> **状态**: 🔄 设计中 → ✅ 设计完成（2026-07-20 审核修订后）
>
> **审核记录**: [audit_report.md](./audit_report.md) — 6 项阻断级问题已修订

---

## 1. 项目背景

### 1.1 V5.1 → V5.6 演进历史

| 阶段 | 源数 | 完全通过 | 通过率 | 关键动作 |
|------|------|----------|--------|----------|
| V5.1 | 328 | 7/35 | 20% | 字段类型修复（Gson 严格解析） |
| V5.2 | 224 | 1/20 | 5% | 移除 104 失效拆分子源 |
| V5.3 | 224 | 1/71 | 1.4% | App 内置 5 维度调试验证发现 |
| V5.4 | 184 | 2/21 | 9.5% | 清理 40 不可恢复源 + 修复 29 |
| V5.5 | 184 | 1/20 | 5% | Cronet 差异瓶颈 |
| V5.6 | 184 | 1/3 抽验 | 33% | 单源深度修复工作流验证可行 |
| **V5.7** | **184** | **1/13 启用源** | **7.7%** | **字段补齐 100% + 真机 5 维度验证** |

### 1.2 用户两次严重批评（2026-07-20）

1. **第一次批评**："184个订阅源，为什么那么多被禁用的？"
2. **第二次批评**："每一个订阅源的名称、源URL、图标、搜索地址、分类URL、列表规则、列表下一页规则、标题规则、时间规则、图片URL规则、链接规则、WEB_VIEW 中的内容规则，这些都是必不可少的，为什么你搞的很多订阅源，丢三落四！你确定你认认真真的优化测试了么？"

### 1.3 V5.7 阶段1成果

- 字段填充率从 47-99% 提升到 **100%**
- 13 个启用源共补 34 个字段（18 提取值 + 16 通用默认值）
- 输出文件：`output/rss/optimized_v5_7_final.json`

### 1.4 V5.7 阶段2成果

- 真机 5 维度验证：**1/13 完全通过**（源[81]）
- 关键认知：**字段填充 100% ≠ 真机可用 100%**
- 字段补齐只是"有规则"，但规则是否匹配真实 DOM 结构、能否被 Legado 规则引擎正确解析，必须真机验证

---

## 2. 项目目标

### 2.1 核心目标

将 V5.7 的 184 源全部修复到以下状态：
1. **12 必备字段全部填充**（100% 填充率，ruleContent 可为空）
2. **App 内置 5 维度真机调试全部通过**（domain/list/search/category/content）
3. **能登录的源模拟跳过登录**
4. **视频源点进列表后能正常查看播放**

### 2.2 子目标

| 子目标 | 描述 | 优先级 |
|--------|------|--------|
| 修复 13 个启用源 | 将 13 个补齐字段后的启用源修复到 5 维度通过 | P0 |
| 恢复 CF 盾源 | 用 google cache 串行方式破盾 15 个 CF 盾源 | P1 |
| 恢复 timeout 源 | 重试 7 个 timeout 源 | P1 |
| 全量验证 | 184 源全量 5 维度真机验证 | P0 |
| 经验沉淀 | 陷阱 68-72 沉淀到 skill 文档 | P1 |

---

## 3. 核心约束

### 3.1 12 必备字段清单（用户明确要求）

> **说明**: 用户要求"11 必备字段"，但实际列出 12 项。本规范统一为 **12 必备字段**，其中 `ruleContent` 可为空（缺省时 content 维度自动 skip，符合 REQ-8 通过标准）。

| # | 字段名 | 中文名 | 必填性 | 说明 |
|---|--------|--------|--------|------|
| 1 | sourceName | 源名称 | MUST | 必填 |
| 2 | sourceUrl | 源URL | MUST | 必填 |
| 3 | sourceIcon | 图标 | MUST | 必填 |
| 4 | searchUrl | 搜索地址 | MUST | 必填 |
| 5 | sortUrl | 分类URL | MUST | 必填 |
| 6 | ruleArticles | 列表规则 | MUST | 必填 |
| 7 | ruleNextPage | 列表下一页规则 | MUST | 必填 |
| 8 | ruleTitle | 标题规则 | MUST | 必填 |
| 9 | rulePubDate | 时间规则 | MUST | 必填 |
| 10 | ruleImage | 图片URL规则 | MUST | 必填 |
| 11 | ruleLink | 链接规则 | MUST | 必填 |
| 12 | ruleContent | WEB_VIEW内容规则 | SHOULD | 可为空，缺省时 content=skip 可通过 |

> 注：sourceName/sourceUrl 在 V5.6 已 100% 填充，V5.7 重点补齐其余 10 字段。

### 3.2 真机验证标准

使用 Legado App 内置调试功能（CheckRssSourceService.kt）5 维度校验：
- **domain**: 域名访问是否成功
- **list**: 列表是否解析出内容
- **search**: 搜索功能是否可用
- **category**: 分类是否可用
- **content**: 正文是否可解析

**唯一可信验证标准**：PC Playwright 验证 ≠ 真机 Cronet 验证（关键教训）。

### 3.3 单源深度修复工作流（V5.6 验证可行）

```
1. 选定 1 源 → 模拟器 App 内置调试看错误
2. mitmproxy 抓包真机 App Cronet 实际请求
3. 分析真实 HTML 结构
4. 重写规则（12 必备字段全部填充，ruleContent 可为空）
5. 5 维度真机调试验证（domain/list/search/category/content）
6. 失败回到分析（最多 3 次）→ 通过后下一个
```

---

## 4. 关键文件路径

### 4.1 输入文件

| 文件 | 说明 |
|------|------|
| `output/rss/optimized_v5_6_final.json` | V5.6 最终交付版（184源，备份在 `.bak_v5_7`） |
| `output/rss/optimized_v5_7_final.json` | V5.7 字段补齐版（184源，字段填充率100%） |
| `output/rss/v5_7_field_suggestions_v2.json` | V5.7 字段提取建议（13源） |
| `output/rss/v5_7_debug_verify_result.json` | V5.7 阶段2 5维度真机验证结果 |
| `output/rss/v5_7_debug_verify_report.md` | V5.7 阶段2 验证报告 |
| `output/rss/v5_7_debug_logs/src_*_category.log` | 13 源分类维度 logcat 日志 |
| `output/rss/v5_7_debug_logs/src_*_search.log` | 13 源搜索维度 logcat 日志 |
| `output/rss/v5_7_debug_shots/` | 13 源调试截图 |

### 4.2 统计/诊断脚本

| 脚本 | 用途 |
|------|------|
| `output/rss/v5_6_disabled_stats.py` | 统计禁用源原因分布 |
| `output/rss/v5_6_field_fill_rate.py` | 统计 11 必备字段填充率 |
| `ai_tests/scripts/v5_7_fix_missing_fields_v2.py` | 智能提取缺字段（Playwright） |
| `ai_tests/scripts/v5_7_apply_patches.py` | 应用字段补丁到 JSON |
| `ai_tests/scripts/v5_7_debug_verify.py` | 5 维度真机验证脚本 |

### 4.3 核心源码

| 文件 | 说明 |
|------|------|
| `app/src/main/java/io/legado/app/service/CheckRssSourceService.kt` | 5 维度校验核心服务 |
| `app/src/main/java/io/legado/app/model/CheckRssSource.kt` | RssSource 校验逻辑 |
| `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt` | 调试入口（L181-L185） |

### 4.4 skill 文档

| 文件 | 说明 |
|------|------|
| `.trae/skills/legado-source-creator/references/source-analysis/batch-optimization-patterns.md` | 陷阱1-67已沉淀 |
| `.trae/skills/legado-source-creator/SKILL.md` | skill 主文档（5阶段闭环+79条陷阱） |

### 4.5 历史报告

- `output/rss/v5_5_final_report.md` - V5.5 最终报告（含 Cronet 配置分析）
- `output/rss/v5_6_single_source_workflow.md` - V5.6 单源深度修复工作流
- `docs/specs/rss-batch-optimize-v2/v5_optimization_final_report.md` - V5 最终成果报告

---

## 5. OpenSpec 四文档索引

| 文档 | 内容 |
|------|------|
| [README.md](./README.md) | 本文档（项目概述+背景+目标+约束） |
| [spec.md](./spec.md) | 功能需求规格（必须做什么） |
| [design.md](./design.md) | 技术设计（怎么做+失败原因明细） |
| [tasks.md](./tasks.md) | 任务分解（实施步骤+验收标准） |

---

## 6. 测试环境

| 项 | 值 |
|---|---|
| 模拟器 | MEmu 127.0.0.1:21503 |
| App 包名 | io.legado.app.debug |
| ADB 路径 | D:\Program Files\Microvirt\MEmu\adb.exe |
| Python venv | ai_tests/venv/Scripts/python.exe |
| Cronet 状态 | ❌ 未下载（用 OkHttp fallback） |

---

**生成时间**: 2026-07-20
**最后修订**: 2026-07-20（审核修订：6 项阻断级问题已修复）
**当前任务状态**: V5.7 阶段2 完成（1/13 通过），设计文档已审核修订，等待新窗口接手阶段3 深度修复
