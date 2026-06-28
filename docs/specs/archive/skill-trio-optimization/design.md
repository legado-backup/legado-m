# Design: Skill Trio 优化 — AI 友好度提升

---

## 1. Technical Approach（技术方案）

### 1.1 总体架构

本次优化**不改变**现有的金字塔架构（L1-L4），而是优化各层内容的**呈现方式**和**AI 可执行性**：

```
L1: SKILL.md（精简版，<500行）
  ↓ 精简后保留：决策树 + 速查表 + Phase 流程 + 完成标志
  ↓ 移除到 L2：详细解释、完整函数列表、长篇示例
L2: references/（按需查阅）
  ↓ 新增：未实现函数速查表、MVP 选择决策树详情
L3: basic-memory（简化双写）
  ↓ 3步流程：判断类型 → 写Skill文档 → 写memory
  ↓ 统一 metadata 字段集
L4: 源码（不变）
```

### 1.2 三阶段实施策略

```
阶段一：修断路（P0）
  ├─ 1.1 workflow-auditor 字段对齐
  ├─ 1.2 MockJsExtensions 签名修复
  ├─ 1.3 陷阱数量统一
  └─ 1.4 @. 前缀验证清理

阶段二：铺快车道（P1）
  ├─ 2.1 SKILL.md 精简重构
  ├─ 2.2 决策树嵌入（MVP选择 + 脚本选择 + Phase失败标准）
  ├─ 2.3 basic-memory 双写简化
  ├─ 2.4 skill-auditor 分层审查
  └─ 2.5 自动化检测脚本

阶段三：装红绿灯（P2）
  ├─ 3.1 全局触发词表
  ├─ 3.2 调用链路图
  ├─ 3.3 统一降级路径模式
  ├─ 3.4 审计报告格式简化
  └─ 3.5 workflow-auditor 关系说明补充
```

---

## 2. Architecture Decisions（架构决策）

### AD-1: SKILL.md 精简策略 — "拆分而非删除"

**决策**：将 source-creator SKILL.md 从 669 行精简到 <500 行，采用"拆分到 L2"而非"删除内容"。

**理由**：
- 删除内容会丢失信息，AI 需要时无法查阅
- 拆分到 references/ 子文档，AI 按需读取，减少主文档上下文占用
- 符合金字塔架构设计

**拆分清单**：

| 当前位置 | 内容 | 拆分目标 |
|---------|------|---------|
| SKILL.md L117-263 | basic-memory 完整操作规范 | references/basic-memory-usage.md（新建） |
| SKILL.md L266-368 | JVM 测试基础设施详情 | references/jvm-infrastructure.md（新建） |
| SKILL.md L531-571 | 代码进化机制详情 | references/code-evolution.md（新建） |
| SKILL.md L583-594 | 订阅源核心差异详情 | references/special-scenarios/rss-core-diff.md（已有目录） |

**SKILL.md 保留内容**（精简后）：
- 触发条件 + 源类型快速决策
- 陷阱速查表（精选高频项，标注"完整79条详见 references/troubleshooting/"）
- 5 阶段工作流（精简版，每阶段 <20 行）
- MVP 选择决策树（新增）
- 脚本选择决策树（新增）
- Phase 完成检查清单
- 参考文档索引表

**状态**：📋 待实施

### AD-2: MockJsExtensions 签名修复 — "对齐 Legado 源码"

**决策**：修复 6 个核心函数签名，补充 ~15 个高频缺失函数，明确标注 80+ 未实现函数。

**修复清单**：

| 函数 | 当前 Mock | 修复后 Mock | Legado 源码 |
|------|----------|------------|------------|
| ajax | `ajax(url: String): String` | `ajax(url: Any): String` | `ajax(url: Any): String?` |
| createSymmetricCrypto | 2 重载(String,String,String) | 4 重载(+ByteArray,ByteArray?) | 4 重载 |
| put | `put(key: String, value: Any?): String` | `put(key: String, value: String): String` | `put(key: String, value: String): String` |
| get | `get(key: String): Any?` | `get(key: String): String` | `get(key: String): String` |
| hexDecodeToString | `hexDecodeToString(hex: String): String` | `hexDecodeToString(utf8: String): String?` | `hexDecodeToString(utf8: String): String?` |
| ajaxAll | `ajaxAll(urls: Any?): String` | `ajaxAll(urlList: Array<String>): Array<StrResponse>` | 同左 |

**新增高频函数**（~15 个）：
- getVerificationCode, importScript, getCookie
- downloadFile, readFile, readTxtFile
- strToBytes, bytesToStr, base64DecodeToByteArray
- connect, get, post, head
- queryTTF, replaceFont

**未实现函数标注**：在 SKILL.md 增加"MockJsExtensions 未实现函数速查表"章节，按类别列出，标注影响和建议处理方式。

**状态**：📋 待实施

### AD-3: workflow-auditor 字段对齐 — "统一执行证据数据模型"

**决策**：在 source-creator 的执行证据 write_note 模板中增加 workflow-auditor 需要的字段。

**统一后的执行证据 metadata 字段集**：

```python
# Phase 1 执行证据
metadata = {
    "source_name": "{源名称}",
    "phase": "1",
    "basic_memory_search": "命中/未命中/降级",  # 已有
    "trap_check": "已检查/未检查",              # 新增
    "cms_type": "{检测到的CMS类型或none}",      # 新增
    "cf_detected": "true/false"                 # 新增
}

# Phase 3 执行证据
metadata = {
    "source_name": "{源名称}",
    "phase": "3",
    "test_coverage": "{X%}",                   # 已有
    "confidence_high": "{N}",                   # 已有
    "confidence_medium": "{N}",                 # 已有
    "confidence_low": "{N}",                    # 已有
    "confidence_unverifiable": "{N}",           # 新增
    "jvm_evolution_needed": "true/false",       # 新增（替代 tags 检测）
    "phase4_triggered": "true/false"            # 新增
}

# Phase 5 执行证据
metadata = {
    "source_name": "{源名称}",
    "phase": "5",
    "dual_write": "完成/部分完成/失败",          # 新增
    "sync_status": "synced/pending/conflict",   # 新增
    "schema_validation": "通过/未通过",           # 新增
    "code_evolution_executed": "true/false/N/A" # 新增
}
```

**workflow-auditor 检查项更新**：

| 检查项 | 字段来源 | 失败处理 |
|--------|---------|---------|
| Phase 1 执行证据 | metadata.basic_memory_search | 标记 WARN，建议补写 |
| Phase 3 执行证据 | metadata.test_coverage | 标记 WARN，建议补写 |
| Phase 5 执行证据 | metadata.dual_write | 标记 WARN，建议补写 |
| 陷阱检查 | metadata.trap_check | 标记 WARN |
| 测试覆盖率 | metadata.test_coverage | 数值 > 0 |
| 经验反哺 | metadata.dual_write | ∈ {完成,部分完成} |
| 代码进化 | metadata.jvm_evolution_needed → metadata.code_evolution_executed | 如 needed=true 则必须 executed=true |
| Phase 完成标志 | 上下文搜索 [PHASEX_COMPLETE] | 3 个标志都存在 |

