package io.legado.app.service

import io.legado.app.model.SuspectReason
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * 「存疑源跳过」口径（`suspectSkipLabel`）的行为护栏。
 *
 * 语义：与质检底座 [SuspectReason] 同源 —— 静态可判定其失败**不可归因于源本身**（需登录 / jsLib 依赖 /
 * 源变量依赖 / webView 型 / 内网地址）时，巡检判**跳过·存疑**而非「网站失效」等确定性失败，避免误杀
 * 可用源；非存疑源返回 null（按常规失败归因）。
 */
class CheckSourceSuspectSkipTest {

    @Test
    fun noReason_isNotSuspect() {
        assertNull(suspectSkipLabel(emptyList()))
    }

    @Test
    fun loginDependency_labelsLogin() {
        assertEquals("存疑（登录依赖）", suspectSkipLabel(listOf(SuspectReason.LOGIN)))
    }

    @Test
    fun multipleReasons_joinByEnumerationOrder() {
        assertEquals(
            "存疑（jsLib依赖、源变量依赖）",
            suspectSkipLabel(listOf(SuspectReason.JS_LIB, SuspectReason.SOURCE_VARIABLE))
        )
    }

    @Test
    fun allReasons_coverEveryCategory() {
        val label = suspectSkipLabel(SuspectReason.entries.toList())
        assertEquals(
            "存疑（登录依赖、jsLib依赖、源变量依赖、webView型、内网地址）",
            label
        )
    }
}
