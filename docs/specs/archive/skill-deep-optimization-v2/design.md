# Design: Skill 深度优化 V2 — 仿真服务端关键 Bug 修复 + 设计哲学修正 + 价值验证落地 + 减少用户手工操作 + 查漏补缺 + 真实测试验证优化修复

---

## 1. Technical Approach（技术方案）

### 1.1 总体架构

本次优化**不改变**现有架构，而是在现有基础上**修复 7 个致命 bug + 整改基础设施 + 补齐测试验证**：

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Python 客户端层（整改）                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ debug-source.py  │  │ deep-verify.py   │  │ check_health.py  │  │
│  │ (自动埋点+函数名 │  │ (移除deprecated  │  │ (三合一合并)     │  │
│  │  对齐)           │  │  标记)           │  │                  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              JVM 服务端 (Bug 修复)                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  规则引擎层（修复）                                          │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │   │
│  │  │AnalyzeRule   │ │AnalyzeByRegex│ │AnalyzeUrl    │         │   │
│  │  │(修复:NativeObj│ │(新增:正则模式)│ │(修复:type二进制│       │   │
│  │  │ +unescape    │ │              │ │ +XML内容类型) │         │   │
│  │  │ +put/get层级)│ │              │ │              │         │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Mock 层（修复）                                             │   │
│  │  ┌──────────────┐ ┌──────────────┐                         │   │
│  │  │MockCookieStore│ │MinimalMockJs │                         │   │
│  │  │(修复:getSub  │ │Extensions    │                         │   │
│  │  │ Domain多段TLD)│ │(修复:put/get │                         │   │
│  │  │              │ │ 委托+重定向) │                         │   │
│  │  └──────────────┘ └──────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  调试器层（修复）                                             │   │
│  │  ┌──────────────┐                                          │   │
│  │  │BookSourceDebug│  修复:变量持久化使用 MockBook/MockSource  │   │
│  │  │er             │  而非 MinimalMockJsExtensions            │   │
│  │  └──────────────┘                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│           测试验证层（新增）                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │AnalyzeUrlTest│ │MockCookieTest│ │AnalyzeRuleTest│               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│  ┌──────────────┐ ┌──────────────┐                               │
│  │MockJsExtTest │ │test-real-     │                               │
│  │              │ │sources.sh     │                               │
│  └──────────────┘ └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Bug 修复方案

#### Bug 1: 变量 put/get 两套不互通（FR-1.1）

**根因**：`MinimalMockJsExtensions.put()` 存到自己的 `variableMap`，而 `AnalyzeRule.get()` 从 `chapter → book → source` 取。

**修复方案**：让 `MinimalMockJsExtensions` 持有 `MockBook` 和 `MockSource` 引用，`put/get` 委托到这些对象的 variableMap。

```kotlin
// 修改前（bug）
class MinimalMockJsExtensions {
    private val variableMap = mutableMapOf<String, String>()
    fun put(key: String, value: String): String {
        variableMap[key] = value  // 存到自己的 map
        return value
    }
}

// 修改后（修复）
class MinimalMockJsExtensions(
    private val mockBook: MockBook? = null,
    private val mockSource: MockSource? = null,
    private val mockChapter: MockBookChapter? = null
) {
    fun put(key: String, value: String): String {
        // 委托到 AnalyzeRule 层级存储
        mockChapter?.putVariable(key, value)
            ?: mockBook?.putVariable(key, value)
            ?: mockSource?.put(key, value)
        return value
    }
    
    fun get(key: String): String {
        return mockChapter?.getVariable(key)
            ?: mockBook?.getVariable(key)
            ?: mockSource?.get(key)
            ?: ""
    }
}
```

**验证**：书源 ruleBookInfo.init 中 `java.put("tocUrl", "...")` 在 ruleToc 中 `@get:{tocUrl}` 能正确取到。

#### Bug 2: getSubDomain 简化错误（FR-1.2）

**根因**：用 `parts.takeLast(2)` 替代 PublicSuffixDatabase，多段 TLD 域名（.co.uk/.com.cn）提取错误。

**修复方案**：引入 Mozilla Public Suffix List 的简化实现，或硬编码常见多段 TLD。

```kotlin
// 修改前（bug）
fun getSubDomain(url: String): String {
    val parts = URL(url).host.split(".")
    return parts.takeLast(2).joinToString(".")  // www.example.co.uk → co.uk（错误）
}

// 修改后（修复）
private val MULTI_PART_TLDS = setOf(
    "co.uk", "ac.uk", "gov.uk", "org.uk",  // 英国
    "com.cn", "net.cn", "org.cn", "gov.cn",  // 中国
    "com.au", "net.au", "org.au",  // 澳大利亚
    "co.jp", "or.jp", "ne.jp",  // 日本
    "com.br", "net.br", "org.br"  // 巴西
    // ... 更多多段 TLD
)

fun getSubDomain(url: String): String {
    val host = URL(url).host
    val parts = host.split(".")
    if (parts.size < 2) return host
    val lastTwo = parts.takeLast(2).joinToString(".")
    if (parts.size >= 3 && MULTI_PART_TLDS.contains(lastTwo)) {
        return parts.takeLast(3).joinToString(".")  // www.example.co.uk → example.co.uk
    }
    return lastTwo  // www.example.com → example.com
}
```

**验证**：`www.example.co.uk` 的 Cookie 存到 `example.co.uk`。

#### Bug 3: NativeObject/LinkedTreeMap 处理缺失（FR-1.3）

**根因**：spec.md REQ-L6-3 标记完成但实际未实现。

**修复方案**：在 AnalyzeRule.getStringList/getString 中新增分支。

```kotlin
// 在 getStringList 中新增
when (result) {
    is NativeObject -> {
        // Rhino 原生对象，按键值访问
        val value = result.get(key)
        return listOf(value?.toString() ?: "")
    }
    is LinkedTreeMap<*, *> -> {
        // gson LinkedTreeMap，按键值访问
        val value = result[key]
        return listOf(value?.toString() ?: "")
    }
    // ... 原有分支
}
```

**验证**：JS 返回 `{name: "斗破"}` 时 `getString("name")` 返回 `"斗破"`。

#### Bug 4: unescape 缺失（FR-1.4）

**根因**：真机 getString 最后有 `StringEscapeUtils.unescapeHtml4(resultStr)`，仿真没有。

**修复方案**：在 AnalyzeRule.getString 返回前添加 unescape。

```kotlin
// 修改前（bug）
return resultStr

// 修改后（修复）
import org.apache.commons.text.StringEscapeUtils
return StringEscapeUtils.unescapeHtml4(resultStr)
```

**验证**：正文中的 `&amp;` 被正确反转为 `&`。

#### Bug 5: Mode.Regex 缺失（FR-1.5）

**根因**：仿真版 AnalyzeRule 无 AnalyzeByRegex。

**修复方案**：新增 AnalyzeByRegex 类，AnalyzeRule.getString 支持 Mode.Regex 分支。

```kotlin
class AnalyzeByRegex(private val content: String) {
    fun getString(rule: String): String {
        val pattern = rule.removePrefix("@regex:")
        val match = Regex(pattern).find(content)
        return match?.value ?: ""
    }
    
    fun getStringList(rule: String): List<String> {
        val pattern = rule.removePrefix("@regex:")
        return Regex(pattern).findAll(content).map { it.value }.toList()
    }
}

// AnalyzeRule.getString 中新增
Mode.Regex -> {
    return AnalyzeByRegex(content).getString(rule)
}
```

**验证**：使用 `@regex:` 前缀的规则能正确匹配。

#### Bug 6: type 二进制处理修复（FR-1.6）

**根因**：type 非空时两个分支都走 executeStrRequest，未处理二进制返回。

**修复方案**：type 非空时返回 hex 编码的二进制数据。

```kotlin
// 修改前（bug）
val response = executeStrRequest(...)  // 总是走字符串请求

// 修改后（修复）
if (urlOption.type != null) {
    // 二进制类型，返回 hex 编码
    val bytes = executeByteArrayRequest(...)
    return HexUtil.encodeHexStr(bytes)
} else {
    return executeStrRequest(...)
}
```

#### Bug 7: 重定向行为修复（FR-1.7）

**根因**：仿真 followRedirects(true)，真机 followRedirects(false)。

**修复方案**：改为 followRedirects(false)。

```kotlin
// 修改前（bug）
.followRedirects(true)

// 修改后（修复）
.followRedirects(false)  // 对齐真机，用于拦截重定向
```

### 1.3 测试基础设施整改方案

#### 整改 1: 孤儿脚本索引 + 合并（FR-2.1）

将 3 个 check_*.py 合并为 `check_health.py`，并在 SKILL.md 索引。

```python
# check_health.py
"""三合一健康检查：死链 + 版本锁 + 文件债务"""
import check_dead_links
import check_version_lock
import check_file_debt

def main():
    print("=== 死链检测 ===")
    check_dead_links.main()
    print("\n=== 版本锁检测 ===")
    check_version_lock.main()
    print("\n=== 文件债务扫描 ===")
    check_file_debt.main()
```

#### 整改 2: deep-verify.py 废弃决策修正（FR-2.2）

移除 deprecated 标记，重新定位为"JVM 不可用时降级路径"。

```python
# 修改前
# ⚠️ DEPRECATED: 本脚本已废弃，请使用 debug-source.py 进行端到端调试。

# 修改后
# 📋 定位：JVM 不可用时的 Python 仿真降级路径
# 首选：debug-source.py（JVM 真机级调试）
# 降级：deep-verify.py（Python 仿真，覆盖率 35%）
```

#### 整改 3: 函数名对齐设计文档（FR-2.3/2.4）

```python
# evolution_trigger.py
# 修改前
def trigger_evolution(error, rule_content):
    ...

# 修改后
def analyze_test_failure(error, rule_content):
    ...

# evolution_convergence.py
# 修改前
def check_evolution_allowed(error, rule_content):
    ...

# 修改后
def should_evolve(error, rule_content):
    ...
```

#### 整改 4: 硬编码路径修复（FR-2.5）

```python
# 修改前
BASE_DIR = Path(r"f:\myself\github\WeAgentChat\temp\legado\.trae\skills\legado-source-creator")

# 修改后
BASE_DIR = Path(__file__).resolve().parent.parent  # 相对于脚本位置
```

#### 整改 5: stub mock 行为验证（FR-2.6）

