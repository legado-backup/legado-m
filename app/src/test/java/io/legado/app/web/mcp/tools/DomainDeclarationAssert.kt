package io.legado.app.web.mcp.tools

import io.legado.app.web.mcp.McpTool
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import java.io.File

/**
 * 域声明测试公共断言（二期 · tasks 2.27）。
 *
 * 抽出的两点是**每个域都要验的同一件事**（避免 20 份域测试各写一遍、口径漂移）：
 * 1. 域内元数据一致性（`domain` 统一 / 名唯一 / 名带域前缀）；
 * 2. **AD-10 结构红线**：域文件不得直接访问 DAO、不得 import `api.controller`，执行体须走 Kernel。
 */
internal object DomainDeclarationAssert {

    fun assertMetadataConsistent(tools: List<McpTool>, domain: String, prefix: String) {
        assertTrue("域 $domain 不应为空", tools.isNotEmpty())
        tools.forEach { tool ->
            assertEquals("域文件内的 domain 必须一致", domain, tool.domain)
            assertTrue("工具名须带域前缀（$prefix）：${tool.name}", tool.name.startsWith(prefix))
        }
        assertEquals("工具名在本域内须唯一", tools.size, tools.map { it.name }.toSet().size)
    }

    /**
     * 结构红线检查。
     *
     * 先**剔除注释行**再断言（域文件的 KDoc 里就写着"不得 import api.controller"，
     * 直接扫全文会自证违规 —— 一期 `httpServer_hasNoEndpointLevelWhenBranch` 踩过同样坑）。
     */
    fun assertKernelOnly(relFromMcp: String) {
        val code = source(relFromMcp).lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
        assertFalse("AD-10：域文件不得直接访问 DAO", code.contains("appDb."))
        assertFalse("AD-10：域文件不得直接访问 DAO", Regex("""\bDao\.""").containsMatchIn(code))
        assertFalse("REQ-2-305：web/mcp 内不得 import api.controller", code.contains("api.controller"))
        assertTrue("执行体须调 service/kernel：$relFromMcp", code.contains("service.kernel"))
    }

    fun source(relFromMcp: String): String {
        val rel = "src/main/java/io/legado/app/web/mcp/$relFromMcp"
        return listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }?.readText()
            ?: throw AssertionError("未找到源文件：$rel")
    }
}
