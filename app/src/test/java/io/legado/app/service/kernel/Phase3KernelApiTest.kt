package io.legado.app.service.kernel

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 三期 §1 对 Kernel 的**新增/补方法**回归锚点（web-mcp-productization 三期 · tasks §1）。
 *
 * 三期端点全部**复用二期内核**，少数缺口由本期在已有 Kernel 文件里补方法。补方法是"一期看不到、
 * 二期也没写"的**唯一新增业务代码**，最容易被后续重构静默删掉（删了不会编译错，只会让某个端点
 * 运行时抛 `NoSuchMethod`/返回错值）⇒ 用源码扫描把方法名钉住。
 *
 * 扫描方式与 `KernelSweepTest` 同口径（读源码 + 剥行注释），避免依赖 Room/Context（纯 JVM 构造不出）。
 */
class Phase3KernelApiTest {

    private val kernelDir = listOf(
        File("src/main/java/io/legado/app/service/kernel"),
        File("../app/src/main/java/io/legado/app/service/kernel"),
        File("app/src/main/java/io/legado/app/service/kernel"),
    ).firstOrNull { it.isDirectory }
        ?: throw AssertionError("未找到 service/kernel 目录")

    private fun code(fileName: String): String {
        val file = File(kernelDir, fileName)
        assertTrue("内核文件须存在：$fileName", file.isFile)
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 三期补的 Kernel 方法（文件 → 方法名）。 */
    private val phase3KernelMethods = mapOf(
        "DiagReadKernel.kt" to listOf("recentAudit"),
        "TtsKernel.kt" to listOf("testTts"),
        "BookshelfKernel.kt" to listOf("searchBookshelf"),
        "AppSettingsKernel.kt" to listOf("appInfo"),
        "ContentKernel.kt" to listOf(
            "rssArticles", "rssArticleContent", "markRssRead", "readStats", "saveBookmark", "restoreBackup",
            // 三期补记（IF-12）：名场面保存的 JSON 体包装（bookUrl 必填校验）—— 与 7 条补记路由配套
            "saveSceneBookmark",
        ),
        "RssSourceKernel.kt" to listOf("markArticleRead"),
    )

    @Test
    fun phase3AddedKernelMethods_areStillPresent() {
        phase3KernelMethods.forEach { (fileName, methods) ->
            val src = code(fileName)
            methods.forEach { method ->
                assertTrue(
                    "$fileName 应保留三期补的方法 $method（三期端点依赖它；删除不会编译错但会运行期失效）",
                    Regex("""\bfun\s+$method\s*\(""").containsMatchIn(src),
                )
            }
        }
    }

    @Test
    fun cacheTaskKernel_syncRequiresCloudStorageConfigured() {
        val src = code("CacheTaskKernel.kt")
        // 云存储未配置时 `syncList` 应前置校验并抛业务 400（IllegalArgumentException），
        // 而不是放行到 `getBackupNames` 抛「WebDAV not configured」→ HTTP 500（真机实测缺陷，2026-09-29）
        assertTrue(
            "syncList 应先校验 AppCloudStorage.isOk（未配置 ⇒ 400 人话引导，而非 500）",
            Regex("""suspend\s+fun\s+syncList\([^)]*\)\s*:\s*Map<[^>]*>\s*=\s*withContext\(IO\)\s*\{(?s:.{0,500}?)require\(AppCloudStorage\.isOk\)""")
                .containsMatchIn(src),
        )
        assertTrue(
            "syncRun 也应先校验 AppCloudStorage.isOk（与 syncList 同前置条件）",
            Regex("""suspend\s+fun\s+syncRun\([^)]*\)\s*:\s*Map<[^>]*>\s*=\s*withContext\(IO\)\s*\{(?s:.{0,600}?)require\(AppCloudStorage\.isOk\)""")
                .containsMatchIn(src),
        )
    }

    @Test
    fun phase3AddedKernelMethods_areSuspend() {
        phase3KernelMethods.forEach { (fileName, methods) ->
            val src = code(fileName)
            methods.forEach { method ->
                assertTrue(
                    "$fileName 的 $method 须是 suspend（内核契约：全链挂起）",
                    Regex("""suspend\s+fun\s+$method\s*\(""").containsMatchIn(src),
                )
            }
        }
    }

    /**
     * 三期 L11 缺口补齐（S3 支撑件）：`AppSettingsKernel.ping()` 连通性探针。
     *
     * 锁三件事：① 必须是 suspend（内核契约）；② **只回非敏感键**（曾漏的 L11 属"后端无端点"缺口，
     * 补时最容易顺手把地址/令牌塞进去 ⇒ 此处按白名单反查）；③ 不得回传凭据类字样。
     */
    @Test
    fun appSettingsKernel_pingIsSuspendedAndNonSensitive() {
        val src = code("AppSettingsKernel.kt")
        assertTrue("ping 须是 suspend（内核契约）", Regex("""suspend\s+fun\s+ping\s*\(""").containsMatchIn(src))
        val body = Regex("""suspend\s+fun\s+ping\s*\(\s*\)[\s\S]{0,600}?\n\s{4}\}""").find(src)?.value
        assertTrue("应能定位 ping 函数体", body != null)
        listOf("ok", "serverTime", "versionName", "consoleApiLevel", "webServiceRunning", "mcpEndpoint")
            .forEach { key ->
                assertTrue("ping 出参须含非敏感键 $key", body!!.contains("\"$key\""))
            }
        listOf("token", "Token", "password", "secret", "hostAddress", "ip").forEach { banned ->
            assertTrue(
                "ping 出参**不得**含敏感/凭据类字段（命中 $banned）",
                !body!!.contains("\"$banned"),
            )
        }
    }

    /**
     * IF-22（第 5 轮 UX/IA 重构）：`prefsGet` 的**白名单语义与元数据出参**。
     *
     * 为什么必须钉住：
     * 1. 工具描述写的是「keys 省略 = 白名单全集」，而原实现空列表**返回空结果**（实现与描述不符）——
     *    控制台设置页按「不传 keys」读取会拿到空列表而误判"没有可写偏好"；此断言防回退。
     * 2. `available`（白名单键元数据）是控制台**按类型渲染控件**的唯一来源（前端不复制键表，
     *    删掉它不会编译错，但会让设置页在无元数据时退化）。
     * 3. 白名单是安全边界：**绝不含**凭据类键（AD-18 同类口径）。
     */
    @Test
    fun appSettingsKernel_prefsGetWhitelistSemanticsAndMetadata() {
        val src = code("AppSettingsKernel.kt")
        assertTrue(
            "prefsGet 空 keys 须回落到白名单全集（与 MCP 工具描述一致；否则控制台读到空列表）",
            Regex("""\.ifEmpty\s*\{\s*settingDefs\.map""").containsMatchIn(src),
        )
        assertTrue(
            "prefsGet 须回传 available 元数据（控制台据此按类型渲染控件，前端不复制键表）",
            src.contains("\"available\" to availableDefs()"),
        )
        assertTrue(
            "availableDefs 必须**只由白名单**生成（不得另有来源，否则可能漏出非白名单键）",
            Regex("""private fun availableDefs\(\)\s*:\s*List<Map<String,\s*Any\?>>\s*=\s*settingDefs\.map""")
                .containsMatchIn(src),
        )

        // 白名单块不得含凭据类字样（不含裸 `key`：白名单本就是 `PreferKey.*` 常量）
        val whitelistBlock = Regex("""private val settingDefs = listOf\([\s\S]*?\n    \)""").find(src)?.value
        assertTrue("应能定位 settingDefs 白名单块", whitelistBlock != null)
        listOf("token", "password", "passwd", "secret", "auth", "cookie", "credential", "apikey")
            .forEach { banned ->
                assertTrue(
                    "白名单**不得**含凭据类键（命中 $banned）",
                    !whitelistBlock!!.lowercase().contains(banned),
                )
            }
    }
}