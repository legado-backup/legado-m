package io.legado.app.help.source

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 隐式分页识别纯函数的回归测试（2026-10-01 缺陷③）。
 *
 * 背景：用户写 `page={{Math.floor(Math.random() * 100) + 1}}` 这类随机/自定义分页表达式**完全不生效**
 * ——原判定只认字面量 `{{page}}`，而解析层对 `{{...}}` 是通用 JS 求值（识别层与解析层能力不对等）。
 * 现放宽为「含任意 `{{...}}` 内联 JS 占位」，本测试把放宽边界与**不误判**两侧同时钉死。
 */
class RssImplicitPageDetectorTest {

    @Test
    fun literalPagePlaceholderIsStillDetected() {
        // 存量兼容：`{{page}}` 必须继续判为可翻页
        assertTrue(RssImplicitPageDetector.detect(null, "https://example.com/list/{{page}}.html"))
        assertTrue(RssImplicitPageDetector.detect("", "https://example.com/list?page={{page}}"))
    }

    @Test
    fun randomPageExpressionIsDetected() {
        // 🔴 缺陷③核心：随机/自定义分页表达式必须判为可翻页（否则既不翻页也不出现页码入口）
        assertTrue(
            RssImplicitPageDetector.detect(
                null,
                "https://example.com/list?page={{Math.floor(Math.random() * 100) + 1}}"
            )
        )
    }

    @Test
    fun customPageComputationIsDetected() {
        // 自定义换算（如页码 × 步长）同样应识别
        assertTrue(RssImplicitPageDetector.detect(null, "https://example.com/list/{{page * 20}}.html"))
    }

    @Test
    fun urlWithoutPlaceholderIsNotDetected() {
        // 无占位符 ⇒ 不得判为可翻页（否则会对同一 URL 无限重复请求）
        assertFalse(RssImplicitPageDetector.detect(null, "https://example.com/list.html"))
        assertFalse(RssImplicitPageDetector.detect(null, "https://example.com/list?page=1"))
    }

    @Test
    fun incompleteBracesAreNotDetected() {
        // 只有单侧花括号（非法 JS）不算内联占位
        assertFalse(RssImplicitPageDetector.detect(null, "https://example.com/list/{{page.html"))
        assertFalse(RssImplicitPageDetector.detect(null, "https://example.com/list/page}}.html"))
    }

    @Test
    fun explicitNextPageRuleWins() {
        // 源已填 ruleNextPage ⇒ 以显式规则为准，不做隐式判定（即便 URL 含占位符）
        assertFalse(RssImplicitPageDetector.detect("//a/@href", "https://example.com/list/{{page}}.html"))
    }

    @Test
    fun blankInputsAreNotDetected() {
        assertFalse(RssImplicitPageDetector.detect(null, null))
        assertFalse(RssImplicitPageDetector.detect(null, ""))
        assertFalse(RssImplicitPageDetector.detect("", "   "))
    }
}