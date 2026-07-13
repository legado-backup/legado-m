# P1-D Rhino JSON.parse 问题分析

> 分析日期：2026-07-13
> 数据来源：`temp/tmp/Downloadslogs5/` 07-12/07-13 真机日志
> 问题等级：P1-D（功能降级，不崩溃，但影响封面加载与书源可用性）

## 1. 日志证据

### 1.1 核心错误（appLog-26-07-12_23-11-23.884.txt:28-41，记录数最多 18 条）

```
26-07-12 23:11:29.570: AppLog 执行请求头规则出错
com.script.ScriptException: org.mozilla.javascript.EcmaError: SyntaxError: Empty JSON string (<Unknown source>#43) in <Unknown source> at line number 43
com.script.ScriptException: org.mozilla.javascript.EcmaError: SyntaxError: Empty JSON string (<Unknown source>#43) in <Unknown source> at line number 43
	at com.script.rhino.RhinoScriptEngine.eval(RhinoScriptEngine.kt:113)
	at com.script.AbstractScriptEngine.eval(AbstractScriptEngine.kt:58)
	at com.script.AbstractScriptEngine.eval(AbstractScriptEngine.kt:66)
	at io.legado.app.data.entities.BaseSource$-CC.$default$evalJS(BaseSource.kt:342)
	at io.legado.app.data.entities.RssSource.evalJS(RssSource.kt:14)
	at io.legado.app.data.entities.BaseSource$-CC.evalJS$default(BaseSource.kt:325)
	at io.legado.app.data.entities.BaseSource$-CC.$default$getHeaderMap(BaseSource.kt:109)
	at io.legado.app.data.entities.RssSource.getHeaderMap(RssSource.kt:14)
	at io.legado.app.model.analyzeRule.AnalyzeUrl.<init>(AnalyzeUrl.kt:135)
	at io.legado.app.model.analyzeRule.AnalyzeUrl.<init>(AnalyzeUrl.kt:81)
	at io.legado.app.help.glide.OkHttpStreamFetcher.loadData(OkHttpStreamFetcher.kt:78)
	...
Caused by: org.mozilla.javascript.EcmaError: SyntaxError: Empty JSON string (<Unknown source>#43)
	at org.mozilla.javascript.ScriptRuntime.constructError(ScriptRuntime.java:5235)
	at org.mozilla.javascript.ScriptRuntime.constructError(ScriptRuntime.java:5216)
	at org.mozilla.javascript.NativeJSON.parse(NativeJSON.java:91)
	at org.mozilla.javascript.NativeJSON.parse(NativeJSON.java:68)
```

### 1.2 错误分布统计

| 日志文件 | 记录数 | 触发行号 | 时间段 |
|---------|--------|---------|--------|
| `appLog-26-07-12_23-11-23.884.txt` | 18 | #43 / #26 | 23:11~23:13 |
| `appLog-26-07-12_14-46-07.609.txt` | 6 | #32 | 14:46~14:47 |
| `appLog-26-07-12_22-58-56.891.txt` | 4 | #43 / #26 | 23:06~23:07 |
| `logcat.txt` | 5（sourceDebug 注入 JS） | — | 14:54~14:55 |

> 触发行号 #32 / #43 / #26 不一致，说明多个 RssSource 的 header JS 规则都存在此问题（不同书源 JS 行号不同）。

### 1.3 触发时机规律

所有错误均发生在 `LifecycleHelp MainActivity onResume` 或 `WelcomeActivity onDestroy` 之后立即触发，且调用栈包含 Glide 线程池（`GlideExecutor$DefaultThreadFactory`）→ 说明是 **Activity 恢复时 Glide 加载 RssSource 封面图片** 触发的。

### 1.4 logcat.txt 中的对照证据（行 24947，sourceDebug 标签）

```
07-13 14:54:59.974  3912 13470 D sourceDebug:         const jsonLdElement = document.getElementById('videoData');
07-13 14:54:59.974  3912 13470 D sourceDebug:         if (dateElement && jsonLdElement) {
07-13 14:54:59.974  3912 13470 D sourceDebug:             ...
07-13 14:54:59.974  3912 13470 D sourceDebug:                 try {
07-13 14:54:59.974  3912 13470 D sourceDebug:                     jsonLdData = JSON.parse(jsonLdElement.textContent);
```

> 注意：logcat 中这段 `JSON.parse(jsonLdElement.textContent)` 是 **WebView 注入的页面 JS**（视频详情页脚本），不是 header 规则 JS。两者是不同场景的 JSON.parse 调用，但都暴露同一类问题：**书源/页面 JS 代码未对空字符串做容错判断**。本报告聚焦 appLog 中的"执行请求头规则出错"（header JS 场景）。