**状态**：📋 待实施

### AD-4: skill-auditor 分层审查 — "L1/L2/L3 三级"

**决策**：将 42 个检查点重组为 3 层，支持增量审查。

**分层方案**：

| 层级 | 检查项数 | 预估时间 | 内容 | 适用场景 |
|------|---------|---------|------|---------|
| **L1 快速** | 10 | 5分钟 | A1死链 + A4薄文件 + B5版本锁 + H1旧版源码 + H2临时脚本 + H4缓存 + C1语法 + C4 JAR存在 + S1模板 + S5输出 | 日常检查 |
| **L2 核心** | 15 | 20分钟 | A2跨文件 + A3数量 + B1-B4代码一致性 + C2-C3脚本 + D1-D2源码匹配 + E1-E2 memory + F1-F3新用户 | 定期审查 |
| **L3 深度** | 17 | 40分钟 | D3-D4字段定义 + E3-E4重复/目录 + G1-G3设计文档 + H3-H10债务 + S2-S4补充 | 发布前 |

**合并方案**（42 → ~30）：

| 合并后检查项 | 原检查项 | 理由 |
|-------------|---------|------|
| 代码一致性统一检查 | H8 + B1 + D1 | 都涉及 Kotlin 代码与文档/源码对比 |
| 文档一致性统一检查 | H9 + A4 + D3 + D4 | 都涉及文档内容与实际/源码对比 |
| memory 一致性检查 | H10 + E1 + E2 | 都涉及 basic-memory 笔记与文档对比 |
| 文件债务快速扫描 | H1 + H2 + H3 + H4 + H5 + H6 | 都是文件存在性检查，可批量 |

**状态**：📋 待实施

### AD-5: basic-memory 双写简化 — "7步→3步"

**决策**：将 Phase 5 反哺写入策略从 7 步简化为 3 步。

**当前 7 步**：
1. 判断经验类型 → 确定 note_type 和 directory
2. 先更新 Skill 文档
3. 检查 basic-memory 是否已有同类笔记
4. 找到 → edit_note append
5. 未找到 → write_note
6. 写入时包含元数据
7. 检查双写一致性

**简化后 3 步**：
1. **更新 Skill 文档**（references/ 下对应文件）
2. **写 basic-memory**（使用统一模板，自动包含元数据）
3. **标记 sync_status**（synced/pending/conflict）

**简化模板**：
```python
mcp_basic-memory_write_note(
    title="经验: {简短描述}",
    content="## 网站特征\n{描述}\n\n## 解决方案\n{方案}\n\n## 参考\n- {references路径}",
    directory="{note_type对应目录}",
    project="legado",
    note_type="{experience/pattern/trap/verification}",
    tags=["{技术栈}", "{网站类型}"],
    metadata={"source_doc": "references/{路径}", "sync_status": "synced"}
)
```

**状态**：📋 待实施

### AD-6: 决策树嵌入 — "替代自由判断"

**决策**：在 SKILL.md 中嵌入 3 个决策树，替代 AI 的自由判断。

**决策树 1：MVP 选择**
```
规则含 webView/webJs？
  ├─ 是 → 无法验证（标记需真机）
  └─ 否 → 规则含 <js> 或 @js:？
            ├─ 是 → 规则含加密解密？
            │       ├─ 是 → MVP4（完整AnalyzeRule+hutool）
            │       └─ 否 → MVP4（完整AnalyzeRule）
            └─ 否 → 规则含加密解密？
                    ├─ 是 → MVP3（+hutool加密）
                    └─ 否 → 规则纯 CSS？
                            ├─ 是 → MVP2（+jsoup CSS）
                            └─ 否 → MVP1（Rhino桥接）即可
不确定 → 始终用 MVP4（最高覆盖率）
```

**决策树 2：脚本选择**
```
必选：verify-source.py（源完整性）
  ↓
规则含 CSS 选择器？ → verify-selector.py
规则含加密？ → verify-decrypt.py
规则含图片？ → verify-image.py
需要全链路？ → debug-source.py
需要网站分析？ → analyze-site.py
```

**决策树 3：Phase 3 失败判定**
```
静态陷阱扫描发现 ES6 语法？ → 失败，进入 Phase 4
JVM 测试报错（TypeError/ClassCastException）？ → 失败，进入 Phase 4
可信度评估为"低"的规则超过 50%？ → 建议进入 Phase 4
CSS 选择器匹配 0 元素？ → 失败，进入 Phase 4
以上都不满足 → Phase 3 通过
```

**状态**：📋 待实施

### AD-7: 全局触发词表与调用链路

**决策**：建立三个 Skill 的全局触发词表和调用链路图。

**全局触发词表**（去重后）：

| 触发词 | 唯一归属 Skill | 说明 |
|--------|--------------|------|
| 创建书源/订阅源 | source-creator | 核心创建功能 |
| 修复/优化源 | source-creator | 修复流程 |
| 审查skill/优化skill | skill-auditor | skill 本身质量审查 |
| 全面审查/深度审查 | skill-auditor | 注意：需与"审计任务"区分 |
| 审计任务/任务后审计 | workflow-auditor | 单次任务执行证据审计 |
| skill质量检查/健康度 | skill-auditor | skill 诊断 |

**调用链路图**：
```
用户请求
  ├─ "创建/修复书源" → source-creator
  │     └─ 任务完成 → 自动调用 workflow-auditor（审计执行证据）
  │           └─ 审计失败 → 提示用户重新执行对应 Phase
  ├─ "审查skill" → skill-auditor
  │     └─ 发现 skill 问题 → 修复 → 回归验证
  └─ "审计任务" → workflow-auditor（手动触发）
```

**上下文传递规范**：
- source-creator → workflow-auditor：传递 `source_name` 和 `task_type`
- skill-auditor → source-creator：无直接传递（skill-auditor 修复后由用户决定是否重新创建源）

**状态**：📋 待实施

### AD-8: 自进化闭环架构 — "测试失败→自动进化→重新验证"

**决策**：建立三层进化闭环（经验层 + 客户端层 + 服务端层），测试失败时自动触发进化。

**进化闭环架构**：

