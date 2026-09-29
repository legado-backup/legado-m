package io.legado.app.web.api

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.api.ReturnData
import io.legado.app.web.TokenManager.Level
import kotlinx.coroutines.runBlocking
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
    fun install_registersAllDeclaredRoutes() {
        ApiRouteBootstrap.install()
        // 口径：一期 28 条 + 二期 `/mcp` 3 条（POST/GET/DELETE）+ **三期 13 组 144 条**（B 10 / C 3 / D 6 /
        // E 9 / N 漫画 5 / N 视频 7 / O 发现 7 / M 角色 4 / L 存储 6 / AI+外观+缓存 38 / G 书架 11 /
        // G 设置 36 / F 控制台 2）+ **四期 3 条**（`/consoleInstall` 接线 + `/consoleRollback` 回退 +
        // 三期缺口补齐 `/ping` 连通性自检）+ **三期补记 9 条**（书签删除 `/deleteBookmark`、名场面
        // `/getSceneBookmarks`·`/saveSceneBookmark`·`/deleteSceneBookmark`、HTTP TTS
        // `/getHttpTtsList`·`/saveHttpTts`·`/deleteHttpTts`、阅读目标 `/getReadGoal`·`/saveReadGoal`
        // —— 均为内核/MCP 工具已有、当时只差 HTTP 路由 ⇒ 前端只能降级）= 187。
        // 新增端点时须同步此常量（tasks 三期 §1 收尾项）。
        assertEquals("路由总数 = 一期 28 + 二期 3 + 三期 144 + 四期 3 + 三期补记 9", 187, ApiRegistry.size)
        assertTrue(ApiRouteBootstrap.isInstalled)
    }

    @Test
    fun mcpTransport_registersThreeMethodsAtReadonly() {
        // REQ-2-107 / SC-2-16：「/mcp 是一条注册路由」的证据 —— 三方法同名路径、级别 READONLY，
        // 真正双闸在协议核内（路由级只做最低门槛，否则只读令牌连 tools/list 都进不去）。
        ApiRouteBootstrap.install()
        listOf(Method.POST, Method.GET, Method.DELETE).forEach { method ->
            val route = ApiRegistry.find(method, "/mcp")
            assertNotNull("/mcp 须注册 $method 分支（REQ-2-102）", route)
            assertEquals("路由级门槛须为 READONLY（双闸在协议核）", Level.READONLY, route!!.level)
        }
    }

    @Test
    fun install_isIdempotent() {
        ApiRouteBootstrap.install()
        ApiRouteBootstrap.install()
        ApiRouteBootstrap.install()
        assertEquals("重复调用不得重复注册（5.10 幂等要求）", 187, ApiRegistry.size)
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

    // ------------------------------------------------------------ 扩展性（SC-1-14）

    @Test
    fun newRoute_isReachableWithoutTouchingHttpServer() = runBlocking {
        // SC-1-14 证据：新增端点只需在 web/api/routes/ 声明一行（此处以运行时注册等价模拟），
        // `serve()` / `HttpServer.kt` 零改动 —— 结构侧由 httpServer_hasNoEndpointLevelWhenBranch 断言。
        ApiRouteBootstrap.install()
        val probePath = "/__probe_extensibility__"
        ApiRegistry.register(
            ApiRoute(Method.GET, probePath, Level.READONLY) { ReturnData().setData("ok") }
        )

        assertEquals("新增 1 条须叠加在原 187 条之上（互不干扰）", 188, ApiRegistry.size)
        val route = ApiRegistry.find(Method.GET, probePath)
        assertNotNull("声明即注册 ⇒ 查表立即可达", route)

        // 端到端：新端点经 ApiEnvelope 自动继承统一信封 / 真实状态码能力（无需触碰 serve()）
        val resp = ApiEnvelope.dispatch(route!!, ApiContext(Method.GET, probePath, emptyMap()))
        assertEquals("新端点自动继承 200 信封能力", 200, resp.status.requestStatus)
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

    // ------------------------------------------------------------ 二期 §2.1 / §2.6：MCP 元数据与悬空清理

    @Test
    fun mcpMetadataFields_areOptionalWithSafeDefaults() {
        // 二期 §2.1：ApiRoute 追加 mcpTitle/mcpDescription/mcpDangerous 三个可选字段，
        // 默认 null/null/false ⇒ 一期 28 条路由零改动（编译不受影响）。
        val plain = ApiRoute(Method.GET, "/__probe_mcp_meta__", Level.READONLY) { ReturnData() }
        assertNull("未声明时 mcpToolName 为 null", plain.mcpToolName)
        assertNull("未声明时 mcpTitle 为 null", plain.mcpTitle)
        assertNull("未声明时 mcpDescription 为 null", plain.mcpDescription)
        assertEquals("未声明时 mcpDangerous 为 false", false, plain.mcpDangerous)

        val declared = ApiRoute(
            Method.GET, "/__probe_mcp_meta_declared__", Level.READONLY,
            mcpToolName = "bookshelf_list",
            mcpTitle = "书架列表",
            mcpDescription = "读取书架全部书籍",
            mcpDangerous = false,
        ) { ReturnData() }
        assertEquals("bookshelf_list", declared.mcpToolName)
        assertEquals("书架列表", declared.mcpTitle)
        assertNotNull(declared.mcpDescription)
    }

    @Test
    fun sourceRoutes_doNotDeclareDanglingMcpToolNames() {
        // 二期 §2.6：列表/批量变体（source_get_all / source_save_multi / rss_source_get_all /
        // rss_source_save_multi）在 spec §4.2 无 1:1 工具 ⇒ 置为不投影（默认 null），
        // 避免"路由指向不存在的工具"这种隐性错误。此处以源码扫描锁死防回归。
        val code = mainSource("web/api/routes/SourceRoutes.kt").lines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
        listOf("source_get_all", "source_save_multi", "rss_source_get_all", "rss_source_save_multi")
            .forEach { name ->
                assertTrue(
                    "悬空 mcpToolName 须已清理（$name 在 spec §4.2 无 1:1 工具）",
                    !code.contains("mcpToolName = \"$name\""),
                )
            }
        // 正向断言：1:1 可对拍的投影须保留（防"一刀切全删"）
        assertTrue(
            "1:1 可对拍的路由仍须保留 mcpToolName（source_get）",
            code.contains("mcpToolName = \"source_get\""),
        )
    }

    private fun mainSource(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }
}