```python
# auto_evolve_server.py
def generate_mock(func_name, signature):
    mock_code = f"""
    fun {func_name}({signature}): Any {{
        // TODO: 验证行为与源码一致
        return getDefaultReturnValue()
    }}
    """
    return mock_code

# 新增：行为验证
def verify_mock_behavior(func_name):
    """进化后验证 Mock 函数可调用"""
    client = RuleEngineClient()
    client.start_server()
    try:
        result = client.eval_js(f"java.{func_name}('test')")
        return result is not None
    except:
        return False
```

#### 整改 6: speed_metrics 自动埋点（FR-2.7）

```python
# debug-source.py 中自动记录
import speed_metrics
import time

start_time = time.time()
# ... 执行调试 ...
execution_sec = time.time() - start_time
speed_metrics._record("execution_sec", execution_sec)
if evolution_triggered:
    speed_metrics._record("evolution_sec", evolution_time)
```

---

## 2. Architecture Decisions（架构决策）

### AD-1: 变量持久化修复采用委托模式

**决策**：MinimalMockJsExtensions 持有 MockBook/MockSource 引用，put/get 委托到这些对象。

**理由**：
- 与真机 `java.put()` 调用 AnalyzeUrl/AnalyzeRule 的 put 一致
- 不破坏现有 MinimalMockJsExtensions 接口
- MockBook/MockSource 在整个调试会话期间持久存在

### AD-2: getSubDomain 采用硬编码多段 TLD 列表

**决策**：使用硬编码的多段 TLD 集合，而非引入完整的 PublicSuffixDatabase。

**理由**：
- 完整的 PublicSuffixDatabase 需要 ~200KB 数据文件，不符合懒原则
- 硬编码常见多段 TLD（约 50 个）可覆盖 95%+ 场景
- 后续可按需扩展

### AD-3: AnalyzeByRegex 新增而非复用

**决策**：新增 AnalyzeByRegex 类，而非复用现有正则逻辑。

**理由**：
- 真机有独立的 AnalyzeByRegex 类
- 保持与真机架构一致
- 复杂度低（~50 行）

### AD-4: deep-verify.py 保留而非废弃

**决策**：移除 deprecated 标记，重新定位为"JVM 不可用时降级路径"。

**理由**：
- deep-verify.py 有 1887 行 Python 模拟逻辑，是 JVM 不可用时的唯一降级路径
- 废弃决策过于激进，未考虑 JVM 不可用场景
- 保留不等于推荐，SKILL.md 中明确"首选 debug-source.py"

### AD-5: 3 个 check_*.py 合并为 check_health.py

**决策**：合并为单一入口，保留原脚本作为模块。

**理由**：
- 减少脚本数量（懒原则）
- 统一入口便于调用
- 保留原脚本作为可独立运行的模块

### AD-6: 测试验证采用真实网站回测

**决策**：必须用真实网站回测，禁止用 mock 数据。

**理由**：
- mock 数据回测无法发现"仿真通过但手机报错"的问题
- 真实网站回测是唯一能验证"仿真=真机"的方法
- 选取 3 个不同类型的书源（简单+加密+分页）覆盖核心场景

### AD-7: 自进化方向从"补全 Mock"转向"自动修复书源规则"

**决策**：自进化的终点从"Mock 补全了"改为"书源规则修复成功或给出明确修复建议"。

**理由**：
- 用户不关心 Mock 缺不缺失，用户关心的是"我的书源能不能用"
- 补全 Mock 是手段，修复书源规则才是目的
- auto_evolve_server 从"自动补全 Mock 的主力"降为"仅当 mock_missing 时触发的辅助"

**实现**：
- evolution_trigger 新增 rule_error 分类的修复建议生成逻辑
- classify-and-fix 实现真正的 fix（自动修改源 JSON 并重新验证）
- auto_evolve_server 只在 mock_missing 类型时触发

### AD-8: 负面测试——故意制造错误的测试

**决策**：补充 5 个负面测试场景，验证仿真能检测到错误并给出明确信息。

**理由**：
- 只测 happy path 的测试是"自嗨式测试"
- 真正能反映问题的测试应该是"故意制造错误的测试"
- 负面测试能验证错误信息是否可操作

**5 个负面测试场景**：
1. 故意写错 ruleToc → 验证检测到"目录阶段失败"
2. 需要登录的网站 → 验证 site_type_detector 识别并提示
3. 有 CF 保护的网站 → 验证 site_type_detector 识别并标记
4. 故意写错 CSS 选择器 → 验证检测到"选择器未匹配"
5. 故意写错加密参数 → 验证 verify-decrypt.py 检测到"解密失败"

### AD-9: 仿真服务端从"必须依赖"降为"可选工具"

**决策**：JVM 不可用时自动降级到 deep-verify.py（Python 仿真），工作流不中断。

**理由**：
- 仿真服务端是"测试工具"而非"开发依赖"
- JVM 不可用时整个 5 阶段工作流就断了，违背 Legado 设计哲学
- deep-verify.py 有 1887 行 Python 模拟逻辑，是合理的降级路径

**实现**：
- debug-source.py 启动前 ping JVM，失败时自动降级
- SKILL.md 明确"JVM 不可用时降级到 Python 仿真（覆盖率 35%）"

### AD-10: 价值层面空架子清理——提升或废弃

**决策**：7 个价值层面空架子，要么提升到有真实价值，要么废弃。

**理由**：
- 代码能跑但不解决问题 = 价值层面空架子
- 空架子会误导维护者以为"功能已实现"

**清理方案**：
| 脚本 | 处理方式 |
|------|---------|
| speed_metrics.py | 提升：数据驱动经验反哺（first_pass_rate < 60% 时触发） |
| evolution_trigger.py | 提升：分类后执行实际修复（而非只分类） |
| evolution_convergence.py | 提升：死循环检测被实际触发并记录 |
| auto_evolve_server.py | 提升：Mock 有行为验证（而非 stub） |
| generate-js-doc.py | 废弃或重写：文档内容从代码动态提取 |
| deep-analyze-js.py | 废弃或重写：提取通用分析函数为 CLI 工具 |
| 3 个 check_*.py | 提升：检测结果用于实际修复 |

### AD-11: 知识库强制查阅机制

**决策**：Phase 2（构建规则）增加"知识库查阅"步骤，生成规则前必须 Grep references/ 中的相关陷阱。

**理由**：
- references/ 有 40+ 文档但生成书源时很少查阅
- 知识库与代码脱节（陷阱说一套，代码做另一套）
- 强制查阅能提升规则质量

**实现**：
- Phase 2 输出中包含"已查阅的陷阱清单"
- 79 条陷阱清单与 verify-source.py 检查项对齐
- 版本锁定一致性检查（references/ vs build.gradle.kts）

### AD-12: 错误信息可操作性提升

**决策**：每个错误类型增加"修复建议"字段，给出可操作的修复建议。

**理由**：
- 用户看到 `TypeError: java.xxx is not a function` 不知道怎么修复
- 错误信息应该指导用户修复，而非只是报错

**实现**：
- TypeError → "该 JS 函数在仿真服务端未实现，建议：1) 检查函数名拼写 2) 标记为 unverifiable 3) 手动在手机验证"
- 网络错误 → "可能原因：超时/DNS 解析失败/连接拒绝"
- 规则解析错误 → 输出原始 HTML 片段 + 规则 + 预期结果

### AD-13: 真实用户体验验证

**决策**：用真实网站 URL 走一遍完整 5 阶段工作流，记录体验报告。

**理由**：
- 从未站在用户角度体验过完整工作流
- 一直在"造工具"，从未"用工具"
- "仿真通过=手机可用"这个核心假设从未被验证

**验证内容**：
1. 端到端体验：5 阶段工作流完整走通，记录每阶段耗时和问题
2. 仿真 vs 手机对比：将仿真通过的书源导入手机，验证是否真的可用
3. 错误恢复体验：故意制造错误，验证用户能否根据错误信息自行修复

---

## 2.5 减少用户手工操作（核心进化方向 — 用户最新诉求）

> **背景**：用户明确指出"如果真的需要用户手工操作的话，你得想想办法"。原有设计的"必须人工干预边界"过于消极，只是"检测到→标记→停止"。新增 10 个架构决策（AD-14 到 AD-23），将"消极模式"改为"积极模式"：检测到→尝试辅助→辅助失败再标记。

### AD-14: 登录场景主动辅助架构 — "Cookie 优先，表单辅助，OAuth 标记"

**决策**：登录场景采用三层辅助策略，而非直接标记"需人工"。

**三层辅助策略**：

```
检测到登录需求
  ↓
第一层：Cookie 导入（首选）
  ├─ 提示用户提供浏览器 Cookie
  ├─ 自动解析 Cookie 字符串
  ├─ 注入到 MockCookieStore
  └─ 重新执行请求 → 成功则继续
  ↓ 失败
第二层：表单登录辅助
  ├─ 自动分析登录表单结构
  ├─ 提示用户需要提供哪些字段
  ├─ 用户提供字段值后自动提交
  └─ 重新执行请求 → 成功则继续
  ↓ 失败
第三层：OAuth 标记
  └─ 标记"需人工"，输出降级建议
```

**实现**：

```python
# login_assistant.py（新增）
def assist_login(url, html, mock_cookie_store):
    """登录场景主动辅助"""
    # 1. 分析登录表单
    form_info = analyze_login_form(html)
    
    # 2. 尝试 Cookie 导入（首选）
    cookie_str = prompt_user_for_cookie(url)
    if cookie_str:
        mock_cookie_store.set_cookie(url, cookie_str)
        if verify_login_success(url, mock_cookie_store):
            persist_cookie(url, cookie_str)
            return {"status": "success", "method": "cookie_import"}
    
    # 3. 尝试表单登录（辅助）
    if form_info:
        fields = prompt_user_for_credentials(form_info)
        if fields:
            login_result = submit_login_form(form_info, fields)
            if login_result.success:
                persist_cookie(url, login_result.cookies)
                return {"status": "success", "method": "form_login"}
    
    # 4. OAuth 标记
    return {"status": "needs_manual", "reason": "OAuth or complex login"}
```

**Cookie 持久化**：

