package io.legado.app.web.mcp

import io.legado.app.BuildConfig
import io.legado.app.web.TokenManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * MCP 工具目录单测（web-mcp-productization 二期 · tasks 2.4 / 2.5 / 2.26 / 2.29）。
 *
 * 锁四件事：① **元数据不变量**（名唯一 / 说明非空 / schema 含 required / 级别非 NONE）；
 * ② **级别裁剪**（可见数累积、单调）；③ **域元数据**（`byDomain` 与 `domains()` 一致）；
 * ④ **sourceSet 装配**（debug 构建下 L3 工具可见）。
 *
 * ⚠️ **规模断言（release 218 / debug 232）在 tasks 2.26 落地** —— 那时 20 个域文件齐备；
 * 本文件当前只锁"与规模无关的结构不变量"，以免每补一个域就改测试（避免测试成为噪音）。
 */
class McpToolCatalogTest {

    @Test
    fun all_hasUniqueNames() {
        val all = McpToolCatalog.all()
        assertEquals("工具名必须唯一（重名会让 find 命中错执行体）", all.size, all.map { it.name }.toSet().size)
    }

    @Test
    fun everyTool_hasCompleteMetadata() {
        McpToolCatalog.all().forEach { tool ->
            assertTrue("name 须非空", tool.name.isNotBlank())
            assertTrue("title 须非空：${tool.name}", tool.title.isNotBlank())
            assertTrue("REQ-2-207：description 须非空：${tool.name}", tool.description.isNotBlank())
            assertTrue("REQ-2-203：domain 须非空：${tool.name}", tool.domain.isNotBlank())
            assertTrue("级别不得为 NONE：${tool.name}", tool.level != TokenManager.Level.NONE)
            assertTrue("REQ-2-204：schema 须含 required：${tool.name}", tool.inputSchema.has("required"))
            assertEquals(
                "readOnlyHint 默认须与级别一致（保守口径）：${tool.name}",
                tool.level == TokenManager.Level.READONLY,
                tool.readOnlyHint
            )
        }
    }

    @Test
    fun find_everyDeclaredToolIsReachable() {
        McpToolCatalog.all().forEach { tool ->
            assertNotNull("find 必须命中：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun visibleFor_isCumulativeAndMonotonic() {
        val none = McpToolCatalog.visibleFor(TokenManager.Level.NONE)
        val readonly = McpToolCatalog.visibleFor(TokenManager.Level.READONLY)
        val manage = McpToolCatalog.visibleFor(TokenManager.Level.MANAGE)
        val admin = McpToolCatalog.visibleFor(TokenManager.Level.ADMIN)

        assertTrue("NONE 令牌看不到任何工具", none.isEmpty())
        assertTrue("可见面须随级别单调不减（REQ-2-202 口径=累积）", readonly.size <= manage.size)
        assertTrue(manage.size <= admin.size)
        assertEquals("ADMIN 可见全部工具", McpToolCatalog.all().size, admin.size)
        assertTrue("readonly 面不得含任何非 READONLY 工具", readonly.all { it.level == TokenManager.Level.READONLY })
    }

    @Test
    fun byDomain_isConsistentWithDomains() {
        val domains = McpToolCatalog.domains()
        assertTrue("域集合不应为空", domains.isNotEmpty())
        domains.forEach { domain ->
            val inDomain = McpToolCatalog.byDomain(domain)
            assertTrue("byDomain($domain) 不应为空", inDomain.isNotEmpty())
            assertTrue("byDomain($domain) 的元素 domain 须一致", inDomain.all { it.domain == domain })
        }
        assertEquals(
            "各域数量之和须等于工具总数",
            McpToolCatalog.all().size,
            domains.sumOf { McpToolCatalog.byDomain(it).size }
        )
    }

    @Test
    fun declaredDomains_coverBatchesLandedSoFar() {
        // 分期落地口径：本批次（§1 + 首批域）已声明 6 个域；每批域任务完成后此断言随之扩展，
        // 缺口最终由 tasks 2.26 的总数断言兜死（不会静默漏项）。
        val domains = McpToolCatalog.domains().toSet()
        listOf(
            MCP_DOMAIN_BOOKSHELF, MCP_DOMAIN_READING, MCP_DOMAIN_SOURCE,
            MCP_DOMAIN_RSS, MCP_DOMAIN_RULE, MCP_DOMAIN_BACKUP,
            MCP_DOMAIN_TTS, MCP_DOMAIN_STATS, MCP_DOMAIN_AUTOTASK, MCP_DOMAIN_DIAG,
            MCP_DOMAIN_STORAGE, MCP_DOMAIN_MULTIFORM, MCP_DOMAIN_EXPLORE, MCP_DOMAIN_CHARACTER,
            MCP_DOMAIN_AI, MCP_DOMAIN_APPEARANCE, MCP_DOMAIN_CACHE, MCP_DOMAIN_APP
        ).forEach { domain ->
            assertTrue("域 $domain 须已有工具声明", domains.contains(domain))
        }
    }

    @Test
    fun toolCount_matchesLandedScope() {
        // tasks 2.26（分期口径 · 与决策 #25 一致）：以**逐工具清单实测数**为准，禁止为凑目标数增删工具。
        // release 面 = 19 个域文件声明的 **217** 个（三期缺口补齐新增 `legado_ping` 连通性自检探针
        // —— 见 FEATURE-MATRIX L11 / 三期 tasks 2.15.3）；debug 面另含 14 个 L3 调试工具
        // （tasks 5.12：perf 1 + 源/订阅调试 9 + 诊断 4）⇒ 231。
        val expected = if (BuildConfig.BUILD_DEBUG) 231 else 217
        assertEquals("工具总数须与已落地域一致（release 217 / debug 231）", expected, McpToolCatalog.all().size)
    }

    @Test
    fun levelRank_matchesWebAuthOrdering() {
        assertEquals(0, McpToolCatalog.levelRank(TokenManager.Level.NONE))
        assertEquals(1, McpToolCatalog.levelRank(TokenManager.Level.READONLY))
        assertEquals(2, McpToolCatalog.levelRank(TokenManager.Level.MANAGE))
        assertEquals(3, McpToolCatalog.levelRank(TokenManager.Level.ADMIN))
    }

    @Test
    fun debugBuild_exposesL3Tools_releaseDoesNot() {
        val names = McpToolCatalog.all().map { it.name }
        if (BuildConfig.BUILD_DEBUG) {
            assertTrue(
                "debug 构建须装配 L3 调试工具（sourceSet 同包同名覆盖生效）",
                names.contains("perf_metrics_get")
            )
        } else {
            assertTrue(
                "release 构建不得出现任何 L3 调试工具（REQ-2-403）",
                !names.contains("perf_metrics_get")
            )
        }
    }
}
