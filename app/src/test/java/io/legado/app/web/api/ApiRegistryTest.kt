package io.legado.app.web.api

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.api.ReturnData
import io.legado.app.web.TokenManager.Level
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File

/**
 * ApiRegistry / ApiRouteBootstrap 单测（一期 · 5.9 / SC-1-14 / SC-1-15）。
 *
 * 两类断言：
 * 1. **行为**：注册 / 查表 / 未注册返回 null / 重复注册抛异常 / install 幂等且为 28 条；
 * 2. **结构（源码扫描）**：`HttpServer.kt` 内**无端点级 `when (uri)` 分支**（SC-1-15 的单测版，
 *    门禁 `audit_api_registry.py` 的补充）。
 */
class ApiRegistryTest {

    @Before
    fun setUp() {
        ApiRouteBootstrap.resetForTest()
    }

    // ------------------------------------------------------------ 安装 / 计数

    @Test
    fun install_registersExactly28Routes() {
        ApiRouteBootstrap.install()
        assertEquals("一期旧端点须为 28 条（与改造前一一对应）", 28, ApiRegistry.size)
        assertTrue(ApiRouteBootstrap.isInstalled)
    }

    @Test
    fun install_isIdempotent() {
        ApiRouteBootstrap.install()
        ApiRouteBootstrap.install()
        ApiRouteBootstrap.install()
        assertEquals("重复调用不得重复注册（5.10 幂等要求）", 28, ApiRegistry.size)
    }

    @Test
    fun all_hasUniqueKeys_andEveryRouteComplete() {
        ApiRouteBootstrap.install()
        val all = ApiRegistry.all()
        assertEquals("路由键必须唯一", all.size, all.map { it.key }.toSet().size)
        all.forEach { route ->
            assertTrue("路径须以 / 开头：${route.path}", route.path.startsWith("/"))
            assertTrue("级别不得为 NONE：${route.key}", route.level != Level.NONE)
        }
    }

    // ------------------------------------------------------------ 查表

    @Test
    fun find_knownRoute_returnsIt() {
        ApiRouteBootstrap.install()
        val route = ApiRegistry.find(Method.POST, "/saveBookSource")
        assertNotNull(route)
        assertEquals("/saveBookSource", route!!.path)
        assertEquals(Level.MANAGE, route.level)
    }

    @Test
    fun find_unknownRouteOrWrongMethod_returnsNull() {
        ApiRouteBootstrap.install()
        assertNull("未注册路径须返回 null（REQ-1-506）", ApiRegistry.find(Method.GET, "/no-such-endpoint"))
        assertNull("方法不匹配也须返回 null", ApiRegistry.find(Method.GET, "/saveBookSource"))
    }

    @Test
    fun register_duplicateKey_throws() {
        val dummy = ApiRoute(Method.GET, "/dup-probe", Level.READONLY) { ReturnData() }
        ApiRegistry.register(dummy)
        val ex = runCatching { ApiRegistry.register(dummy) }.exceptionOrNull()
        assertTrue(
            "同一「方法 + 路径」重复注册必须抛异常（编程错误须启动期暴露）",
            ex is IllegalArgumentException
        )
    }

    // ------------------------------------------------------------ 级别（关键用例）

    @Test
    fun addLocalBook_isManage_notRelaxedByUploadBookPrefix() {
        // REQ-1-106 / SC-1-03：页面在 /uploadBook/ 下但属写端点 ⇒ 必须是 manage
        ApiRouteBootstrap.install()
        val route = ApiRegistry.find(Method.POST, "/addLocalBook")
        assertNotNull(route)
        assertEquals(Level.MANAGE, route!!.level)
    }

    @Test
    fun backup_endpoints_areAdmin() {
        ApiRouteBootstrap.install()
        assertEquals(Level.ADMIN, ApiRegistry.find(Method.GET, "/backup")?.level)
        assertEquals(Level.ADMIN, ApiRegistry.find(Method.GET, "/backupPreview")?.level)
    }

    @Test
    fun readEndpoints_areReadonly_writeEndpoints_areManageOrAbove() {
        ApiRouteBootstrap.install()
        assertEquals(Level.READONLY, ApiRegistry.find(Method.GET, "/getBookshelf")?.level)
        assertEquals(Level.READONLY, ApiRegistry.find(Method.GET, "/getBookSources")?.level)
        assertEquals(Level.MANAGE, ApiRegistry.find(Method.POST, "/saveBook")?.level)
        assertEquals(Level.MANAGE, ApiRegistry.find(Method.POST, "/deleteRssSources")?.level)
    }

    // ------------------------------------------------------------ 结构（源码扫描）

    @Test
    fun httpServer_hasNoEndpointLevelWhenBranch() {
        // 注意：必须**先剔除注释**再断言 —— 本文件 KDoc 里就写着「不再有端点级 when (uri) 分支」，
        // 直接扫全文会把这句话当成违规命中（首次实现即踩此坑）。
        val code = mainSource("web/HttpServer.kt").lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")

        assertTrue(
            "HttpServer.kt 不得再出现端点级 when (uri) 分支（SC-1-15）",
            !Regex("""when\s*\(\s*\w*uri\w*\s*\)""").containsMatchIn(code)
        )
        // 端点路径字面量必须已全部搬走
        listOf("/saveBookSource", "/getBookshelf", "/getBookContent", "/backupPreview").forEach { path ->
            assertTrue(
                "端点 $path 不应再出现在 HttpServer.kt 的可执行代码中",
                !code.contains("\"$path\"")
            )
        }
    }

    private fun mainSource(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }
}