```python
def persist_cookie(url, cookie_str):
    """Cookie 持久化到文件"""
    domain = extract_domain(url)
    cache_path = f"tools/.cookie-cache/{domain}.json"
    with open(cache_path, 'w') as f:
        json.dump({"cookie": cookie_str, "timestamp": time.time()}, f)

def load_persisted_cookie(url):
    """加载持久化的 Cookie"""
    domain = extract_domain(url)
    cache_path = f"tools/.cookie-cache/{domain}.json"
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            data = json.load(f)
            # 检查是否过期（7天）
            if time.time() - data["timestamp"] < 7 * 86400:
                return data["cookie"]
    return None
```

**状态**：📋 待实施

### AD-15: CF盾破盾辅助架构 — "自动求解优先，Cookie 导入降级"

**决策**：CF 场景采用自动破盾优先策略，而非直接标记"需配置"。

**破盾策略**：

```
检测到 CF Challenge
  ↓
第一层：自动求解（首选）
  ├─ 集成 cloudscraper 库
  ├─ 自动求解 CF JS Challenge（5秒等待 + JS求值）
  ├─ 获取 cf_clearance Cookie
  └─ 重新执行请求 → 成功则继续
  ↓ 失败
第二层：Cookie 导入（降级）
  ├─ 提示用户手动破盾
  ├─ 用户提供 cf_clearance Cookie
  └─ 重新执行请求 → 成功则继续
  ↓ 失败
第三层：标记需 webView
  └─ 标记"需 webView 配置"，输出降级建议
```

**实现**：

```python
# cf_bypass.py（新增）
def bypass_cf(url, html, mock_cookie_store):
    """CF 盾破盾辅助"""
    # 1. 尝试自动破盾
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        if not is_cf_challenge(response.text):
            cf_cookie = extract_cf_cookie(response)
            mock_cookie_store.set_cookie(url, cf_cookie)
            persist_cookie(url, cf_cookie)
            return {"status": "success", "method": "auto_bypass"}
    except ImportError:
        pass  # cloudscraper 未安装
    
    # 2. 尝试 Cookie 导入
    cf_cookie = prompt_user_for_cf_cookie(url)
    if cf_cookie:
        mock_cookie_store.set_cookie(url, cf_cookie)
        persist_cookie(url, cf_cookie)
        if verify_no_cf(url, mock_cookie_store):
            return {"status": "success", "method": "cookie_import"}
    
    # 3. 标记需 webView
    return {"status": "needs_webview", "reason": "CF bypass failed"}
```

**UA 指纹优化**：

```python
# 完整浏览器指纹
BROWSER_FINGERPRINTS = {
    "chrome": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"'
    },
    # Firefox, Safari 等
}
```

**状态**：📋 待实施

### AD-16: 验证码识别辅助架构 — "OCR 优先，人工辅助降级"

**决策**：验证码场景采用 OCR 识别优先策略，而非直接标记"需人工"。

**识别策略**：

```
检测到验证码
  ↓
第一层：类型识别
  ├─ 识别验证码类型（图形/滑块/点选/行为）
  └─ 图形验证码 → 第二层；其他 → 第三层
  ↓
第二层：OCR 识别（图形验证码）
  ├─ 集成 ddddocr 库
  ├─ 识别 4-6 位字母数字
  └─ 识别成功 → 提交验证码 → 成功则继续
  ↓ 失败
第三层：人工辅助
  ├─ 导出验证码图片
  ├─ 提示用户手动识别
  └─ 用户输入 → 提交 → 成功则继续
  ↓ 失败
第四层：标记需人工
  └─ 标记"需人工"，输出降级建议
```

**实现**：

```python
# captcha_assistant.py（新增）
def assist_captcha(url, html, mock_cookie_store):
    """验证码识别辅助"""
    # 1. 识别验证码类型
    captcha_type = identify_captcha_type(html)
    
    if captcha_type == "image":
        # 2. 图形验证码 OCR
        captcha_img_url = extract_captcha_img_url(html)
        captcha_img = download_image(captcha_img_url)
        
        try:
            import ddddocr
            ocr = ddddocr.DdddOcr()
            result = ocr.classification(captcha_img)
            if submit_captcha(url, result, mock_cookie_store):
                persist_cookie(url, mock_cookie_store.get_cookie(url))
                return {"status": "success", "method": "ocr"}
        except ImportError:
            pass  # ddddocr 未安装
        
        # 3. 人工辅助
        img_path = export_captcha_image(captcha_img)
        user_input = prompt_user_for_captcha(img_path)
        if user_input and submit_captcha(url, user_input, mock_cookie_store):
            persist_cookie(url, mock_cookie_store.get_cookie(url))
            return {"status": "success", "method": "manual"}
    
    # 4. 复杂验证码标记
    return {"status": "needs_manual", "reason": f"complex captcha: {captcha_type}"}
```

**状态**：📋 待实施

### AD-17: 加密自动分析架构 — "JS 代码扫描 + 模式匹配 + 代码生成"

**决策**：加密场景采用自动分析策略，而非要求用户手动分析。

**分析流程**：

```
发现正文加密
  ↓
第一层：JS 代码扫描
  ├─ 扫描 JS 代码中的加密函数调用
  ├─ 识别 CryptoJS.AES.decrypt / CryptoJS.DES.decrypt 等
  └─ 提取加密类型
  ↓
第二层：密钥提取
  ├─ 硬编码：var key = "xxx"
  ├─ 变量引用：var key = someFunction()
  └─ 函数返回值：getKey()
  ↓
第三层：模式判断
  ├─ IV 存在 → CBC/CTR/GCM
  └─ IV 不存在 → ECB
  ↓
第四层：代码生成
  └─ 生成 createSymmetricCrypto 调用代码模板
```

**实现**：

```python
# crypto_analyzer.py（新增）
def analyze_encryption(js_code, html):
    """加密自动分析"""
    # 1. 扫描加密函数调用
    crypto_calls = scan_crypto_calls(js_code)
    # 匹配模式：CryptoJS.AES.decrypt, CryptoJS.DES.decrypt, CryptoJS.RSA.decrypt 等
    
    if not crypto_calls:
        return {"status": "no_encryption"}
    
    # 2. 提取密钥
    for call in crypto_calls:
        key = extract_key(js_code, call)
        iv = extract_iv(js_code, call)
        
        # 3. 判断模式
        mode = determine_mode(call["type"], iv)
        
        # 4. 生成代码模板
        code_template = generate_decrypt_code(call["type"], key, iv, mode)
        
        # 5. 验证
        if verify_decrypt(code_template, html):
            return {
                "status": "success",
                "type": call["type"],
                "key": key,
                "iv": iv,
                "mode": mode,
                "code_template": code_template
            }
    
    return {"status": "analysis_failed"}
```

**状态**：📋 待实施

### AD-18: 网站结构智能分析架构 — "CMS 识别 + 结构分析 + 规则建议"

**决策**：网站结构场景采用自动分析策略，而非要求用户手动分析。

**分析流程**：

```
分析网站
  ↓
第一层：CMS 识别
  ├─ 扫描 HTML 特征（wp-content, typecho, dede 等）
  ├─ 匹配预设规则模板
  └─ 输出 CMS 类型 + 置信度
  ↓
第二层：页面结构分析
  ├─ 分析列表页 HTML 结构
  ├─ 分析详情页 HTML 结构
  ├─ 分析目录页 HTML 结构
  └─ 分析正文页 HTML 结构
  ↓
第三层：规则建议生成
  ├─ 基于 CMS 模板 + 页面结构
  ├─ 生成 CSS/XPath 规则建议
  └─ 输出规则 + 置信度 + 依据
  ↓
第四层：分页识别
  ├─ 识别分页结构
  └─ 生成 nextTocUrl/nextContentUrl 规则
  ↓
第五层：反爬策略识别（FR-15.5）
  ├─ 检测频率限制（429/503 响应码）
  ├─ 检测 IP 封禁（403 + 特定页面）
  ├─ 检测 UA 检测（响应内容随 UA 变化）
  └─ 输出反爬策略清单 + 规避建议
  ↓
第六层：网站结构变化检测（FR-15.6）
  ├─ 对比历史分析结果
  ├─ 检测选择器是否失效
  └─ 输出"网站结构已变化"警告 + 变化点清单
```

**实现**：

```python
# site_analyzer.py（新增）
def analyze_site(url):
    """网站结构智能分析"""
    # 1. 获取首页 HTML
    html = fetch_html(url)
    
    # 2. CMS 识别
    cms_type = identify_cms(html)
    if cms_type:
        template = load_cms_template(cms_type)
    
    # 3. 页面结构分析
    list_page = analyze_list_page(html)
    detail_page = analyze_detail_page(html)
    toc_page = analyze_toc_page(html)
    content_page = analyze_content_page(html)
    
    # 4. 规则建议生成
    rules = generate_rule_suggestions(
        template, list_page, detail_page, toc_page, content_page
    )
    
    # 5. 分页识别
    pagination = identify_pagination(html)
    
    # 6. 反爬策略识别（FR-15.5）
    anti_crawl = identify_anti_crawl(html, response)
    
    # 7. 网站结构变化检测（FR-15.6）
    structure_change = detect_site_structure_change(url, html)
    
    return {
        "cms_type": cms_type,
        "rules": rules,
        "pagination": pagination,
        "anti_crawl": anti_crawl,
        "structure_change": structure_change,
        "confidence": calculate_confidence(rules)
    }
```

**状态**：📋 待实施

### AD-19: 错误自动修复架构 — "分析 + 修复 + 验证 + 记录"

**决策**：错误场景采用自动修复策略，而非只输出修复建议。

**修复流程**：

```
规则错误
  ↓
第一层：错误分析
  ├─ CSS 选择器匹配 0 → 分析页面结构
  ├─ URL 返回空 → 分析 URL 结构
  ├─ 字段映射错误 → 分析字段位置
  └─ 语法错误 → 分析错误位置
  ↓
第二层：自动修复
  ├─ CSS 选择器：.nonexistent → .chapter-list
  ├─ URL 模板：参数缺失 → 补充参数
  ├─ 字段映射：作者↔简介 → 交换映射
  └─ 语法错误：JSONPath 语法 → 修正语法
  ↓
第三层：自动验证
  ├─ 修复后重新执行 debug-source.py
  └─ 通过 → 成功；失败 → 重试（最多 3 次）
  ↓
第四层：历史记录
  └─ 记录到 basic-memory（note_type=fix-history）
```

**实现**：