## 2. 源码定位

### 2.1 关键文件与行号

| 文件 | 行号 | 作用 |
|------|------|------|
| [`BaseSource.kt:104-133`](../../app/src/main/java/io/legado/app/data/entities/BaseSource.kt) | 104-133 | `getHeaderMap()` —— header 规则解析入口，**catch 块静默吞掉异常** |
| [`BaseSource.kt:325-343`](../../app/src/main/java/io/legado/app/data/entities/BaseSource.kt) | 325-343 | `evalJS()` —— JS 执行入口，直接调 `RhinoScriptEngine.eval` |
| [`RssSource.kt:14`](../../app/src/main/java/io/legado/app/data/entities/RssSource.kt) | 14 | `@Parcelize` 注解行，编译生成 `$default$evalJS` / `$default$getHeaderMap` |
| [`AnalyzeUrl.kt:130-145`](../../app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt) | 130-145 | `init` 块调用 `source?.getHeaderMap(hasLoginHeader)` |
| [`OkHttpStreamFetcher.kt:78`](../../app/src/main/java/io/legado/app/help/glide/OkHttpStreamFetcher.kt) | 78 | Glide 加载图片入口，构造 `AnalyzeUrl` |
| [`RhinoScriptEngine.kt:106-115`](../../modules/rhino/src/main/java/com/script/rhino/RhinoScriptEngine.kt) | 106-115 | RhinoException → ScriptException 转换点 |
| [`AnalyzeRule.kt:843-874`](../../app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt) | 843-874 | `AnalyzeRule.evalJS()`（另一版本，规则解析用） |

### 2.2 完整调用链

```
Glide 加载 RssSource 封面
  └─ OkHttpStreamFetcher.loadData(OkHttpStreamFetcher.kt:78)
     └─ AnalyzeUrl.<init>(AnalyzeUrl.kt:81) → init 块(AnalyzeUrl.kt:135)
        └─ RssSource.getHeaderMap()  →  BaseSource.$default$getHeaderMap(BaseSource.kt:109)
           │  header 字段以 "@js:" 或 "<js>" 开头 → 触发 evalJS
           └─ BaseSource.evalJS(jsStr)  (BaseSource.kt:325)
              └─ RhinoScriptEngine.eval(jsStr, scope)  (BaseSource.kt:342)
                 └─ cx.evaluateReader  (RhinoScriptEngine.kt:105)
                    └─ 书源 JS 内部调用 JSON.parse("")
                       └─ NativeJSON.parse(NativeJSON.java:91)
                          └─ 抛出 EcmaError: SyntaxError: Empty JSON string
                             └─ RhinoScriptEngine.kt:113 包装为 ScriptException 抛出
                                └─ 被 BaseSource.kt:121 catch 捕获
                                   └─ AppLog.put("执行请求头规则出错\n$e", e)  ← 静默吞掉，调用者无感知
```

### 2.3 关键源码片段（BaseSource.kt:104-133）

```kotlin
fun getHeaderMap(hasLoginHeader: Boolean = false) = HashMap<String, String>().apply {
    header?.let {
        try {
            val json = when {
                it.startsWith("@js:", true) -> evalJS(it.substring(4)).toString()
                it.startsWith("<js>", true) -> evalJS(
                    it.substring(4, it.lastIndexOf("<"))
                ).toString()
                else -> it
            }
            GSONStrict.fromJsonObject<Map<String, String>>(json).getOrNull()?.let { map ->
                putAll(map)
            } ?: GSON.fromJsonObject<Map<String, String>>(json).getOrNull()?.let { map ->
                log("请求头规则 JSON 格式不规范，请改为规范格式")
                putAll(map)
            }
        } catch (e: Exception) {
            AppLog.put("执行请求头规则出错\n$e", e)   // ← 第122行：静默吞掉
        }
    }
    if (!has(AppConst.UA_NAME, true)) {
        put(AppConst.UA_NAME, AppConfig.userAgent)   // ← 兜底默认 UA
    }
    ...
}
```

## 3. 根因分析

### 3.1 直接根因

**书源 header JS 代码缺陷**：某个（或多个）RssSource 的 `header` 字段以 `@js:` 或 `<js>` 开头，其 JS 代码内部调用了 `JSON.parse(xxx)`，而 `xxx` 在运行时为**空字符串**（`""`），Rhino 1.8.1 的 `NativeJSON.parse` 严格按 ECMAScript 规范抛出 `SyntaxError: Empty JSON string`。