```
┌─────────────────────────────────────────────────────────┐
│                   Skill 自进化闭环                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ 经验层     │  │ 客户端层   │  │ 服务端层   │           │
│  │(basic-mem)│  │(Python)   │  │(JVM/Kotlin)│          │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        │              │              │                  │
│        └──────────────┼──────────────┘                  │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │  进化触发器      │                        │
│              │ (测试失败分析)   │                        │
│              └────────┬────────┘                        │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │  分类进化需求     │                        │
│              ├─────────────────┤                        │
│              │ 经验缺失→写memory│                        │
│              │ Mock缺失→补函数  │                        │
│              │ 行为不一致→修源码│                        │
│              │ 脚本不足→强Python│                       │
│              └────────┬────────┘                        │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │  自动进化执行     │                        │
│              │ (备份→修改→重建)  │                        │
│              └────────┬────────┘                        │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │  重新验证        │                        │
│              │ (进化后重跑测试)  │                        │
│              └────────┬────────┘                        │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │  成果沉淀        │                        │
│              │ (写回三层+版本号) │                        │
│              └─────────────────┘                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**进化触发条件与分类**：

| 触发条件 | 分类 | 进化对象 | 进化动作 | 可进化性判断 |
|---------|------|---------|---------|------------|
| `TypeError: java.xxx is not a function` | Mock 函数缺失 | 服务端 | 读 Legado 源码 → **依赖分析** → 补 MinimalMockJsExtensions.kt → 重建 JAR | 依赖分析通过则进化，否则标记"需简化实现" |
| JVM 结果与预期不符（如 CSS 匹配 0 但真机有） | 行为不一致 | 服务端 | 对比 AnalyzeRule.kt → 修正 → 重建 JAR | 总是可进化 |
| 测试脚本无法验证某场景（如分页加载） | 脚本能力不足 | 客户端 | 增强 debug-source.py | 总是可进化 |
| 新网站特征（如新 CMS 类型） | 经验缺失 | 经验层 | 写 basic-memory + 更新 references/ | 总是可进化 |
| 加密方式不识别 | Mock 缺失 | 服务端 | 补 createSymmetricCrypto 重载 → 重建 JAR | 总是可进化 |
| CF 拦截未检测 | 脚本不足 | 客户端 | 增强 html_fetcher.py CF 检测 | 总是可进化 |
| JSONPath/CSS 语法错误 | 规则语法错误 | 规则层 | 分析语法错误 → 修正规则 | 总是可进化 |
| searchUrl 返回空/错误 | URL 模板错误 | 规则层 | 分析 URL 编码/参数 → 修正模板 | 总是可进化 |
| 选择器匹配 0 元素 | 选择器错误 | 规则层 | 分析页面结构 → 修正选择器 | 总是可进化 |
| 字段对应错误（如作者解析成简介） | 字段映射错误 | 规则层 | 分析字段映射 → 修正规则 | 总是可进化 |

**依赖分析实现**（服务端自动进化的关键步骤）：

```python
def analyze_function_dependency(func_name: str, source_code: str) -> DependencyAnalysis:
    """分析 Legado 源码中函数的依赖，判断是否可独立 Mock"""
    # 1. 提取函数签名和实现
    func_impl = extract_function(source_code, func_name)
    
    # 2. 分析依赖的类和对象
    dependencies = extract_dependencies(func_impl)
    # 例如：importScript 依赖 AppContext、ScriptEngine 等
    
    # 3. 判断可独立 Mock 性
    non_mockable_deps = [d for d in dependencies if d in NON_MOCKABLE_CLASSES]
    # NON_MOCKABLE_CLASSES = ["AppContext", "WebBook", "ChapterProvider", "BookProvider", ...]
    
    if not non_mockable_deps:
        return DependencyAnalysis(
            can_mock=True,
            action=f"直接复制实现到 MinimalMockJsExtensions.kt",
            dependencies=dependencies
        )
    else:
        return DependencyAnalysis(
            can_mock=False,
            action=f"标注'需简化实现'，依赖不可 Mock 的类: {non_mockable_deps}",
            dependencies=dependencies,
            non_mockable=non_mockable_deps
        )
```

**进化安全机制**：
1. 进化前备份：`cp legado-rule-engine-mvp4.jar legado-rule-engine-mvp4.jar.bak.{timestamp}`
2. 进化失败回滚：`cp legado-rule-engine-mvp4.jar.bak.{timestamp} legado-rule-engine-mvp4.jar`
3. 进化版本标记：JAR 文件名含版本号（如 `legado-rule-engine-mvp4-v2.1.jar`）
4. 进化日志：写入 basic-memory（note_type=experience, tags=["evolution"]）

**进化触发器实现**（嵌入 debug-source.py）：

```python
# 实际函数名: trigger_evolution（非 analyze_test_failure）
# 返回 dict（非 EvolutionNeed 对象），含 convergence 字段
def trigger_evolution(error_type, error_msg, stack_trace=''):
    """分析测试失败，输出进化需求 JSON。
    返回 dict: {type, target, action, source, convergence}"""
    etype, action, default_source = _classify(error_type, error_msg)
    target = _extract_target(error_msg, stack_trace)
    source = _extract_source(stack_trace, etype) or default_source

    # 收敛检查（4.6.7：嵌入收敛机制）
    convergence = {'same_error_count': 1, 'should_evolve': True, 'reason': ''}
    try:
        from evolution_convergence import check_evolution_allowed
        error_signature = f"{etype}:{target}"
        allowed, count, reason = check_evolution_allowed(error_signature)
        convergence['same_error_count'] = count
        convergence['should_evolve'] = allowed
        convergence['reason'] = reason
    except ImportError:
        convergence['reason'] = '收敛模块不可用，允许进化'

    return {'type': etype, 'target': target, 'action': action,
            'source': source, 'convergence': convergence}