```python
# auto_fixer.py（新增）
def auto_fix_error(error, source_json, html):
    """错误自动修复"""
    fix_history = load_fix_history(error["type"])
    
    # 1. 优先尝试历史修复方案
    if fix_history:
        for fix in fix_history:
            fixed_json = apply_fix(source_json, fix)
            if verify_fix(fixed_json, html):
                record_fix_history(error, fix, success=True)
                return {"status": "success", "method": "history", "fixed_json": fixed_json}
    
    # 2. 分析错误并生成修复方案
    fix = analyze_and_generate_fix(error, html)
    
    # 3. 应用修复
    fixed_json = apply_fix(source_json, fix)
    
    # 4. 验证修复
    if verify_fix(fixed_json, html):
        record_fix_history(error, fix, success=True)
        return {"status": "success", "method": "auto", "fixed_json": fixed_json}
    
    # 5. 重试（最多 3 次）
    for i in range(3):
        fix = refine_fix(fix, error, html)
        fixed_json = apply_fix(source_json, fix)
        if verify_fix(fixed_json, html):
            record_fix_history(error, fix, success=True)
            return {"status": "success", "method": "retry", "fixed_json": fixed_json}
    
    record_fix_history(error, fix, success=False)
    return {"status": "failed", "suggestion": fix}
```

**状态**：📋 待实施

### AD-20: 用户交互优化架构 — "交互式引导 + 进度反馈"

**决策**：用户交互采用交互式引导策略，而非只输出建议。

**交互模式**：

```
检测到需要用户操作
  ↓
交互式引导
  ├─ 输出操作步骤（分步骤引导）
  ├─ 等待用户输入
  ├─ 验证用户输入
  └─ 成功 → 继续；失败 → 重新引导
  ↓
进度反馈
  ├─ 长时间操作时输出进度
  └─ "正在破盾...30%" "正在登录...50%"
```

**实现**：

```python
# interactive_guide.py（新增）
def guide_login(url):
    """交互式登录引导"""
    print(f"检测到 {url} 需要登录")
    print("请按以下步骤获取 Cookie：")
    print("1. 打开浏览器，访问", url)
    print("2. 按 F12 打开开发者工具")
    print("3. 切换到 Network 标签")
    print("4. 登录后刷新页面")
    print("5. 点击任意请求，复制 Cookie 头的值")
    print("6. 粘贴到这里（以 Cookie: 开头）：")
    
    cookie_str = input("> ")
    if validate_cookie_format(cookie_str):
        return parse_cookie_str(cookie_str)
    else:
        print("Cookie 格式无效，请重新输入")
        return guide_login(url)

def feedback_progress(action, progress):
    """进度实时反馈"""
    print(f"[{action}] {progress}%")
```

**状态**：📋 待实施

### AD-21: Cookie/Session 管理增强架构 — "文件持久化 + 跨网站复用"

**决策**：Cookie 管理从内存版升级为文件持久化版，支持跨会话复用。

**架构**：

```
MockCookieStore（内存版，现有）
  ↓ 升级
PersistentCookieStore（文件持久化版，新增）
  ├─ 内存缓存（ConcurrentHashMap）
  ├─ 文件持久化（tools/.cookie-cache/{domain}.json）
  ├─ 启动时自动加载
  ├─ 写入时自动持久化
  └─ 过期管理（expires/max-age）
```

**实现**：

```kotlin
class PersistentCookieStore(private val cacheDir: String = "tools/.cookie-cache") {
    private val cookieMap = ConcurrentHashMap<String, MutableMap<String, CookieEntry>>()
    
    data class CookieEntry(
        val value: String,
        val expires: Long? = null,  // null = 会话级
        val domain: String
    )
    
    init {
        // 启动时自动加载
        loadAllFromDisk()
    }
    
    fun getCookie(url: String): String {
        val domain = getSubDomain(url)
        cleanupExpired(domain)
        return cookieMap[domain]?.entries
            ?.joinToString("; ") { "${it.key}=${it.value.value}" } ?: ""
    }
    
    fun setCookie(url: String, cookie: String) {
        val domain = getSubDomain(url)
        val map = cookieMap.getOrPut(domain) { mutableMapOf() }
        cookie.split(";").forEach { pair ->
            val idx = pair.indexOf("=")
            if (idx > 0) {
                val key = pair.substring(0, idx).trim()
                val value = pair.substring(idx + 1).trim()
                map[key] = CookieEntry(value, domain = domain)
            }
        }
        saveToDisk(domain)  // 写入时自动持久化
    }
    
    private fun saveToDisk(domain: String) {
        val file = File(cacheDir, "$domain.json")
        file.parentFile?.mkdirs()
        file.writeText(gson.toJson(cookieMap[domain]))
    }
    
    private fun loadAllFromDisk() {
        val dir = File(cacheDir)
        if (!dir.exists()) return
        dir.listFiles { f -> f.extension == "json" }?.forEach { file ->
            val domain = file.nameWithoutExtension
            val map = gson.fromJson(file.readText(), typeOf<MutableMap<String, CookieEntry>>())
            cookieMap[domain] = map
        }
    }
    
    private fun cleanupExpired(domain: String) {
        val now = System.currentTimeMillis()
        cookieMap[domain]?.entries?.removeIf { entry ->
            entry.value.expires != null && entry.value.expires < now
        }
    }
}
```

**状态**：📋 待实施

### AD-22: 网络请求增强架构 — "自适应 + 代理池 + UA 池"

**决策**：网络请求从基础安全机制升级为智能自适应策略。

**增强内容**：

```
network_safety_interceptor.py（现有，基础）
  ↓ 升级
smart_http_client.py（新增，智能）
  ├─ 自适应重试（根据错误类型调整）
  ├─ 代理池支持（多个代理轮换）
  ├─ 频率自适应（429/503 降速）
  ├─ UA 池（随机选择）
  ├─ Referer 自动携带
  └─ 请求日志增强
```

**实现**：

```python
# smart_http_client.py（新增）
class SmartHttpClient:
    def __init__(self):
        self.ua_pool = load_ua_pool()
        self.proxy_pool = load_proxy_pool()
        self.request_interval = 1.0  # 默认 1 秒
        self.last_request_time = 0
        self.request_log = []
    
    def request(self, url, method="GET", headers=None, data=None, timeout=30):
        # 1. 频率控制
        self._wait_for_interval()
        
        # 2. UA 选择
        ua = random.choice(self.ua_pool)
        headers = headers or {}
        headers["User-Agent"] = ua
        headers["Referer"] = self._get_referer(url)
        
        # 3. 代理选择
        proxy = random.choice(self.proxy_pool) if self.proxy_pool else None
        
        # 4. 请求
        response = self._do_request(url, method, headers, data, timeout, proxy)
        
        # 5. 自适应
        if response.status_code in (429, 503):
            self.request_interval = min(self.request_interval * 2, 10.0)  # 降速
        elif response.status_code == 200:
            self.request_interval = max(self.request_interval * 0.9, 0.5)  # 加速
        
        # 6. 日志
        self.request_log.append({
            "url": url, "method": method, "status": response.status_code,
            "timestamp": time.time()
        })
        
        return response
    
    def _wait_for_interval(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request_time = time.time()
```

**状态**：📋 待实施

### AD-23: 知识库增强架构 — "特征库 + 方案库 + 自动匹配"

**决策**：知识库从静态文档升级为动态特征库+方案库，支持自动匹配。

**架构**：

```
references/（现有，静态知识）
  ↓ 增强
references/site-features/（新增，网站特征库）
  ├─ biquge.md（笔趣阁特征）
  ├─ wordpress-novel.md（WordPress 小说主题特征）
  └─ ...
references/solutions/（新增，解决方案库）
  ├─ login-cookie-import.md（登录 Cookie 导入方案）
  ├─ cf-cloudscraper.md（CF cloudscraper 破盾方案）
  ├─ crypto-aes-ecb.md（AES ECB 解密方案）
  └─ ...
basic-memory（现有，经验索引）
  ↓ 增强
basic-memory/site-features/（新增，特征索引）
basic-memory/solutions/（新增，方案索引）
```

**自动匹配实现**：

```python
# knowledge_matcher.py（新增）
def match_site_features(url, html):
    """自动匹配网站特征"""
    # 1. 提取网站特征
    features = extract_features(url, html)
    # features = {"domain": "biquge.com", "cms": "unknown", "encryption": "none"}
    
    # 2. 搜索特征库
    matches = []
    for feature_file in glob.glob("references/site-features/*.md"):
        stored_features = load_features(feature_file)
        similarity = calculate_similarity(features, stored_features)
        if similarity > 0.6:
            matches.append({"file": feature_file, "similarity": similarity})
    
    # 3. 按相似度排序
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    
    return matches

def match_solutions(problem_type, problem_details):
    """自动匹配解决方案"""
    # 1. 搜索方案库
    matches = []
    for solution_file in glob.glob("references/solutions/*.md"):
        solution = load_solution(solution_file)
        if solution["problem_type"] == problem_type:
            relevance = calculate_relevance(problem_details, solution)
            matches.append({"file": solution_file, "relevance": relevance})
    
    # 4. 按相关性排序
    matches.sort(key=lambda x: x["relevance"], reverse=True)
    
    return matches
```

**状态**：📋 待实施

---

## 2.6 查漏补缺（17 条深刻反思对照 — 全方位覆盖）

> **背景**：用户重新贴出 17 条深刻反思，要求"查漏补缺！不要遗漏任何细节！全方位查漏补缺！"。经逐条对照，发现 9 个遗漏项，归为 6 个架构决策（AD-24 到 AD-29）。

### AD-24: 设计哲学落地架构 — "脚本价值分类 + CLI 封装评估 + 高频优先 + 不实现清单"

**决策**：将反思错误 4/9/10 从"哲学层反思"落地为具体可执行的架构。

**脚本用户价值分类**：

```python
# scripts/classify_script_value.py（新增）
SCRIPT_CLASSIFICATION = {
    # 用户直接受益（优先维护）
    "user_benefit": [
        "debug-source.py",        # 端到端调试，验证规则是否正确
        "verify-decrypt.py",     # 验证解密，处理加密网站
        "verify-selector.py",    # 验证选择器，确保规则匹配
        "verify-image.py",       # 验证图片解密
        "html_fetcher.py",       # 获取 HTML，分析网站结构
        "site_type_detector.py", # 检测网站类型，给出准确规则
    ],
    # 方便 AI 但用户不受益（降低优先级或废弃）
    "ai_only": [
        "auto_evolve_server.py",     # 自动补全 Mock，用户不关心
        "speed_metrics.py",          # 记录执行速度，用户不关心
        "evolution_convergence.py",  # 防止无限进化，用户不关心
        "evolution_trigger.py",      # 分类错误，用户不关心
        "generate-js-doc.py",        # 生成文档，用户不关心
        "deep-analyze-js.py",        # 分析 JS，用户不关心
        "check_*.py",                # 检测问题，用户不关心
    ]
}
```

