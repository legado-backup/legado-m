package io.legado.app.web

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 写面审计落库的接线不变量（一期 3.7 / REQ-1-307）。
 *
 * 为何用源码不变量：落库路径依赖 `appDb`（Room）与 HTTP 会话，纯 JVM 驱动不了；而本批的四条约定
 * **编译期完全无感**，漏改即静默失灵（审计表永远是空的，或反过来把只读请求也灌进去把表撑爆）。
 */
class McpAuditorWiringTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val auditor by lazy { read("src/main/java/io/legado/app/web/McpAuditor.kt") }
    private val envelope by lazy { read("src/main/java/io/legado/app/web/api/ApiEnvelope.kt") }
    private val context by lazy { read("src/main/java/io/legado/app/web/api/ApiContext.kt") }
    private val httpServer by lazy { read("src/main/java/io/legado/app/web/HttpServer.kt") }
    private val webService by lazy { read("src/main/java/io/legado/app/service/WebService.kt") }

    @Test
    fun auditScopeIsWriteSurfaceOnly() {
        assertTrue(
            "审计只覆盖写面（level != READONLY）——否则审计表退化为访问日志",
            auditor.contains("if (route.level == TokenManager.Level.READONLY) return")
        )
    }

    @Test
    fun targetIsSanitizedBeforePersisting() {
        assertTrue(
            "target 必须经脱敏（REQ-1-308），禁止直写请求体",
            auditor.contains("target = AuditSanitizer.extractTarget(postData)")
        )
        assertFalse(
            "不得把原始 postData 直接落库",
            auditor.contains("target = postData")
        )
    }

    @Test
    fun insertIsAsynchronousAndNeverBlocksResponse() {
        assertTrue("落库须异步投递", auditor.contains("Coroutine.async {"))
        assertFalse("审计不得用 runBlocking（会阻塞 HTTP 线程）", auditor.contains("runBlocking"))
    }

    @Test
    fun dispatchRecordsWithRequestLevel() {
        val body = envelope.substringAfter("suspend fun dispatch(")
            .substringBefore("fun errorResponseOf(")
        assertTrue("dispatch 须审计", body.contains("McpAuditor.record("))
        assertTrue("审计须带上本次请求的令牌级别", body.contains("level = ctx.level"))
        assertTrue("审计须带耗时", body.contains("elapsedMs = System.currentTimeMillis() - startedAt"))
        assertFalse(
            "3.7 已落地：不得再留空的 finally 审计挂点",
            body.contains("// 3.7 异步审计挂点")
        )
    }

    @Test
    fun requestContextCarriesTokenLevel() {
        assertTrue(
            "ApiContext 须承载令牌级别（供审计回答\"谁在调用\"）",
            context.contains("val level: TokenManager.Level = TokenManager.Level.NONE")
        )
        assertTrue(
            "HttpServer 构造 ApiContext 时须传入实际级别",
            httpServer.contains("ApiContext(session.method, uri, session.parameters, postData, files, got)")
        )
    }

    @Test
    fun denialsAreAudited() {
        assertTrue(
            "未授权尝试写面须留痕（安全取证的关键一类）",
            httpServer.contains("""errorMsg = if (got == TokenManager.Level.NONE) "unauthorized" else "forbidden"""")
        )
        assertTrue("限流拒绝亦须留痕", httpServer.contains("""errorMsg = "rate limited""""))
    }

    @Test
    fun retentionPurgeIsWiredIntoServiceStart() {
        assertTrue(
            "保留策略（>7 天清理）须在 Web 服务启动时投递一次",
            webService.contains("McpAuditor.purgeExpired()")
        )
        assertTrue("保留期须为 7 天", auditor.contains("const val RETENTION_MS = 7L * 24 * 60 * 60 * 1000"))
    }
}