> Rhino 行为符合标准（Chrome V8 同样会抛 `Unexpected end of JSON input`），**不是引擎 Bug**。问题在于书源 JS 代码没有对空字符串做容错判断（如 `if (str) JSON.parse(str)`）。

### 3.2 触发场景

- **触发时机**：Activity `onResume`（从后台切回前台、页面切换）
- **触发路径**：Glide 异步加载 RssSource 封面 → `OkHttpStreamFetcher` → 构造 `AnalyzeUrl` → 获取请求头 → 执行 header JS → JS 内 `JSON.parse("")` 抛错
- **高频原因**：Glide 图片加载是高频异步操作，每次封面加载都会重新构造 `AnalyzeUrl` 并执行 header 规则，导致同一书源的同一错误被反复触发（日志中 18 条记录来自同一时间段）

### 3.3 静默吞掉确认

`BaseSource.kt:121-123` 的 catch 块**完全静默吞掉异常**：

| 缺失信息 | 后果 |
|---------|------|
| 未记录哪个书源（`sourceUrl`/`sourceName`/`getKey()`） | 无法定位是哪个 RssSource 的问题 |
| 未记录 header 规则格式（`@js:` / `<js>` / 纯JSON） | 无法判断是 JS 规则问题还是纯 JSON 解析问题 |
| 未记录 header 规则长度（脱敏） | 无法判断规则规模 |
| 未记录调用来源（Glide / 网络请求） | 无法判断影响范围 |
| 调用者无感知 | `getHeaderMap` 返回空 Map + 默认 UA，调用者不知道 header 规则已失效 |

### 3.4 用户感知影响

| 维度 | 影响 |
|------|------|
| **功能** | 书源请求头规则失效 → 使用默认 UA → 可能被网站拒绝 → 封面加载失败 |
| **稳定性** | 不崩溃（catch 兜底 + 默认 UA 兜底），属于**功能降级** |
| **可诊断性** | 极差——日志只有异常堆栈，无书源标识，用户和开发者都无法定位问题源 |
| **性能** | 每次封面加载都重复抛错+记录日志，产生大量无效日志（18条/时段） |
| **日志噪音** | AppLog 被同一错误反复刷屏，掩盖其他真实问题 |

### 3.5 与 project_memory 经验的对照

`project_memory.md` 已记录"evalJS 返回值可能是 InputStream 而非 ByteArray"教训，强调 **evalJS 调用点需要类型容错**。本问题类似地暴露了 evalJS 调用点的另一类容错缺失：**JS 内部异常（JSON.parse 失败）会原样抛出，调用点 catch 后静默吞掉**。两类问题本质相同——evalJS 是不可靠外部 JS 执行，调用点必须做充分的**类型容错 + 日志容错 + 降级容错**。

## 4. 修复方案

### 4.1 文件路径

主修复文件：`f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\data\entities\BaseSource.kt`

（可选增强）`f:\myself\github\WeAgentChat\temp\legado\app\src\main\java\io\legado\app\model\analyzeRule\AnalyzeRule.kt`

### 4.2 修改点

#### 修改点 1（必做）：增强 `getHeaderMap` catch 块日志

**目的**：记录书源标识 + 规则格式 + 规则长度，让日志可定位问题源。遵守 AGENTS.md "改造必加日志"规范第3条（网络请求关键节点）、第7条（错误处理路径——所有 catch 块必须有日志且不能静默吞掉）。

**位置**：`BaseSource.kt:121-123`

**old_string 草案**：
```kotlin
            } catch (e: Exception) {
                AppLog.put("执行请求头规则出错\n$e", e)
            }
```

**new_string 草案**：
```kotlin
            } catch (e: Exception) {
                // 改造必加日志：记录书源标识 + 规则格式 + 规则长度，便于定位问题源
                // 不记录 header 规则内容（可能含敏感 token），只记录长度做脱敏
                val headerType = when {
                    it.startsWith("@js:", true) -> "@js"
                    it.startsWith("<js>", true) -> "<js>"
                    else -> "json"
                }
                AppLog.put(
                    "执行请求头规则出错 source=${getKey()} type=$headerType len=${it.length}\n$e", e
                )
            }
```

**理由**：
- `getKey()` 返回 `sourceUrl`（RssSource）或 `bookSourceUrl`（BookSource），是书源唯一标识
- `type` 区分 JS 规则 vs 纯 JSON，帮助判断是 JS 代码缺陷还是 JSON 格式问题
- `len` 记录规则长度，脱敏后仍能判断规则规模（是否异常短/长）
- 不记录 `it` 内容，避免泄露 header 中的 token/cookie（遵守 AGENTS.md "日志内容安全"规范）