**仿真服务端模块定位评估**：

| 模块 | 当前定位 | 评估后定位 | 原因 |
|------|---------|-----------|------|
| AnalyzeUrl | 重新实现 | 保持重新实现 | 真机无 CLI 接口，必须重新实现 |
| AnalyzeRule | 重新实现 | 保持重新实现 | 真机无 CLI 接口，必须重新实现 |
| JsExtensions | 重新实现（120+ 函数） | 混合：高频重新实现 + 低频标记 unverifiable | 80% 函数用户用不到 |
| CookieStore | 重新实现 | 保持重新实现 | 真机 Cookie 管理无 CLI 接口 |
| Debugger | 重新实现 | 保持重新实现 | 真机 Debug 无 CLI 接口 |

**高频场景优先排序**：

| 优先级 | 差距 | 影响百分比 | 实现难度 |
|--------|------|-----------|---------|
| P0 | unescape | 100% | 低（1 行代码） |
| P0 | put/get 层级存储 | 90% | 中（委托机制） |
| P0 | NativeObject 处理 | 30% | 中（键值访问） |
| P0 | Mode.Regex | 20% | 中（新增 AnalyzeByRegex） |
| P1 | getSubDomain | 10% | 低（硬编码列表） |
| P1 | 重定向行为 | 10% | 低（改 true→false） |
| P1 | type 二进制 | 5% | 低（分支修正） |

**不实现清单（Do-Not-Implement List）**：

| # | 不实现项 | 原因 | 影响场景 |
|---|---------|------|---------|
| 1 | BackstageWebView | 需完整浏览器引擎，投入巨大 | webView 登录类书源 |
| 2 | importScript | 远程 JS 加载，安全风险高 | importScript 规则 |
| 3 | queryTTF/replaceFont | 字体反爬，场景极少 | 字体加密类书源 |
| 4 | 文件/压缩包操作 | 场景极少 | 下载类书源 |
| 5 | createAsymmetricCrypto | RSA 场景极少 | RSA 加密类书源 |

**状态**：📋 待实施

### AD-25: 三 Skill 协作"互相制约"验证架构

**决策**：三 Skill 协作从"单向背书"改为"双向制约"，通过注入错误验证检查点有效性。

**制约关系图**：

```
┌──────────────────────┐
│ legado-skill-auditor  │ ──制约──→ legado-source-creator 的质量
│                      │ ←─制约── legado-source-creator 注入错误验证 auditor 有效性
└──────────────────────┘
         ↑↓
┌──────────────────────┐
│ legado-workflow-auditor│ ──制约──→ 两者的执行完整性
│                      │ ←─制约── 两者注入缺失验证 auditor 有效性
└──────────────────────┘
```

**注入错误验证实现**：

```python
# scripts/validate_skill_checks.py（新增）
def inject_errors_and_validate(skill_name, check_points):
    """注入错误并验证检查点能否发现"""
    results = []
    for check in check_points:
        # 1. 制造错误（如陷阱数写错/字段不存在/文档不一致）
        error = create_injected_error(check["type"])
        # 2. 运行检查点
        detected = run_check(check, error)
        # 3. 记录结果
        results.append({
            "check_id": check["id"],
            "check_name": check["name"],
            "injected_error": error["description"],
            "detected": detected,
            "detection_rate": 1 if detected else 0
        })
    # 4. 统计命中率
    hit_rate = sum(r["detection_rate"] for r in results) / len(results)
    return {"results": results, "hit_rate": hit_rate}

# skill-auditor: 42 个检查点
auditor_results = inject_errors_and_validate("skill-auditor", AUDITOR_CHECK_POINTS)
# 预期：hit_rate >= 0.80

# workflow-auditor: 8 项检查
workflow_results = inject_errors_and_validate("workflow-auditor", WORKFLOW_CHECK_POINTS)
# 预期：hit_rate == 1.00
```

**状态**：📋 待实施

### AD-26: 质量保障增强架构 — "版本一致性 + 完成定义检查清单"

**决策**：将反思错误 12/13 落地为具体可执行的检查机制。

**版本一致性检查**：

```python
# scripts/check_version_consistency.py（新增）
VERSION_LOCKS = {
    "jsoup": "1.16.2",    # jsoup#2017 破坏性变更
    "rhino": "1.8.1",     # Android 6 以下缺少 Arrays.setAll
    "hutool": "5.8.22",   # 书源加解密依赖
    "okhttp": "4.12.0",   # HTTP 客户端
    "gson": "2.10.1",     # JSON 解析
}

def check_version_consistency():
    """检查 references/ 中的版本描述 vs build.gradle.kts 实际版本"""
    inconsistencies = []
    for lib, expected_version in VERSION_LOCKS.items():
        # 1. 从 build.gradle.kts 读取实际版本
        actual = read_version_from_gradle(lib)
        # 2. 从 references/ 读取文档中的版本
        documented = read_version_from_references(lib)
        # 3. 对比
        if actual != expected_version:
            inconsistencies.append(f"{lib}: build={actual}, expected={expected_version}")
        if documented != expected_version:
            inconsistencies.append(f"{lib}: references={documented}, expected={expected_version}")
    return inconsistencies  # 预期：空列表
```

**完成定义检查清单**：

```python
# scripts/verify_completion.py（新增）
COMPLETION_CHECKLIST = {
    "code_exists": lambda task: grep_code_exists(task["file"], task["function"]),
    "file_modified": lambda task: read_file_modified(task["file"], task["expected_change"]),
    "function_works": lambda task: run_command(task["verify_command"]),
    "design_aligned": lambda task: check_design_alignment(task["design_ref"]),
}

def verify_task_completion(task):
    """任务完成前必须执行的验证"""
    results = {}
    for check_name, check_func in COMPLETION_CHECKLIST.items():
        results[check_name] = check_func(task)
    all_passed = all(results.values())
    return {"passed": all_passed, "results": results}
```

**状态**：📋 待实施

### AD-27: 统一降级链架构 — "自动求解 → Cookie 导入 → 手动引导 → 标记 unverifiable"

**决策**：FR-11 到 FR-20 各自独立的辅助能力，统一为一条降级链。

**统一降级链架构**：

```python
# tools/degradation_chain.py（新增）
DEGRADATION_STEPS = [
    {"name": "auto_solve",    "description": "自动求解（cloudscraper/OCR/加密分析等）"},
    {"name": "cookie_import", "description": "Cookie 导入（从持久化存储或用户输入）"},
    {"name": "manual_guide",  "description": "手动引导（交互式引导用户操作）"},
    {"name": "mark_unverifiable", "description": "标记 unverifiable（最后手段）"},
]

def degrade(url, obstacle_type, context):
    """统一降级链"""
    log = []
    for step in DEGRADATION_STEPS:
        log.append({"step": step["name"], "status": "trying", "timestamp": now()})
        try:
            result = execute_step(step["name"], url, obstacle_type, context)
            if result["success"]:
                log.append({"step": step["name"], "status": "success", "result": result})
                return {"resolved": True, "method": step["name"], "log": log}
            else:
                log.append({"step": step["name"], "status": "failed", "reason": result["reason"]})
        except Exception as e:
            log.append({"step": step["name"], "status": "error", "error": str(e)})
    return {"resolved": False, "method": "unverifiable", "log": log}
```

**支持的障碍类型（obstacle_type）**：

| obstacle_type | 对应模块 | auto_solve 策略 | cookie_import 策略 | manual_guide 策略 |
|---------------|----------|----------------|-------------------|-------------------|
| `login` | login_assistant (7.1) | 表单自动填充 | Cookie 导入 | 交互式登录引导 |
| `cf` | cf_bypass (7.2) | cloudscraper 自动求解 | cf_clearance Cookie 导入 | 手动破盾引导 |
| `captcha` | captcha_assistant (7.3) | ddddocr OCR 识别 | Cookie 导入 | 图片导出手动识别 |
| `crypto` | crypto_analyzer (7.4) | 加密类型识别+解密代码生成 | — | 手动分析引导 |
| `anti_crawl` | site_analyzer (7.5.8) | UA 池切换+请求降速 | — | 代理池配置引导 |

**状态**：📋 待实施

### AD-28: 用户体验增强架构 — "耗时优化 + 错误友好化 + 进度反馈"

**决策**：将反思错误 14/15 落地为具体可执行的用户体验增强。

**工作流耗时统计**：

```python
# tools/workflow_timer.py（新增）
class WorkflowTimer:
    def __init__(self):
        self.phases = {}
    
    def start_phase(self, phase_name):
        self.phases[phase_name] = {"start": time.time()}
    
    def end_phase(self, phase_name):
        self.phases[phase_name]["end"] = time.time()
        self.phases[phase_name]["duration"] = self.phases[phase_name]["end"] - self.phases[phase_name]["start"]
    
    def report(self):
        total = sum(p["duration"] for p in self.phases.values())
        bottleneck = max(self.phases.items(), key=lambda x: x[1]["duration"])
        return {"total": total, "phases": self.phases, "bottleneck": bottleneck[0]}
```

**错误信息用户友好化**：

```python
# tools/error_translator.py（新增）
ERROR_TRANSLATIONS = {
    "TypeError: java.{func} is not a function": {
        "level": "致命",
        "user_message": "该功能（{func}）在仿真环境中暂不支持",
        "suggestions": [
            "在手机上直接测试此书源",
            "提供网站 URL 让 AI 分析是否可替代",
            "标记此功能为 unverifiable"
        ],
        "impact": "影响 {func} 相关功能，场景{frequency}"
    },
    "state: -1, msg: 网络请求失败": {
        "level": "严重",
        "user_message": "网络请求失败",
        "suggestions": ["检查网络连接", "检查 URL 是否正确", "检查是否被反爬拦截"],
        "impact": "影响所有网络请求"
    }
}

def translate_error(technical_error, context):
    """将技术错误翻译为用户友好信息"""
    for pattern, translation in ERROR_TRANSLATIONS.items():
        if pattern_matches(pattern, technical_error):
            return fill_template(translation, context)
    return {"level": "提示", "user_message": technical_error, "suggestions": []}
```

**状态**：📋 待实施

