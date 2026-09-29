package io.legado.app.web.api.routes

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 三期路由 **handler 出参契约** 回归（web-mcp-productization 三期 · 实测缺陷固化）。
 *
 * **复现的缺陷（2026-09-29 真机冒烟发现）**：`DebugRoutes` / `LogRoutes` 的 handler 起初
 * **直接返回裸 `Map`**（`SourceDebugKernel.xxx(...)` 原样返回），而 `ApiEnvelope.dispatch` 只接受
 * `ReturnData` 或 `NanoHTTPD.Response` ⇒ 命中 `else -> error("handler 返回类型非法…")`
 * ⇒ **这两组的每个端点都 500**。同期其它组（`SourceRoutes` / `ContentRoutes` / `SettingsRoutes`…）
 * 都写了 `ReturnData().setData(...)`，故只有这两组中招。
 *
 * **为什么用源码扫描而不是调用 handler**：handler 会走到 `service/kernel` → Room DAO，
 * 纯 JVM 单测构造不出 Android 环境（实测 `ClassNotFoundException`）⇒ 与 `KernelSweepTest`
 * 同款口径：剥注释后做结构断言。
 */
class Phase3RouteEnvelopeTest {

    private val routesDir = listOf(
        File("src/main/java/io/legado/app/web/api/routes"),
        File("../app/src/main/java/io/legado/app/web/api/routes"),
        File("app/src/main/java/io/legado/app/web/api/routes"),
    ).firstOrNull { it.isDirectory }
        ?: throw AssertionError("未找到 web/api/routes 目录")

    private fun code(fileName: String): String {
        val file = File(routesDir, fileName)
        assertTrue("路由文件须存在：$fileName", file.isFile)
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** 本轮实测出缺陷的两个文件（B/C 组）。 */
    private val guarded = listOf("DebugRoutes.kt", "LogRoutes.kt")

    @Test
    fun debugAndLogRoutes_wrapEveryHandlerResultInReturnData() {
        guarded.forEach { fileName ->
            val src = code(fileName)
            val routes = Regex("""ApiRoute\(""").findAll(src).count()
            val envelopes = Regex("""ReturnData\(\)\.setData\(""").findAll(src).count()
            assertTrue("$fileName 不该是空文件", routes > 0)
            assertTrue(
                "$fileName 的每个 handler 都必须 ReturnData().setData(...)" +
                    "（裸 Map 会被 ApiEnvelope 判为非法 ⇒ 500）：声明 $routes 条，信封 $envelopes 处",
                envelopes >= routes,
            )
        }
    }

    @Test
    fun guardedRoutes_doNotReturnKernelCallDirectly() {
        // 反例守卫：handler 体不得以 `Kernel.xxx(...)` 直接作为最后表达式返回
        //（即 `{ ctx -> SomeKernel.call(...) }` 这种裸返回形态）
        guarded.forEach { fileName ->
            val src = code(fileName)
            val bareReturn = Regex("""\{\s*(?:ctx|_)\s*->\s*\n\s*(?:SourceDebugKernel|DiagReadKernel|BookSourceKernel)\.""")
            assertTrue(
                "$fileName 存在 handler 直接返回 Kernel 裸结果的写法（应包 ReturnData）",
                !bareReturn.containsMatchIn(src),
            )
        }
    }
}