# 根因分类映射（5类，非10类）：
# TypeError → mock_missing | ClassCastException → behavior_mismatch
# timeout/SocketTimeoutException → network_issue
# JSONPath/CSS/XPath error → rule_error | 其他 → experience_missing
```

**状态**：📋 待实施

### AD-9: 自进化全流程模拟器 — "基于 test-infra-upgrade 的进化集成层"

**决策**：本 Spec **不重复实现**全流程模拟器的基础能力（AnalyzeUrl 移植、debugBookSource/debugRssSource 端到端调试、CookieStore、MockJsExtensions 扩展、debug-source.py），这些由 `test-infra-upgrade` Spec 提供。本 Spec 在此基础上增加**自进化集成层**：网站类型检测、进化触发器嵌入、验证报告增强、速度度量。

**与 test-infra-upgrade 的分工**：

| 能力 | 归属 | 说明 |
|------|------|------|
| AnalyzeUrl 移植 | test-infra-upgrade L0 | URL 解析三步流水线 |
| 端到端 debugBookSource | test-infra-upgrade L1 | search→detail→toc→content 全链路 |
| 端到端 debugRssSource | test-infra-upgrade L2 | sort→content 全链路 |
| 增量日志输出 | test-infra-upgrade L3 | 真机级 `[mm:ss.SSS] ︾︽⇒┌└≡◇` 格式 |
| CookieStore 内存实现 | test-infra-upgrade L4 | 二级域名 Cookie 管理 |
| MockJsExtensions 扩展 | test-infra-upgrade L5 | 网络类+加密类函数补齐 |
| Book/BookSource 上下文注入 | test-infra-upgrade L6 | 13 个变量注入 |
| debug-source.py | test-infra-upgrade L7 | 替代 deep-verify.py |
| **网站类型检测+场景分类** | **本 Spec AD-9** | 登录/CF/验证码检测+可零干预/需配置/必须人工分类 |
| **进化触发器嵌入** | **本 Spec AD-9** | debug-source.py 失败时触发进化闭环 |
| **验证报告增强** | **本 Spec AD-9** | 增加进化记录+速度度量+网站类型标注 |
| **网络请求安全机制** | **本 Spec AD-9** | 频率控制+UA伪装+超时重试+请求日志 |
| **进化反馈循环** | **本 Spec AD-9** | 用户手机端反馈→basic-memory→下次更精准 |

**自进化集成层架构**（嵌入 test-infra-upgrade 的 debug-source.py）：

```
debug-source.py（test-infra-upgrade 提供）
  ├─ Step 0: 网站类型检测（本 Spec 新增，嵌入 debug-source.py 前置）
  │   ├─ 请求首页 → 检测登录表单/重定向 → 标记"需登录"
  │   ├─ 检测 CF 特征 → 标记"需 webView 配置"
  │   ├─ 检测验证码 → 标记"需人工"
  │   └─ 判断属于哪类场景（可零干预/需配置/必须人工）
  │       ├─ 可零干预 → 继续 test-infra-upgrade 的 Step 1-6
  │       ├─ 需配置 → 输出干预建议，停止模拟
  │       └─ 必须人工 → 输出干预建议，停止模拟
  │
  ├─ Step 1-6: 端到端调试（test-infra-upgrade 提供）
  │   ├─ search→detail→toc→content→review 全链路
  │   ├─ 真机级日志输出
  │   ├─ Cookie/Header 自动携带
  │   └─ 分页验证
  │
  ├─ Step 7: 可信度评估（本 Spec 增强）
  │   ├─ 每步标注可信度（高/中/低/不可验证）
  │   └─ 汇总全流程可信度
  │
  ├─ Step 8: 输出验证报告（本 Spec 增强）
  │   ├─ JSON 中增加 "_verified": true/false
  │   ├─ 验证报告（每步结果+模拟数据样本+网站类型+干预建议）
  │   ├─ 进化记录（如有）：触发原因+进化动作+结果
  │   └─ 速度度量：耗时+首次通过率
  │
  └─ 失败处理（本 Spec 新增）
      ├─ 触发进化触发器（AD-8）
      ├─ 进化收敛检查（AD-10）
      │   ├─ 通过 → 执行进化 → 重新运行 debug-source.py
      │   └─ 不通过 → 标记"需人工介入"
      └─ 进化成果沉淀（AD-8）
```

**网站类型检测实现**（site_type_detector.py，嵌入 debug-source.py Step 0）：

```python
def detect_site_type(url=None, html=None) -> dict:
    """检测网站类型，返回 JSON 格式结果。
    实际接口已从 detect_site_type(source_json) 改为 url=/html= 关键字参数。
    若仅提供 url，内部通过 safe_request 获取 HTML。"""
    
    # 优先级：CF > 验证码 > 登录（CF 页面可能也含登录词）
    cf_hits = _match_features(html, CF_FEATURES)
    captcha_hits = _match_features(html, CAPTCHA_FEATURES)
    login_hits = _match_features(html, LOGIN_FEATURES)
    
    # 1. 检测必须人工场景
    if login_hits:
        return {"site_type": "login_required", "scenario": "must_manual",
                "intervention_suggestion": "需人工登录获取 Cookie，不建议自动化测试",
                "detected_features": login_hits}
    
    if captcha_hits:
        return {"site_type": "captcha_required", "scenario": "must_manual",
                "intervention_suggestion": "需人工处理验证码，不建议自动化测试",
                "detected_features": captcha_hits}
    
    # 2. 检测需配置场景
    if cf_hits:
        return {"site_type": "cf_protected", "scenario": "needs_config",
                "intervention_suggestion": "需配置 webView 或 loginUrl，配置后可继续自动化测试",
                "detected_features": cf_hits}
    
    # 3. 默认可零干预
    return {"site_type": "normal", "scenario": "zero_intervention",
            "intervention_suggestion": "无需干预，可继续自动化测试",
            "detected_features": []}
```

**网络请求安全机制实现**（network_safety_interceptor.py，嵌入 site_type_detector._fetch_html，debug-source.py 引用说明）：

> **实施变更**：嵌入点从 RealHttpExecutor 改为 site_type_detector._fetch_html。debug-source.py 通过 RuleEngineClient 调用 JVM，不直接发 HTTP 请求，因此仅在 site_type_detector 获取 HTML 时使用 safe_request。

```python
# 实际实现为模块级函数（非类），提供 safe_request() 和 get_request_log()
_last_request_time = 0.0
_MIN_INTERVAL = 1.0   # 最小请求间隔(秒)
_RETRY_INTERVAL = 2.0  # 重试间隔(秒)

def safe_request(url, method="GET", headers=None, data=None, timeout=30, max_retries=3):
    """安全请求封装：频率控制 + UA伪装 + 超时重试 + 日志"""
    # 1. 频率控制：距上次请求 <1秒则等待
    # 2. UA伪装：随机选择 UA
    # 3. 超时重试：最多 max_retries 次，间隔 2 秒
    # 返回 {"status": int, "body": str, "url": str}
```

**验证报告增强实现**（嵌入 debug-source.py Step 8）：

```python
def build_enhanced_report(step_results, site_type, evolution_log, speed_metrics):
    """构建增强验证报告"""
    report = {
        "verified": all(s["passed"] for s in step_results),
        "steps": step_results,
        "site_type": site_type.category,
        "intervention": site_type.intervention,
        "confidence": calculate_overall_confidence(step_results),
        "evolution_log": evolution_log,  # 进化记录（如有）
        "speed_metrics": speed_metrics   # 速度度量
    }
    if report["verified"]:
        report["verified_at"] = datetime.now().isoformat()
    return report