### AD-29: 用户操作最小化检查架构

**决策**：每次需要用户手工操作时，先评估是否可以自动化。

**用户操作最小化检查**：

```python
# tools/user_action_minimizer.py（新增）
AUTOMATION_ATTEMPTS = {
    "cookie_input": [
        {"method": "read_from_browser", "description": "尝试从浏览器自动读取 Cookie"},
        {"method": "read_from_cache", "description": "尝试从持久化存储读取 Cookie"},
        {"method": "prompt_user", "description": "引导用户手动输入 Cookie"}
    ],
    "captcha_input": [
        {"method": "ocr_recognize", "description": "尝试 OCR 识别验证码"},
        {"method": "export_and_prompt", "description": "导出图片引导用户识别"}
    ],
    "cf_bypass": [
        {"method": "cloudscraper", "description": "尝试 cloudscraper 自动破盾"},
        {"method": "prompt_user", "description": "引导用户手动破盾"}
    ]
}

def minimize_user_action(action_type, context):
    """最小化用户操作"""
    for attempt in AUTOMATION_ATTEMPTS.get(action_type, []):
        result = try_automation(attempt["method"], context)
        if result["success"]:
            return {"automated": True, "method": attempt["method"]}
    return {"automated": False, "fallback": "prompt_user"}
```

**状态**：📋 待实施

### AD-30: 真实测试验证优化修复架构 — "真实源验证 → 问题分类 → 优化修复 → 回归验证 → 经验反哺"

**决策**：前 8 个阶段都是"造工具/修工具"，阶段九用 `output/` 目录中已有的真实源进行端到端验证，形成闭环。

**真实源清单与覆盖场景**：

| 源文件 | 源名 | 覆盖场景 | 验证重点 |
|--------|------|---------|---------|
| `51cg_rss_source.json` | 51吃瓜网 | AES/CBC/PKCS5 图片加密 + DPlayer+m3u8 | FR-1.3 NativeObject + FR-1.4 unescape + 7.4 加密分析 |
| `611371056_rss_source.json` | 小黄书视频 | 双层 XOR+DES+AES-CFB + CF 盾 | 7.2 CF 破盾 + 7.4 加密分析 |
| `acgfta-anime-source.json` | 饭团动漫 | 苹果 CMS(maccms) + webViewGetSource + HLS.js | 7.5 网站结构分析 + webViewGetSource 仿真差距 |
| `jfg-video-source.json` | 机房哥视频 | AES-128-CBC+ZeroPadding 搜索加密 + Video.js | FR-1.6 type 二进制 + 7.4 加密分析 |
| `mjv006-video-source.json` | 18AV视频 | CookieJar 年龄确认 + webViewGetSource | 7.8 Cookie 管理 + webViewGetSource 仿真差距 |
| `优质资源-优化.json` | 1080zyk | 验证码识别 + CF 验证 + CookieJar | 7.3 验证码识别 + 7.2 CF 破盾 + 7.8 Cookie 管理 |

**闭环验证流程**：

```
真实源（output/rss/ + output/book/）
  ↓
第一层：端到端验证
  ├─ 逐一执行 debug-source.py --source {真实源}.json
  ├─ RSS 源：验证 sort→content 2 阶段
  ├─ 书源：验证 search→detail→toc→content 4 阶段
  └─ 记录结果（通过/部分通过/失败 + 失败原因）
  ↓
第二层：问题分类
  ├─ Bug：仿真服务端代码缺陷（加密函数缺失/type 处理错误等）
  ├─ 规则错误：书源/订阅源 JSON 规则有误（选择器/URL/字段映射）
  ├─ 仿真差距：仿真与真机行为不一致（webViewGetSource/CF 检测等）
  └─ 需用户介入：无法自动修复（OAuth 登录/复杂验证码等）
  ↓
第三层：优化修复
  ├─ Bug → 修复仿真服务端代码
  ├─ 规则错误 → 优化 JSON 规则
  ├─ 仿真差距 → 对齐仿真行为
  └─ 需用户介入 → 标记 unverifiable + 用户建议
  ↓
第四层：回归验证
  ├─ 修复后重新执行 debug-source.py
  ├─ 统计回归通过率（目标 >80%）
  └─ 未通过的记录原因
  ↓
第五层：经验反哺
  ├─ 输出完整验证报告
  ├─ 经验写入 basic-memory
  └─ 高频问题模式写入 references/site-features/
```

**状态**：📋 待实施

---

### 3.1 变量跨阶段传递修复后数据流

```
BookSourceDebugger.debugInfo()
  ├─ AnalyzeRule(mockJs, book=mockBook, source=mockSource)
  ├─ 执行 ruleBookInfo.init
  │    └─ JS: java.put("tocUrl", "https://example.com/toc")
  │         └─ MinimalMockJsExtensions.put("tocUrl", "...")
  │              └─ 委托到 mockBook.putVariable("tocUrl", "...")
  └─ → debugToc()
       ├─ AnalyzeRule(mockJs, book=mockBook, source=mockSource)
       ├─ 执行 ruleToc.tocUrl
       │    └─ @get:{tocUrl}
       │         └─ AnalyzeRule.get("tocUrl")
       │              └─ mockBook.getVariable("tocUrl") → "https://example.com/toc" ✅
       └─ AnalyzeUrl(tocUrl, ...) → 正确构造目录页 URL
```

### 3.2 真实书源回测数据流

```
用户执行: bash scripts/test-real-sources.sh

1. 选取 3 个真实书源 JSON
   ├─ simple-biquge.json（简单 CSS 规则）
   ├─ encrypted-novel.json（含 AES 加密）
   └─ paginated-novel.json（含分页目录）

2. 对每个书源执行
   └─ python scripts/debug-source.py --source {json} --key "搜索关键词"
       ├─ Step 0: 网站类型检测
       ├─ Step 1-6: 端到端调试（JVM）
       ├─ Step 7: 可信度评估
       └─ Step 8: 验证报告

3. 验收标准
   ├─ 4 阶段全部通过（search→detail→toc→content）
   ├─ 日志格式与真机一致
   ├─ 无 state=-1 错误
   └─ 可信度评估为"高"
```

---

## 4. File Changes（文件变更清单）

### 4.1 修改文件（Bug 修复）

| 文件路径 | 修改内容 | 行数变化 |
|---------|---------|---------|
| `MinimalMockJsExtensions.kt` | put/get 委托到 MockBook/MockSource；ajax 错误返回 stackTraceStr；get/head/post followRedirects(false) | +30 |
| `AnalyzeRule.kt` | NativeObject/LinkedTreeMap 处理；unescape；Mode.Regex 分支；Mode.Webjs 分支 | +80 |
| `AnalyzeUrl.kt` | type 二进制处理；XML 内容类型处理 | +30 |
| `MockCookieStore.kt` | getSubDomain 多段 TLD 支持 | +20 |
| `BookSourceDebugger.kt` | 变量持久化使用 MockBook/MockSource | +10 |
| `RssSourceDebugger.kt` | 同步传入 MockSource（对齐 BookSourceDebugger 修复） | +5 |
| `RuleEngineServer.kt` | evalJS 命令的 MockJsExtensions 创建逻辑更新（传入 MockBook/MockSource） | +10 |

### 4.2 修改文件（基础设施整改）

| 文件路径 | 修改内容 | 行数变化 |
|---------|---------|---------|
| `deep-verify.py` | 移除 deprecated 标记，更新定位说明 | +5 |
| `quick-verify.py` | 移除硬编码 BASE_DIR | +2 -2 |
| `classify-and-fix.py` | 移除硬编码 BASE_DIR；实现真正的 fix | +20 -2 |
| `evolution_trigger.py` | 函数名对齐 | +2 -2 |
| `evolution_convergence.py` | 函数名对齐 | +2 -2 |
| `auto_evolve_server.py` | 增加行为验证步骤 | +15 |
| `speed_metrics.py` | 增加自动埋点接口 | +10 |
| `debug-source.py` | 调用自动埋点；函数名引用更新 | +5 |
| `SKILL.md` | 补充 check_health.py 索引；精简至 <500 行 | -50 +10 |

### 4.3 新增文件（测试验证）

| 文件路径 | 行数估计 | 职责 |
|---------|---------|------|
| `tools/mvp1-build/src/main/kotlin/.../AnalyzeByRegex.kt` | ~50 | 正则规则解析器 |
| `tools/mvp1-build/src/test/kotlin/.../AnalyzeUrlTest.kt` | ~150 | AnalyzeUrl 单元测试 |
| `tools/mvp1-build/src/test/kotlin/.../MockCookieStoreTest.kt` | ~100 | MockCookieStore 单元测试 |
| `tools/mvp1-build/src/test/kotlin/.../AnalyzeRuleTest.kt` | ~200 | AnalyzeRule 单元测试 |
| `tools/mvp1-build/src/test/kotlin/.../MinimalMockJsExtensionsTest.kt` | ~150 | MockJsExtensions 单元测试 |
| `scripts/check_health.py` | ~30 | 三合一健康检查 |
| `scripts/test-real-sources.sh` | ~50 | 真实书源回测脚本 |

### 4.4 新增文件（减少用户手工操作 — 阶段七）

| 文件路径 | 行数估计 | 职责 | 对应 FR/AD |
|---------|---------|------|-----------|
| `tools/login_assistant.py` | ~200 | 登录场景主动辅助（Cookie 导入/表单登录/OAuth 标记） | FR-11 / AD-14 |
| `tools/cf_bypass.py` | ~150 | CF 盾破盾辅助（cloudscraper 自动求解/Cookie 导入降级） | FR-12 / AD-15 |
| `tools/captcha_assistant.py` | ~120 | 验证码识别辅助（OCR 识别/图片导出降级） | FR-13 / AD-16 |
| `tools/crypto_analyzer.py` | ~250 | 加密自动分析（JS 扫描/密钥提取/模式判断/代码生成） | FR-14 / AD-17 |
| `tools/site_analyzer.py` | ~300 | 网站结构智能分析（CMS 识别/页面分析/规则建议） | FR-15 / AD-18 |
| `tools/auto_fixer.py` | ~250 | 错误自动修复（CSS/URL/字段/语法修复+历史学习） | FR-16 / AD-19 |
| `tools/interactive_guide.py` | ~150 | 用户交互优化（交互式引导+进度反馈） | FR-17 / AD-20 |
| `tools/smart_http_client.py` | ~200 | 网络请求增强（自适应重试+代理池+UA 池） | FR-19 / AD-22 |
| `tools/knowledge_matcher.py` | ~150 | 知识库增强（特征匹配+自动更新） | FR-20 / AD-23 |
| `references/site-features/` | ~500 | 网站特征库（CMS 类型/加密方式/反爬策略等 20+ 特征） | FR-20.1 |
| `references/solutions/` | ~400 | 解决方案库（登录/CF/验证码/加密等 10+ 方案） | FR-20.2 |