#### 修改点 2（可选增强）：`evalJS` 入口添加临时调试日志

**目的**：当修改点 1 仍无法定位具体 JS 行时，临时开启 evalJS 入口日志辅助排查。遵守 AGENTS.md "永久+临时双轨"——此处为**临时日志**，验证后移除。

**位置**：`BaseSource.kt:325`（`evalJS` 方法入口）

**old_string 草案**：
```kotlin
    @Throws(Exception::class)
    fun evalJS(jsStr: String, bindingsConfig: ScriptBindings.() -> Unit = {}): Any? {
        val bindings = buildScriptBindings { bindings ->
```

**new_string 草案**：
```kotlin
    @Throws(Exception::class)
    fun evalJS(jsStr: String, bindingsConfig: ScriptBindings.() -> Unit = {}): Any? {
        // 临时日志：evalJS 入口（仅记录长度，不记录内容），排查 JSON.parse 问题后移除
        Log.d("evalJS", "source=${getKey()} jsLen=${jsStr.length}")
        val bindings = buildScriptBindings { bindings ->
```

**移除条件**：当 appLog 中不再出现"执行请求头规则出错"且确认所有问题书源已修复后，用 Grep 搜索 `Log.d("evalJS"` 移除所有临时日志。

#### 修改点 3（可选增强）：`AnalyzeRule.evalJS` 失败日志

**目的**：`AnalyzeRule.evalJS`（行 843）用于规则解析场景，目前完全没有 try-catch，异常直接抛给调用者。建议在主要调用点（如 `getString` / `getStringList` 等循环内）增加 catch + 日志，避免单个规则 JS 失败导致整个解析中断。

> 本修改点不在本问题必修范围（本问题是 header JS 场景），仅作为同类问题的预防性建议记录。实施前需 OpenSpec 流程评审。

### 4.3 风险评估

| 修改点 | 风险等级 | 影响范围 | 说明 |
|--------|---------|---------|------|
| **修改点 1** | 🟢 低 | 所有 `getHeaderMap` 调用者 | 仅增强 catch 块日志，不改变控制流，返回值不变（仍返回空 Map + 默认 UA）。所有调用者（`AnalyzeUrl`、`OkHttpStreamFetcher`、网络请求等）行为完全不变 |
| **修改点 2** | 🟡 中 | 所有 `BaseSource.evalJS` 调用者 | 临时 `Log.d` 在高频路径（封面加载）会产生日志噪音，**必须验证后移除**。`Log.d` 不抛异常，不影响控制流 |
| **修改点 3** | 🔴 高 | 所有 `AnalyzeRule.evalJS` 调用者 | 改变异常处理语义，可能掩盖真实 bug。**需 OpenSpec 流程评审**，不在本次修复范围 |

### 4.4 验证清单

- [ ] 修改点 1 实施后，重新编译安装，触发封面加载
- [ ] 抓取 appLog，确认日志中包含 `source=xxx type=xxx len=xxx` 字段
- [ ] 根据 `source` 字段定位问题书源，检查其 header 规则
- [ ] 若确认是书源 JS 缺陷（`JSON.parse` 未做空字符串判断），通知用户修复书源或通过书源校验器拦截
- [ ] 若修改点 2 启用，验证完成后用 Grep 搜索 `Log.d("evalJS"` 确认全部移除
- [ ] 更新 `app/src/main/assets/updateLog.md`（遵守版本交付同步规范）

### 4.5 长期建议（不在本次修复范围）

1. **书源校验器增强**：在书源导入/编辑时，静态扫描 header JS 代码中的 `JSON.parse` 调用，提示用户添加空字符串容错
2. **evalJS 沙箱化**：考虑在 `BaseSource.evalJS` 外层包一层 try-catch + 降级返回空字符串，避免书源 JS 缺陷影响主流程（需 OpenSpec 评审，可能改变现有书源兼容性）
3. **Rhino 引擎对比**：参考 AGENTS.md 延伸版本对比方法论，对比蛋蛋Max/阅读NG 的 evalJS 实现是否有更好的容错机制

---

## 总结

**根因**：书源 header JS 代码内部调用 `JSON.parse("")`（空字符串），Rhino 1.8.1 按规范抛出 `SyntaxError: Empty JSON string`，是**书源 JS 缺陷**而非引擎 Bug。`BaseSource.getHeaderMap` 的 catch 块静默吞掉异常，只记录堆栈不记录书源标识，导致无法定位问题源。

**修复点**：`BaseSource.kt:121-123` catch 块增强日志，记录 `source=getKey() type=headerType len=it.length`，让日志可定位到具体书源。