```

**状态**：📋 待实施（依赖 test-infra-upgrade 完成）

### AD-10: 进化收敛机制 — "防止无限进化的护栏"

**决策**：建立 4 层收敛机制，防止进化死循环和过度进化。

**收敛机制架构**：

```
┌─────────────────────────────────────────────────────────┐
│                   进化收敛机制                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────┐ │
│  │ 1.次数上限     │  │ 2.收敛判断     │  │ 3.冲突检测  │ │
│  │ (同一问题≤3次) │  │ (精准度>90%    │  │ (版本管理)  │ │
│  │               │  │  降频,>95%    │  │            │ │
│  │               │  │  停止)        │  │            │ │
│  └───────┬───────┘  └───────┬───────┘  └─────┬──────┘ │
│          │                  │                 │        │
│          └──────────────────┼─────────────────┘        │
│                             │                          │
│                   ┌─────────▼──────────┐               │
│                   │ 4.死循环检测         │               │
│                   │ (24h内相同错误≥3次   │               │
│                   │  →终止+标记环境问题) │               │
│                   └────────────────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**收敛机制实现**（嵌入 evolution_trigger.py）：

```python
# 实际实现为模块级函数（非类），存储于 .evolution_history.json
_MAX_EVOLUTION_COUNT = 3          # 护栏1：同一错误签名最多进化次数
_DEAD_LOOP_WINDOW = 86400         # 护栏4：24小时窗口（秒）
_DEAD_LOOP_THRESHOLD = 3          # 护栏4：24h内相同错误重复次数阈值
_HIGH_ACCURACY_THRESHOLD = 0.90   # 护栏2：降频阈值
_STOP_ACCURACY_THRESHOLD = 0.95   # 护栏2：停止阈值

def check_evolution_allowed(signature, accuracy=0.0):
    """检查是否允许进化（护栏1+2+4），返回 (allowed, count, reason)"""
    # 1. 次数上限检查
    # 2. 死循环检测（24h内相同错误≥3次）
    # 3. 收敛判断（>95%停止，>90%降频每2次允许1次）
    return (allowed, count, reason)

def record_evolution(signature, target, trigger_reason, duration, result):
    """记录进化日志（4.6.6），写入 .evolution_history.json"""

def check_conflict(function_name):
    """护栏3：冲突检测，同函数多次进化时归档旧版本"""

def get_stats():
    """获取进化统计：total/success/accuracy/recent_evolutions"""
```

**状态**：📋 待实施

### AD-11: 必须人工干预边界 — "零干预的极限"

**决策**：明确 3 类场景边界，避免 AI 无限尝试进化。

**场景分类与处理策略**：

| 场景类型 | 检测方法 | AI 处理策略 | 验证报告标注 |
|---------|---------|------------|------------|
| **可零干预** | 无登录表单、无 CF、无验证码 | 全流程模拟 → _verified:true | 网站类型="普通" |
| **需配置** | 检测到 CF 特征或网站结构变化 | 检测后提示用户配置，不自动通过 | 网站类型="需配置"，干预建议 |
| **必须人工** | 检测到登录表单或验证码 | 直接标记"需人工"，不尝试进化 | 网站类型="需人工"，干预建议 |

**场景检测实现**（嵌入 debug-source.py Step 0）：

```python
def detect_site_type(url=None, html=None) -> dict:
    """检测网站类型，返回 JSON 格式结果。
    实际接口已从 detect_site_type(source_json) 改为 url=/html= 关键字参数。
    若仅提供 url，内部通过 safe_request 获取 HTML。"""
    
    # 优先级：CF > 验证码 > 登录（CF 页面可能也含登录词）
    cf_hits = _match_features(html, CF_FEATURES)
    captcha_hits = _match_features(html, CAPTCHA_FEATURES)
    login_hits = _match_features(html, LOGIN_FEATURES)
    
    # 1. 检测必须人工场景
    if login_hits:
        return {"site_type": "login_required", "scenario": "must_manual",
                "intervention_suggestion": "需人工登录获取 Cookie，不建议自动化测试",
                "detected_features": login_hits}
    
    if captcha_hits:
        return {"site_type": "captcha_required", "scenario": "must_manual",
                "intervention_suggestion": "需人工处理验证码，不建议自动化测试",
                "detected_features": captcha_hits}
    
    # 2. 检测需配置场景
    if cf_hits:
        return {"site_type": "cf_protected", "scenario": "needs_config",
                "intervention_suggestion": "需配置 webView 或 loginUrl，配置后可继续自动化测试",
                "detected_features": cf_hits}
    
    # 3. 默认可零干预
    return {"site_type": "normal", "scenario": "zero_intervention",
            "intervention_suggestion": "无需干预，可继续自动化测试",
            "detected_features": []}
```

**状态**：📋 待实施

### AD-12: 自进化全流程模拟器 — "阶段四+五合并架构（基于 test-infra-upgrade）"

**决策**：将阶段四（自进化闭环）和阶段五（零人工干预测试）合并为"自进化全流程模拟器"，因为两者深度耦合。全流程模拟器的基础设施（AnalyzeUrl、debugBookSource、debugRssSource、CookieStore、MockJsExtensions、debug-source.py）由 `test-infra-upgrade` Spec 提供，本 Spec 仅在其上增加自进化集成层。

**合并理由**：
- 全流程模拟器失败时触发进化
- 进化后重新运行全流程模拟器
- 进化触发器嵌入全流程模拟器
- 两者共享网络请求、Cookie、错误分析等基础设施
- **基础设施依赖 test-infra-upgrade**，不重复实现

**合并后的架构**：