### 4.5 修改文件（减少用户手工操作 — 阶段七）

| 文件路径 | 修改内容 | 行数变化 | 对应 FR/AD |
|---------|---------|---------|-----------|
| `MockCookieStore.kt` | 新增 PersistentCookieStore 类（文件持久化+跨网站复用+过期管理） | +120 | FR-18 / AD-21 |
| `RuleEngineServer.kt` | 新增 manageCookie 命令（list/get/set/delete/clear） | +50 | FR-18.5 |
| `debug-source.py` | 集成所有辅助能力（登录/CF/验证码/加密/网站分析/自动修复/交互引导/知识库匹配） | +200 | FR-11~FR-20 |
| `verify-decrypt.py` | 集成加密自动分析（scan_crypto_calls/extract_key/generate_decrypt_code） | +80 | FR-14 |
| `MinimalMockJsExtensions.kt` | 补齐 hutool 加密算法（PBE/RC4/Blowfish 等） | +60 | FR-14.5 |

### 4.6 新增文件（查漏补缺 — 阶段八）

| 文件路径 | 行数估计 | 职责 | 对应 FR/AD |
|---------|---------|------|-----------|
| `scripts/classify_script_value.py` | ~80 | 脚本用户价值分类（13 个脚本分类+优先级） | FR-21.1 / AD-24 |
| `scripts/check_version_consistency.py` | ~100 | 版本一致性检查（jsoup/rhino/hutool 等） | FR-23.1/23.2 / AD-26 |
| `scripts/verify_completion.py` | ~120 | 完成定义检查清单（代码存在/文件修改/功能可用/设计对齐） | FR-23.3 / AD-26 |
| `scripts/validate_skill_checks.py` | ~200 | 三 Skill 检查点有效性验证（注入错误+命中率统计） | FR-22.1~22.5 / AD-25 |
| `tools/degradation_chain.py` | ~150 | 统一降级链（自动求解→Cookie导入→手动引导→标记unverifiable） | FR-24.1~24.4 / AD-27 |
| `tools/degradation_config.json` | ~30 | 降级链配置文件（支持自定义降级链顺序） | FR-24.4 / AD-27 |
| `tools/workflow_timer.py` | ~80 | 工作流耗时统计（5 阶段耗时+瓶颈分析） | FR-25.1 / AD-28 |
| `tools/error_translator.py` | ~120 | 错误信息用户友好化（技术错误→用户语言+分级） | FR-25.2/25.3 / AD-28 |
| `tools/user_action_minimizer.py` | ~100 | 用户操作最小化检查（自动化尝试→手动降级） | FR-25.5 / AD-29 |
| `scripts/analyze_real_source_results.py` | ~100 | 真实源验证结果分析与问题分类（Bug/规则错误/仿真差距/需用户介入） | FR-26.3 / AD-30 |
| `scripts/generate_verification_report.py` | ~80 | 验证报告生成（源数/通过率/失败原因/修复记录/回归结果） | FR-26.5 / AD-30 |

### 4.7 总工作量估计

| 类型 | 文件数 | 行数估计 |
|------|--------|---------|
| 修改 Kotlin（Bug 修复） | 7 | +185 |
| 修改 Python（整改） | 9 | +50 -10 |
| 修改 Markdown | 1 | -40 |
| 新增 Kotlin | 1 | ~50 |
| 新增 Kotlin 测试 | 4 | ~600 |
| 新增 Python/Shell | 2 | ~80 |
| 新增 Python（阶段七辅助能力） | 9 | ~1770 |
| 新增 Markdown（阶段七知识库） | 2 目录 | ~900 |
| 修改 Kotlin（阶段七 Cookie 持久化+加密扩展） | 3 | +230 |
| 修改 Python（阶段七集成辅助能力） | 2 | +280 |
| 新增 Python/JSON（阶段八查漏补缺） | 9 | ~980 |
| 新增 Python（阶段九真实测试验证） | 2 | ~180 |
| **总计** | 49 | ~5220 |

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 变量持久化修复破坏现有行为 | 中 | 高 | 修复后运行现有测试 + 真实书源回测 |
| getSubDomain 硬编码列表遗漏 | 低 | 中 | 覆盖常见 50+ 多段 TLD，后续可扩展 |
| NativeObject 处理引入新 bug | 低 | 中 | 单元测试覆盖 NativeObject + LinkedTreeMap |
| AnalyzeByRegex 实现与真机不一致 | 中 | 中 | 对比真机 AnalyzeByRegex 源码 |
| 真实书源回测网站不可用 | 中 | 低 | 选取 3 个稳定网站 + 备选网站 |
| 函数名变更破坏现有调用 | 低 | 中 | Grep 全局搜索旧函数名，全部更新 |
| cloudscraper 库不可用或破盾失败 | 高 | 中 | 自动破盾失败时降级到 Cookie 导入，输出可操作建议 |
| ddddocr 库识别准确率不足 | 中 | 低 | OCR 失败时导出图片让用户手动识别 |
| 加密自动分析误判加密类型 | 中 | 中 | 输出识别置信度 + 识别依据，低置信度时标记需人工 |
| 网站结构分析规则建议不可用 | 中 | 中 | 输出多条建议（含置信度），用户可选择 |
| 错误自动修复陷入死循环 | 低 | 高 | 最多重试 3 次，3 次失败后停止并记录 |
| Cookie 持久化文件损坏 | 低 | 中 | JSON 格式校验 + 损坏时降级到内存版 |
| 代理池不可用 | 中 | 低 | 代理失败时降级到直连，输出警告 |
| 知识库匹配误判相似案例 | 中 | 低 | 输出相似度分数，低相似度时不自动应用 |
| 新增依赖（cloudscraper/ddddocr）增加安装复杂度 | 中 | 低 | 设为可选依赖，未安装时降级到手动模式 |

---

## 6. 测试策略

### 6.1 单元测试

| 模块 | 测试内容 | 用例数 |
|------|---------|--------|
| AnalyzeUrl | 三步流水线 + UrlOption + 错误码 + type 二进制 | 12 |
| MockCookieStore | 二级域名 + 多段 TLD + Cookie 合并 + removeCookie | 8 |
| AnalyzeRule | NativeObject + LinkedTreeMap + unescape + Mode.Regex + put/get 层级 | 15 |
| MockJsExtensions | ajax + connect + 加密函数 + put/get 委托 | 10 |

### 6.2 集成测试

| 场景 | 测试内容 |
|------|---------|
| 简单书源端到端 | 4 阶段全部通过 |
| 含加密的书源端到端 | 解密成功，正文可读 |
| 失败阶段定位 | 精确定位到失败阶段 |
| 变量链传递 | 变量跨阶段传递成功 |
| 订阅源端到端 | 2 阶段全部通过 |

### 6.3 真实回测

| 用例 | 类型 | 预期 |
|------|------|------|
| 简单笔趣阁书源 | CSS 规则 | 4 阶段通过 |
| 含 AES 加密书源 | 加密规则 | 解密成功 |
| 含分页目录书源 | 分页规则 | 章节完整 |
| 普通视频订阅源 | RSS 规则 | 2 阶段通过 |
| 含加密订阅源 | 加密 RSS | 解密成功 |

### 6.4 减少用户手工操作测试（阶段七新增）

| 场景 | 测试内容 | 预期 |
|------|---------|------|
| 登录场景辅助 | 用户提供 Cookie 后能正常返回内容 | 登录态请求成功 |
| CF 盾破盾 | 简单 CF Challenge 能自动通过 | 破盾成功，内容正常返回 |
| 验证码识别 | 简单图形验证码能 OCR 识别 | 识别准确率 >60% |
| 加密自动分析 | AES/DES/Base64 加密能自动识别 | 输出加密类型+密钥+解密代码 |
| 网站结构分析 | 常见 CMS 能正确识别 | 输出 CMS 类型+规则建议 |
| 错误自动修复 | CSS 选择器错误能自动修复 | 3 次内修复成功 |
| Cookie 持久化 | JVM 重启后 Cookie 不丢失 | 自动加载持久化 Cookie |
| 网络请求自适应 | 检测到 429 时自动降速 | 请求频率自适应 |
| 知识库匹配 | 遇到新网站能匹配相似案例 | 输出匹配案例路径 |

---

## 7. 自我反省记录（深刻版）

> 本章节记录实施过程中的偷懒和错误抉择，作为后续避免的教训。分为三层：技术实现层、设计哲学层、价值验证层。

### 7.1 技术实现层：偷懒导致的致命 bug

| # | 偷懒行为 | 后果 | 正确做法 | 防止措施 |
|---|---------|------|---------|---------|
| 1 | `java.put()` 存到独立 variableMap 而非委托 | 跨阶段变量传递失效 | 委托到 AnalyzeRule/AnalyzeUrl 的 put | 实现后必须用真实书源测试变量链 |
| 2 | getSubDomain 用 `takeLast(2)` | 多段 TLD Cookie 失效 | 使用 PublicSuffixDatabase 或硬编码列表 | 实现后必须测试 .co.uk 等多段 TLD |
| 3 | NativeObject/LinkedTreeMap 标记完成但未实现 | JS 返回对象解析失败 | 认真实现每个 REQ | 标记完成前必须 Grep 确认代码存在 |
| 4 | unescape 漏看真机源码 | 正文残留 HTML 实体 | 逐行对比真机 getString | 实现后必须对比真机日志 |
| 5 | Mode.Regex 未实现 | 正则规则书源无法解析 | 新增 AnalyzeByRegex | 实现后必须测试 @regex: 规则 |
| 6 | type 二进制处理两个分支都走字符串 | 图片/字体下载返回错误 | type 非空时返回 hex 编码 | 实现后必须测试二进制 URL |
| 7 | 重定向行为 followRedirects(true) 与真机相反 | 依赖重定向拦截的书源行为不同 | followRedirects(false) | 实现后必须对比真机行为 |

### 7.2 设计哲学层：根本性错误

