package io.legado.app.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 控制台**按需分发**静态源回归（web-mcp-productization 四期 · tasks 1.2 / REQ-4-104~106）。
 *
 * 锁三件事：
 * 1. **前缀常量值稳定**（`serve()` 的静态兜底分支与前端资源路径都依赖它）；
 * 2. **`serve()` 里存在该前缀分支**（防"控制台路由被静默摘掉"导致 `/console/` 走到 assets 404）；
 * 3. **门禁 G-21 口径不破**：该分支是「静态资源策略前缀判断」，`serve()` 内**不得**出现端点路径字面量。
 *
 * 为什么用源码扫描而不是调用 [FileWeb.getResponse]：它会读 `appCtx.filesDir` / assets，
 * 纯 JVM 单测构造不出 Android 环境（与 `KernelSweepTest` / `Phase3RouteEnvelopeTest` 同口径）。
 */
class FileWebTest {

    @Test
    fun consolePrefix_isStable() {
        assertEquals("/console", FileWeb.CONSOLE_PREFIX)
    }

    @Test
    fun httpServer_routesConsolePrefixToFileWeb() {
        val src = mainSource("web/HttpServer.kt").lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
        assertTrue(
            "serve() 静态兜底必须把控制台前缀交给 FileWeb（防控制台路由被摘掉）",
            src.contains("FileWeb.CONSOLE_PREFIX") && src.contains("FileWeb.getResponse("),
        )
        assertTrue("FileWeb 必须仍走 boot 兜底（assets 引导壳）", src.contains("assetsWeb.getResponse("))
    }

    @Test
    fun fileWeb_hasBootFallbackAndTraversalGuard() {
        val src = mainSource("web/FileWeb.kt").lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
        assertTrue("必须有 boot 壳兜底常量", src.contains("BOOT_ASSET"))
        assertTrue("必须复用 assets 路径安全校验", src.contains("isSafePath"))
        assertTrue("必须做 canonicalPath 前缀校验（防 symlink/规范化绕过）", src.contains("canonicalPath"))
    }

    private fun mainSource(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }
}