```
┌─────────────────────────────────────────────────────────────────┐
│              自进化全流程模拟器（基于 test-infra-upgrade）          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Step 0: 网站类型检测（本 Spec AD-9）                 │        │
│  │  ├─ 可零干预 → 继续全流程模拟                          │        │
│  │  ├─ 需配置 → 输出干预建议，停止模拟                    │        │
│  │  └─ 必须人工 → 输出干预建议，停止模拟                  │        │
│  └───────────────────────┬─────────────────────────────┘        │
│                          ↓                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Step 1-6: 端到端调试（test-infra-upgrade 提供）       │        │
│  │  ├─ search→detail→toc→content→review 全链路           │        │
│  │  ├─ 真机级日志输出（[mm:ss.SSS] ︾︽⇒┌└≡◇）           │        │
│  │  ├─ Cookie/Header 自动携带（MockCookieStore）         │        │
│  │  ├─ AnalyzeUrl 完整移植（URL 解析三步流水线）          │        │
│  │  └─ 全部通过 → Step 8: 输出 _verified:true           │        │
│  │     某步失败 ↓                                       │        │
│  └───────────────────────┬─────────────────────────────┘        │
│                          ↓                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  进化触发器（本 Spec AD-8，嵌入 debug-source.py）       │        │
│  │  ├─ 分析根因（10类分类）                              │        │
│  │  ├─ 收敛检查（AD-10）                                 │        │
│  │  │   ├─ 通过 → 执行进化                               │        │
│  │  │   └─ 不通过 → 标记"需人工介入"                     │        │
│  │  └─ 执行进化                                         │        │
│  │      ├─ 服务端进化（依赖分析→补函数→重建JAR）          │        │
│  │      ├─ 客户端进化（增强脚本）                        │        │
│  │      ├─ 经验层进化（写basic-memory）                  │        │
│  │      └─ 规则层进化（修正规则/URL/选择器）              │        │
│  └───────────────────────┬─────────────────────────────┘        │
│                          ↓                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  重新验证（回到 Step 1-6，调用 test-infra-upgrade）    │        │
│  │  ├─ 通过 → Step 8: 输出 _verified:true               │        │
│  │  └─ 仍失败 → 再次触发进化（受收敛机制限制）            │        │
│  └───────────────────────┬─────────────────────────────┘        │
│                          ↓                                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Step 8: 输出验证报告（本 Spec 增强）                  │        │
│  │  ├─ _verified: true/false                            │        │
│  │  ├─ 每步结果+模拟数据样本                            │        │
│  │  ├─ 网站类型+干预建议                                │        │
│  │  ├─ 进化记录（如有）                                 │        │
│  │  └─ 速度度量（耗时+首次通过率）                       │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**与原阶段四/五的区别**：

| 维度 | 原设计（阶段四+五分离） | 合并后（AD-12） |
|------|----------------------|----------------|
| 架构 | 进化触发器独立 + 模拟器独立 | 进化触发器嵌入模拟器 |
| 数据流 | 模拟器失败→调用进化触发器→返回结果 | 模拟器内部闭环，无需跨模块调用 |
| 重新验证 | 进化后需手动重新运行模拟器 | 进化后自动回到 Step 1 |
| 速度 | 跨模块调用有开销 | 内部闭环，更快 |
| 复杂度 | 两个独立模块 | 一个统一模块 |
| **基础设施来源** | **自行实现全流程模拟器** | **引用 test-infra-upgrade** |

**状态**：📋 待实施（依赖 test-infra-upgrade 完成）

### AD-13: 与 test-infra-upgrade 的依赖关系 — "分层协作，不重复造轮子"

**决策**：本 Spec 的阶段四（自进化闭环）和阶段五（零人工干预测试）依赖 `test-infra-upgrade` Spec 提供的基础设施。本 Spec 不重复实现这些基础设施，仅在其上增加自进化集成层。

**依赖关系图**：

```
test-infra-upgrade Spec（基础设施层）
  ├─ L0: AnalyzeUrl 移植 ──────────────────┐
  ├─ L1: debugBookSource 命令 ─────────────┤
  ├─ L2: debugRssSource 命令 ──────────────┤
  ├─ L3: 增量日志输出 ─────────────────────┤
  ├─ L4: CookieStore 内存实现 ─────────────┤  基础设施
  ├─ L5: MockJsExtensions 扩展 ────────────┤  （不重复实现）
  ├─ L6: Book/BookSource 上下文注入 ────────┤
  ├─ L7: debug-source.py ──────────────────┘
  │
  ↓ 提供
  │
skill-trio-optimization Spec（自进化集成层）
  ├─ AD-8: 进化触发器 ─────────────────────┐
  ├─ AD-9: 网站类型检测+验证报告增强 ────────┤  集成层
  ├─ AD-10: 进化收敛机制 ──────────────────┤  （本 Spec 实现）
  ├─ AD-11: 必须人工干预边界 ───────────────┤
  ├─ AD-12: 自进化全流程模拟器 ─────────────┘
  │
  ↓ 集成点
  │
  ├─ 集成点1: debug-source.py Step 0 嵌入 site_type_detector.py
  ├─ 集成点2: debug-source.py 失败处理嵌入 evolution_trigger.py
  ├─ 集成点3: debug-source.py Step 8 嵌入增强验证报告
  ├─ 集成点4: site_type_detector._fetch_html 引用 network_safety_interceptor
  └─ 集成点5: 进化后重新调用 debug-source.py
```

**集成点详细说明**：

| 集成点 | 位置 | 本 Spec 新增内容 | test-infra-upgrade 提供内容 |
|--------|------|----------------|---------------------------|
| 1 | debug-source.py Step 0 | site_type_detector.py（网站类型检测+场景分类） | debug-source.py 脚本框架 |
| 2 | debug-source.py 失败处理 | evolution_trigger.py（进化触发器+收敛检查） | debug-source.py 失败检测 |
| 3 | debug-source.py Step 8 | 增强验证报告（进化记录+速度度量+网站类型） | 基础验证报告 |
| 4 | site_type_detector._fetch_html | network_safety_interceptor.py（频率控制+UA伪装+超时重试） | urllib 降级实现 |
| 5 | 进化后重新验证 | 自动重新调用 debug-source.py | debug-source.py 命令 |

**实施顺序约束**：

```
test-infra-upgrade 完成（至少 P0 任务）
  ↓
skill-trio-optimization 阶段一/二/三（P0/P1/P2，不依赖 test-infra-upgrade）
  ↓
skill-trio-optimization 阶段四/五（P1，依赖 test-infra-upgrade）
```

**状态**：📋 待实施

---

## 3. Data Flow（数据流）

### 3.1 优化后的执行证据数据流

```
source-creator Phase 1 完成
  → write_note(metadata={source_name, phase:"1", basic_memory_search, trap_check, cms_type, cf_detected})
  → 输出 [PHASE1_COMPLETE] 标志

source-creator Phase 3 完成
  → write_note(metadata={source_name, phase:"3", test_coverage, confidence_*, jvm_evolution_needed, phase4_triggered})
  → 输出 [PHASE3_COMPLETE] 标志

source-creator Phase 5 完成
  → write_note(metadata={source_name, phase:"5", dual_write, sync_status, schema_validation, code_evolution_executed})
  → 输出 [PHASE5_COMPLETE] 标志
  → 自动调用 workflow-auditor(source_name, task_type)

workflow-auditor 执行
  → search_notes(query="执行证据: {source_name}", tags=["execution-log"])
  → 逐项检查 8 个检查项（从 metadata 直接读取）
  → write_note(note_type="audit-report", directory="audit-reports/")
  → 输出审计报告
```

### 3.2 优化后的 skill-auditor 数据流

```
用户请求审查
  → 选择审查模式（L1/L2/L3）
  → L1: 10 项快速检查（含自动化脚本）
  → L2: 15 项核心检查（含合并后的统一检查项）
  → L3: 17 项深度检查（含债务清理）
  → 输出 3 部分报告（问题清单 + 修复验证 + 健康度评分）