| # | 错误 | 后果 | 正确做法 | 防止措施 |
|---|------|------|---------|---------|
| 1 | 把"复刻 Legado"当目标 | 80% Mock 函数用户用不到，20% 高频函数有 bug | 以"用户使用频率"为导向 | 优先实现高频场景 |
| 2 | 自进化方向是"补全 Mock" | 进化终点是"Mock 补全了"而非"用户问题解决了" | 进化方向是"自动修复书源规则" | 进化终点必须对齐用户目标 |
| 3 | 测试策略只测 happy path | 无法发现"仿真通过但手机报错" | 补充负面测试 | 必须有 unhappy path 测试 |
| 4 | 7 个价值层面空架子 | 代码能跑但不解决问题 | 提升或废弃 | 每个脚本必须有真实价值 |
| 5 | 仿真服务端变成"必须依赖" | JVM 不可用时工作流中断 | 降为"可选工具" | 必须有降级路径 |
| 6 | 重新实现了一遍 Legado | 维护成本高、一致性难保证 | 定位为"真机 Debug 的 CLI 封装" | 不追求 100% 覆盖 |
| 7 | 知识库 40+ 文档很少查阅 | 知识库与代码脱节 | 强制查阅机制 | Phase 2 必须查阅陷阱清单 |
| 8 | "完成"=代码写完 | 测试 0%、回测 0% | "完成"=代码+测试+文档+回测 | 完成前必须全部验证 |

### 7.3 价值验证层：根本缺失

| # | 缺失 | 后果 | 正确做法 | 防止措施 |
|---|------|------|---------|---------|
| 1 | 从未验证 Skill 为用户创造的真实价值 | 不知道生成书源的成功率 | 用真实书源回测验证 | 必须有成功率统计 |
| 2 | 从未站在用户角度体验工作流 | 不知道用户体验如何 | 端到端体验完整工作流 | 必须有用户体验报告 |
| 3 | 从未对比仿真通过 vs 手机可用 | 核心假设未验证 | 仿真通过的书源导入手机验证 | 必须有对比报告 |

### 7.4 "懒原则"被误用的反思

| # | 误用 | 实际是 | 正确理解 |
|---|------|--------|---------|
| 1 | getSubDomain 用 `takeLast(2)` | 敷衍 | 懒 = 不写不必要的代码，不是写了但不写完整 |
| 2 | auto_evolve_server 生成 stub mock | 敷衍 | 懒 = 全生命周期高效，不是省略关键步骤 |
| 3 | speed_metrics 手动触发 | 敷衍 | 懒 = 自动化，不是让用户手动操作 |
| 4 | NativeObject 标记完成但未实现 | 欺骗 | 懒 = 诚实面对能力边界，不是假装完成 |

### 7.5 "必须人工干预边界"过于消极的反思（新增 — 用户最新诉求）

> **核心反思**：原有设计（skill-trio FR-10 + test-infra 场景2/3 + v2 FR-5.2/5.3）都是"检测到→标记→停止"的消极模式，没有主动辅助用户解决问题。

| # | 消极设计 | 后果 | 积极改造 | 对应 FR |
|---|---------|------|---------|---------|
| 1 | 检测到登录需求→标记 unverifiable | 用户必须手动写 loginUrl，或放弃 | Cookie 导入优先→表单登录辅助→OAuth 标记 | FR-11 |
| 2 | 检测到 CF 盾→标记 unverifiable | 用户必须手动破盾，或放弃 | cloudscraper 自动破盾→Cookie 导入降级 | FR-12 |
| 3 | 检测到验证码→标记 unverifiable | 用户必须手动识别，或放弃 | OCR 识别→图片导出手动识别 | FR-13 |
| 4 | 加密内容→手动分析 | 用户必须手动分析加密方式 | JS 扫描+密钥提取+代码生成 | FR-14 |
| 5 | 网站结构→手动写规则 | 用户必须从零开始写规则 | CMS 识别+结构分析+规则建议 | FR-15 |
| 6 | 规则错误→报错停止 | 用户必须手动定位和修复 | 自动修复+历史学习+循环验证 | FR-16 |
| 7 | 用户交互→无引导 | 用户不知道该做什么 | 交互式引导+进度反馈 | FR-17 |
| 8 | Cookie 管理→内存版 | JVM 重启后丢失，用户需重新登录 | 文件持久化+跨网站复用 | FR-18 |
| 9 | 网络请求→简单 requests | 容易触发限流/IP 封禁 | 自适应+代理池+UA 池 | FR-19 |
| 10 | 知识库→被动查阅 | 遇到新网站从零开始 | 主动匹配+自动更新 | FR-20 |

**根本原因**：把"减少用户手工操作"当成了"超出范围"，而非"核心价值"。

**正确理解**：Skill 的终极目标是"为用户提供手机端导入直接使用的书源和订阅源"，任何需要用户手工操作的环节，都应该尝试主动辅助，辅助失败再标记需人工。

### 7.6 17 条深刻反思查漏补缺（新增 — 用户最新诉求）

> **核心反思**：用户重新贴出 17 条深刻反思，要求"查漏补缺！不要遗漏任何细节！全方位查漏补缺！"。经逐条对照当前 spec.md/design.md，发现 9 个遗漏项。

| # | 遗漏项 | 对应反思 | 严重度 | 补充方案 | 对应 FR/AD |
|---|--------|---------|--------|---------|-----------|
| GAP-1 | 缺少"脚本用户价值分类" | 错误 4（自进化自嗨） | 🔴 严重 | 13 个脚本区分"用户受益"vs"AI 自嗨"，据此调整维护优先级 | FR-21.1 / AD-24 |
| GAP-2 | 缺少"CLI 封装 vs 重新实现"评估 | 错误 9（造轮子） | 🟠 中等 | 评估 5 个核心模块的定位（重新实现/封装/混合） | FR-21.2 / AD-24 |
| GAP-3 | 缺少"不实现清单"+影响百分比排序 | 错误 10（全覆盖策略） | 🔴 严重 | 明确 5 个不实现项+7 个差距按影响百分比排序 | FR-21.3/21.4/21.5 / AD-24 |
| GAP-4 | FR-8.3 版本一致性太简略 | 错误 12（知识库脱节） | 🟠 中等 | 具体化 5 个版本号对比+完成定义检查清单 | FR-23.1~23.5 / AD-26 |
| GAP-5 | 缺少"完成定义检查清单" | 错误 13（完成定义） | 🔴 严重 | 每个任务完成前执行四项验证 | FR-23.3 / AD-26 |
| GAP-6 | 缺少"错误信息用户友好翻译" | 错误 15（错误不可操作） | 🟠 中等 | 技术错误→用户语言+修复建议+分级 | FR-25.2/25.3 / AD-28 |
| GAP-7 | 三 Skill 协作"互相背书"问题完全未覆盖 | 错误 16（互相背书） | 🔴🔴 致命 | 注入错误验证检查点有效性+防止互相背书机制 | FR-22.1~22.5 / AD-25 |
| GAP-8 | 缺少"统一降级链"架构 | 全流程自动化辅助 | 🔴 严重 | 所有障碍场景遵循统一降级路径 | FR-24.1~24.4 / AD-27 |
| GAP-9 | 缺少"工作流耗时优化" | 错误 14（未体验工作流） | 🟡 提示 | 5 阶段耗时统计+瓶颈分析+优化建议 | FR-25.1 / AD-28 |

**根本原因**：前四层反思虽然覆盖了技术实现、设计哲学、价值验证、用户手工操作四个层面，但仍有 9 个遗漏项未覆盖。这些遗漏项中，GAP-7（三 Skill 互相背书）是最严重的——如果检查点本身无效，那么所有"通过审查"的结论都不可信。

**关键教训**：
1. **反思不能只做一轮**：第一轮反思发现 7 个致命 bug + 8 个设计哲学错误 + 3 个价值缺失 + 10 个用户操作问题，但第二轮反思又发现 9 个遗漏项。反思需要多轮迭代。
2. **"互相背书"是最隐蔽的问题**：三 Skill 协作看起来是"互相制约"，但如果检查点本身从未被验证过有效性，就可能变成"互相背书"。必须通过注入错误来验证检查点有效性。
3. **"不实现清单"和"实现清单"同样重要**：明确列出"不实现什么"可以防止 scope creep，避免在低频场景上浪费精力。
4. **"统一降级链"是架构层面的遗漏**：FR-11 到 FR-20 各自独立的辅助能力，如果没有统一降级链，会导致代码重复、行为不一致。

### 7.7 防止措施总结（升级版）

1. **实现后必须验证**：每个"已完成"的任务必须用工具验证（Read/Grep/RunCommand）
2. **必须对比真机源码**：每个修复必须逐行对比真机对应函数
3. **必须用真实数据回测**：禁止用 mock 数据回测，必须用真实网站
4. **必须同步文档**：新增文件必须立即更新 SKILL.md 索引
5. **必须遵循设计文档**：函数名、文件路径、行数必须对齐设计文档
6. **必须有负面测试**：只测 happy path 的测试是"自嗨式测试"
7. **必须有降级路径**：任何"必须依赖"的工具都必须有降级方案
8. **必须有价值验证**：代码能跑 ≠ 能解决问题，必须验证真实价值
9. **必须站在用户角度**：一直在"造工具"而非"用工具"是最大的偷懒
10. **懒原则不是敷衍**：懒 = 全生命周期高效，绝非敷衍潦草
11. **必须积极辅助优先**（新增）：检测到障碍时，先尝试主动辅助，辅助失败再标记需人工
12. **必须减少用户手工操作**（新增）：任何需要用户手工操作的环节，都应该尝试主动辅助
13. **必须验证检查点有效性**（查漏补缺新增）：三 Skill 协作的检查点必须通过注入错误验证，防止"互相背书"
14. **必须有"不实现清单"**（查漏补缺新增）：明确列出"不实现什么"，防止 scope creep
15. **必须有"完成定义检查清单"**（查漏补缺新增）：每个任务完成前执行四项验证（代码存在/文件修改/功能可用/设计对齐）
16. **必须有"统一降级链"**（查漏补缺新增）：所有障碍场景遵循统一降级路径，降级过程可追踪、可配置
17. **必须统计工作流耗时**（查漏补缺新增）：5 阶段工作流每阶段记录耗时，识别瓶颈并优化
18. **必须错误信息用户友好化**（查漏补缺新增）：技术错误翻译为用户可理解的语言+修复建议+分级
