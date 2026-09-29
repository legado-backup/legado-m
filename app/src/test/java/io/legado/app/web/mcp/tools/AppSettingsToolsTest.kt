package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_APP
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ㉓ 应用设置域声明单测（二期 · tasks 2.24b / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint）、schema 必填、AD-10 结构红线，
 * 以及**已注册进目录**（McpToolCatalog）。凭据类键的拒绝口径由 kernel（[io.legado.app.service.kernel.AppSettingsKernel]）
 * 的白名单保证，本文件只验声明层。
 */
class AppSettingsToolsTest {

    private val tools: List<McpTool> = AppSettingsTools.tools

    @Test
    fun appPrefsGet_isReadonlyWithOptionalKeys() {
        val tool = tools.single { it.name == "app_prefs_get" }
        assertEquals(MCP_DOMAIN_APP, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("只读工具须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("读取偏好不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("keys"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    /**
     * IF-22（第 5 轮 UX/IA 重构）：`app_prefs_get` 的**说明须与内核出参一致**。
     *
     * 起因：描述写「keys 省略 = 白名单全集」，而内核原实现空列表返回空结果（实现与描述不符，
     * 控制台据此读取会误判"没有可写偏好"）；补 `available` 元数据后描述也必须同步 ⇒
     * 用断言把「描述 ↔ 内核契约」钉在一起，防再漂移。
     */
    @Test
    fun appPrefsGet_descriptionMatchesKernelContract() {
        val description = tools.single { it.name == "app_prefs_get" }.description
        assertTrue("描述须说明「keys 省略 = 白名单全集」", description.contains("省略"))
        assertTrue("描述须说明回传 available 元数据", description.contains("available"))
    }

    @Test
    fun writeTools_areManageWithoutReadOnlyHint() {
        listOf("app_prefs_save", "app_theme_mode_set").forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("写工具须为 MANAGE 级：$name", TokenManager.Level.MANAGE, tool.level)
            assertFalse("写工具 readOnlyHint 须为 false：$name", tool.readOnlyHint)
        }
        assertEquals(
            listOf("prefs"),
            tools.single { it.name == "app_prefs_save" }.inputSchema.getAsJsonArray("required").map { it.asString },
        )
        assertEquals(
            listOf("mode"),
            tools.single { it.name == "app_theme_mode_set" }.inputSchema.getAsJsonArray("required").map { it.asString },
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        // 三期 L11：本域含 `legado_ping`（**矩阵指定名**，不属 `app_` 前缀）⇒ 允许两套前缀
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_APP, "app_", "legado_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
        assertEquals("应用设置域须 5 个工具（4 + 连通性自检 legado_ping）", 5, tools.size)
    }

    /** 三期 2.15.3 / FEATURE-MATRIX L11：连通性自检探针的契约（只读、无入参、非危险）。 */
    @Test
    fun legadoPing_isReadonlyNoArgProbe() {
        val tool = tools.single { it.name == "legado_ping" }
        assertEquals(MCP_DOMAIN_APP, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("探针须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("探针不是危险操作（不触发端侧确认闸门）", tool.dangerous)
        assertEquals("探针不接收入参", 0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(
            "探针入参属性应为空（无参数）",
            emptySet<String>(),
            tool.inputSchema.getAsJsonObject("properties").keySet(),
        )
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/AppSettingsTools.kt")
    }
}