```

### 3.3 自进化闭环数据流

```
AI 生成书源 JSON
  → debug-source.py 端到端调试执行
    ├─ Step 1-5 全部通过
    │   → 输出 "_verified": true
    │   → 用户直接导入手机
    │
    └─ 某步失败
        → 进化触发器分析根因
        → 分类进化需求：
          ├─ Mock 函数缺失
          │   → 读 Legado 源码 JsExtensions.kt
          │   → 更新 MinimalMockJsExtensions.kt
          │   → 备份旧 JAR
          │   → 重建 JAR (gradlew.bat fatJar)
          │   → 重新验证 → 通过
          │   → 写入 basic-memory (tags=["evolution"])
          │   → 更新未实现函数速查表
          │
          ├─ 行为不一致
          │   → 对比 AnalyzeRule.kt
          │   → 修正 Kotlin 源码
          │   → 重建 JAR → 重新验证
          │
          ├─ 脚本能力不足
          │   → 增强 debug-source.py
          │   → 重新验证
          │
          └─ 经验缺失
              → 写入 basic-memory
              → 更新 references/

→ 进化成果沉淀
  → 更新精准度指标
  → 标记进化版本号
  → 记录进化日志
```

---

## 4. File Changes（文件变更清单）

### 4.1 修改文件

| 文件 | 变更类型 | 变更内容 | 优先级 |
|------|---------|---------|--------|
| `.trae/skills/legado-source-creator/SKILL.md` | 修改 | 精简至<500行+增加决策树+统一陷阱编号 | P0 |
| `.trae/skills/legado-source-creator/references/troubleshooting/_index.md` | 修改 | 统一陷阱编号为连续 79 条 | P0 |
| `.trae/skills/legado-skill-auditor/SKILL.md` | 修改 | 分层审查+合并重叠项+修正A3数量 | P1 |
| `.trae/skills/legado-workflow-auditor/SKILL.md` | 修改 | 修复字段+补充判定逻辑+增加关系说明 | P0 |
| `.trae/skills/legado-source-creator/tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MinimalMockJsExtensions.kt` | 修改 | 修复6个签名+新增15个高频函数（ajax升级为真实HTTP请求由 test-infra-upgrade 负责） | P0 |
| `.trae/skills/legado-source-creator/scripts/deep-verify.py` | 修改 | 标记为 deprecated，全链路验证改调 debug-source.py（由 test-infra-upgrade 提供） | P1 |
| `.trae/skills/legado-source-creator/tools/rule_engine_client.py` | 修改 | 同步新函数 API（全流程模拟接口由 test-infra-upgrade 负责） | P1 |
| `.trae/skills/legado-source-creator/tools/jvm_helpers.py` | 修改 | 更新可信度评估规则+增加进化触发器 | P1 |
| `AGENTS.md` | 修改 | 统一陷阱数量+更新Skill协作说明 | P0 |
| `docs/specs/skill-architecture-optimization/tasks.md` | 修改 | 标记关联任务状态 | P2 |

### 4.2 新增文件

| 文件 | 内容 | 优先级 |
|------|------|--------|
| `.trae/skills/legado-source-creator/references/basic-memory-usage.md` | basic-memory 完整操作规范（从SKILL.md拆分） | P1 |
| `.trae/skills/legado-source-creator/references/jvm-infrastructure.md` | JVM 测试基础设施详情（从SKILL.md拆分） | P1 |
| `.trae/skills/legado-source-creator/references/code-evolution.md` | 代码进化机制详情（从SKILL.md拆分） | P1 |
| `.trae/skills/legado-source-creator/references/mock-unimplemented-functions.md` | MockJsExtensions 未实现函数速查表 | P1 |
| `.trae/skills/legado-source-creator/scripts/check_dead_links.py` | 自动死链检测脚本 | P2 |
| `.trae/skills/legado-source-creator/scripts/check_version_lock.py` | 版本锁检测脚本 | P2 |
| `.trae/skills/legado-source-creator/scripts/check_file_debt.py` | 文件债务扫描脚本 | P2 |
| `.trae/skills/legado-source-creator/scripts/evolution_trigger.py` | 进化触发器（测试失败根因分析+自动进化执行+收敛机制） | P1 |
| `.trae/skills/legado-source-creator/scripts/evolution_convergence.py` | 进化收敛机制（次数上限+收敛判断+冲突检测+死循环检测） | P1 |
| `.trae/skills/legado-source-creator/scripts/site_type_detector.py` | 网站类型检测器（登录/CF/验证码检测+场景分类） | P1 |
| `.trae/skills/legado-source-creator/scripts/speed_metrics.py` | 速度度量脚本（进化响应时间+AI执行效率+首次通过率） | P1 |
| `.trae/skills/legado-source-creator/scripts/network_safety_interceptor.py` | 网络请求安全机制（频率控制+UA伪装+超时重试+请求日志） | P1 |
| `.trae/skills/legado-source-creator/references/evolution-mechanism.md` | 自进化机制完整文档（从SKILL.md拆分+新增收敛机制+人工干预边界） | P1 |
| `.trae/skills/legado-source-creator/scripts/auto_evolve_server.py` | 服务端自动进化（提取签名→生成Mock→备份→重建→验证→回滚→版本标记，支持 --dry-run） | P1 |
| `.trae/skills/legado-source-creator/scripts/feedback_collector.py` | 进化反馈循环（用户反馈收集+按CMS分组分析+导出 basic-memory cases/） | P1 |
| `.trae/skills/legado-source-creator/scripts/evolution_log.py` | 进化日志记录 + 未实现函数速查表更新（移除已补全函数） | P1 |
| `.trae/skills/legado-source-creator/scripts/precision_metrics.py` | 精准度度量（内置测试通过率 × 真机一致率，趋势报告） | P1 |
| `.trae/skills/legado-source-creator/scripts/rule_evolution.py` | 规则层进化（4类规则错误修正建议：语法/URL模板/选择器/字段映射） | P1 |

### 4.3 引用 test-infra-upgrade 的文件（本 Spec 不修改，仅引用）

| 文件 | 由 test-infra-upgrade 提供 | 本 Spec 引用方式 |
|------|---------------------------|-----------------|
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/AnalyzeUrl.kt` | L0: AnalyzeUrl 移植 | 进化触发器分析 URL 错误时引用 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/BookSourceDebugger.kt` | L1: 端到端书源调试 | 自进化模拟器调用 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/RssSourceDebugger.kt` | L2: 端到端订阅源调试 | 自进化模拟器调用 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockCookieStore.kt` | L4: CookieStore 内存实现 | 网站类型检测引用 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/DebugLogger.kt` | L3: 增量日志输出 | 验证报告引用 |
| `scripts/debug-source.py` | L7: 端到端调试脚本 | 自进化集成层嵌入目标 |

### 4.4 不变文件

