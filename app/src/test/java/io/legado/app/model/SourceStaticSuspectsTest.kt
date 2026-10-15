package io.legado.app.model

import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.BookSourcePart
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 质检底座「静态存疑」单一入口（`SourceQualityChecker.staticSuspectsOf`）与巡检任务态「跳过」三态的行为护栏。
 *
 * 背景（缺口3 + 存疑口径）：`CheckSourceTaskStore.markBlocked` 此前**全仓无调用点**（横幅"跳过 N"恒 0），
 * 且 `CheckSourceService` 不识别「存疑源」⇒ 需登录/依赖 jsLib/内网类源失败时被打成「网站失效」（误杀）。
 * 本用例锁定：①静态存疑判定与底座口径一致；②跳过项**带上原因**且计入横幅「跳过 N」。
 */
class SourceStaticSuspectsTest {

    private fun source(
        url: String = "http://example.com",
        loginUrl: String? = null,
        loginCheckJs: String? = null,
        jsLib: String? = null,
        searchUrl: String? = "http://example.com/search?q={{key}}",
    ) = BookSource(
        bookSourceName = "t",
        bookSourceUrl = url,
        bookSourceGroup = "",
        bookSourceType = 0,
        bookSourceComment = "",
        searchUrl = searchUrl,
        loginUrl = loginUrl,
        loginCheckJs = loginCheckJs,
        jsLib = jsLib,
    )

    @Test
    fun plainSource_isNotSuspect() {
        assertTrue(SourceQualityChecker.staticSuspectsOf(source()).isEmpty())
    }

    @Test
    fun loginDeclared_isSuspectLogin() {
        assertEquals(
            listOf(SuspectReason.LOGIN),
            SourceQualityChecker.staticSuspectsOf(source(loginUrl = "http://example.com/login"))
        )
        assertEquals(
            listOf(SuspectReason.LOGIN),
            SourceQualityChecker.staticSuspectsOf(source(loginCheckJs = "1==1"))
        )
    }

    @Test
    fun jsLibWithJsRule_isSuspectJsLib() {
        val s = source(jsLib = "function f(){}", searchUrl = "http://a/@js:f()")
        assertEquals(listOf(SuspectReason.JS_LIB), SourceQualityChecker.staticSuspectsOf(s))
    }

    @Test
    fun privateAddress_isSuspect() {
        val s = source(url = "http://192.168.1.10:8080")
        assertEquals(listOf(SuspectReason.PRIVATE_ADDRESS), SourceQualityChecker.staticSuspectsOf(s))
    }

    @Test
    fun blockedItem_keepsReasonAndCountsInBanner() {
        CheckSourceTaskStore.begin(listOf(BookSourcePart(bookSourceUrl = "http://example.com")))
        CheckSourceTaskStore.markRunning("http://example.com", "t", 0)
        CheckSourceTaskStore.markBlocked(
            origin = "http://example.com",
            durationMillis = 12L,
            message = "存疑（登录依赖）"
        )
        CheckSourceTaskStore.finish(cancelled = false)
        val state = CheckSourceTaskStore.state.value
        assertEquals(CheckSourceItemStatus.BLOCKED, state.items.single().status)
        assertEquals("存疑（登录依赖）", state.items.single().message)
        assertEquals(1, state.blockedCount)
        assertEquals(0, state.failedCount)
        assertTrue(state.bannerText()!!.contains("跳过 1"))
    }
}