| 文件 | 原因 |
|------|------|
| `references/booksource-schema.md` | 已验证与源码 100% 一致 |
| `references/source-analysis/rss-source-entity.md` | 已验证与源码 100% 一致 |
| `references/rule-syntax.md` | 仅修复 @. 前缀描述（如验证不支持） |
| `templates/*` | 模板文件无需修改 |
| `tools/mvp1-build/build.gradle.kts` | 版本锁已验证一致 |

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| SKILL.md 精简后丢失关键信息 | 中 | 高 | 拆分而非删除，所有内容保留在 references/ |
| Mock 签名修复引入新 bug | 低 | 中 | 修复后运行现有测试脚本验证 |
| 分层审查导致 L1 漏过严重问题 | 低 | 高 | L1 包含所有 P0 级检查项 |
| basic-memory 简化后元数据不完整 | 低 | 中 | 统一模板包含所有必要字段 |
| workflow-auditor 字段变更破坏旧数据 | 中 | 中 | 增加字段兼容性检查（缺失字段时降级为标志解析） |

---

## 6. 验证计划

### 6.1 单元验证

| 验证项 | 方法 | 通过标准 |
|--------|------|---------|
| Mock 签名修复 | 运行 verify-decrypt.py + verify-selector.py | 无 TypeError |
| 陷阱数量统一 | Grep "56条"（排除注释） | 0 结果 |
| 执行证据字段对齐 | 模拟 write_note + search_notes | 8 个检查项均可读取 |
| SKILL.md 行数 | wc -l | < 500 |
| skill-auditor 检查点数 | 计数 | ~30（合并后） |

### 6.2 集成验证

| 验证场景 | 方法 | 通过标准 |
|---------|------|---------|
| 端到端书源创建 | 创建一个普通小说书源 | 8/8 审计通过 |
| 端到端订阅源创建 | 创建一个视频订阅源 | 8/8 审计通过 |
| L1 快速审查 | 执行 L1 层 10 项检查 | 5 分钟内完成 |
| L2 核心审查 | 执行 L2 层 15 项检查 | 20 分钟内完成 |
| 降级路径 | 模拟 basic-memory 不可用 | 三步降级均正常 |

---

## 7. 实施变更记录

> 本章节记录实施过程中与设计文档的不同步项，已于 2026-06-18 同步修复至本 design.md。

### 7.1 已废弃组件替换

| 原设计引用 | 实际实现 | 涉及位置 | 修复说明 |
|-----------|---------|---------|---------|
| `deep-verify.py`（作为活跃工具） | `debug-source.py` | AD-6 决策树2、AD-8 进化触发条件表、AD-8 进化触发器实现、3.3 数据流（2处） | deep-verify.py 已标记 deprecated，全链路验证改用 debug-source.py |
| `full_flow_simulator.py` | `debug-source.py` | AD-11 场景检测实现 | 原设计引用了不存在的 full_flow_simulator.py，实际嵌入 debug-source.py Step 0 |

### 7.2 接口签名变更

| 组件 | 原设计签名 | 实际签名 | 修复说明 |
|------|----------|---------|---------|
| site_type_detector.py | `detect_site_type(homepage_html: str, response_url: str) -> SiteType` | `detect_site_type(url=None, html=None) -> dict` | 接口从位置参数改为关键字参数，返回类型从 SiteType 对象改为 dict。AD-9 和 AD-11 两处代码块已同步更新 |
| evolution_trigger.py | `analyze_test_failure(error, rule_content) -> EvolutionNeed` | `trigger_evolution(error_type, error_msg, stack_trace='') -> dict` | 函数名和参数变更，返回 dict 含 convergence 字段（收敛检查结果嵌入） |
| evolution_convergence.py | `class EvolutionConvergence: should_evolve(error, rule_content) -> EvolutionDecision` | 模块级函数 `check_evolution_allowed(signature, accuracy) -> (allowed, count, reason)` | 从类改为模块级函数，返回元组而非对象 |

### 7.3 嵌入点变更

| 组件 | 原设计嵌入点 | 实际嵌入点 | 修复说明 |
|------|------------|----------|---------|
| network_safety_interceptor.py | RealHttpExecutor（test-infra-upgrade） | site_type_detector._fetch_html | debug-source.py 通过 RuleEngineClient 调用 JVM 不直接发 HTTP，安全机制仅在 site_type_detector 获取 HTML 时生效。AD-9 代码块和 AD-13 集成点4 已同步更新 |

### 7.4 新增脚本（design.md 原未记录）

| 脚本 | 功能 | 对应任务 | 修复说明 |
|------|------|---------|---------|
| `auto_evolve_server.py` | 服务端自动进化（提取签名→生成Mock→备份→重建→验证→回滚→版本标记） | 4.2 服务端自动进化 | 支持 `--dry-run` 模式验证（非完整端到端），已补充至 4.2 新增文件表 |
| `feedback_collector.py` | 进化反馈循环（用户反馈收集+按CMS分组分析+导出 basic-memory cases/） | 5.1 进化反馈循环 | 已补充至 4.2 新增文件表 |
| `evolution_log.py` | 进化日志记录 + 未实现函数速查表更新 | 4.4 进化成果沉淀 | 已补充至 4.2 新增文件表 |
| `precision_metrics.py` | 精准度度量（内置测试通过率 × 真机一致率，趋势报告） | 4.5 精准度度量 | 已补充至 4.2 新增文件表 |
| `rule_evolution.py` | 规则层进化（4类规则错误修正建议：语法/URL模板/选择器/字段映射） | 4.7 规则层进化 | 已补充至 4.2 新增文件表 |

### 7.5 进化触发器分类简化

| 维度 | 原设计 | 实际实现 | 修复说明 |
|------|--------|---------|---------|
| 根因分类数量 | 10 类（含 CF拦截、加密方式、JSONPath/CSS语法、searchUrl、选择器、字段映射等单独分类） | 5 类（mock_missing / behavior_mismatch / network_issue / rule_error / experience_missing） | 部分细分场景合并为 rule_error 和 experience_missing。AD-8 代码块已更新注释说明 |

### 7.6 debug-source.py 集成点扩展

| 集成点 | 原设计 | 实际实现 | 修复说明 |
|--------|--------|---------|---------|
| 集成点数量 | 5 个 | 9 个 | 实际新增：speed_metrics（速度度量）、evolution_convergence（收敛检查）、evolution_log（进化日志）、auto_evolve_server（服务端进化）。AD-13 集成点表保持原5项，新增4项在 debug-source.py 代码中实现 |

### 7.7 auto_evolve_server.py dry-run 模式

| 维度 | 原设计 | 实际实现 | 修复说明 |
|------|--------|---------|---------|
| 验证方式 | 完整端到端（读源码→补函数→重建JAR→验证） | 支持 `--dry-run` 模式（仅提取签名+生成Mock，不实际重建JAR） | tasks.md V13 注明"dry-run验证"。已在新增文件表中标注 --dry-run 支持 |

### 7.8 SKILL.md 行数偏差

| 维度 | 设计目标 | 实际 | 说明 |
|------|---------|------|------|
| SKILL.md 行数 | < 500 行 | 543 行 | 设计目标未达成，超出 43 行。tasks.md V4 记录为 494 行（实施时），后续子代理修改可能增加了内容。设计目标保持不变 |
