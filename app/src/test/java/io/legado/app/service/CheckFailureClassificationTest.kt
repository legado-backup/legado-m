package io.legado.app.service

import com.script.ScriptException
import io.legado.app.exception.ContentEmptyException
import io.legado.app.exception.NoStackTraceException
import io.legado.app.exception.RegexTimeoutException
import io.legado.app.exception.TocEmptyException
import kotlinx.coroutines.TimeoutCancellationException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

/**
 * 巡检失败归因口径（`checkFailureGroupName`）的行为护栏。
 *
 * 关键语义：**业务异常（NoStackTraceException 家族）不得被标成「网站失效」** —— 这类异常携带的是引擎侧
 * 明确结论（目录为空 `TocEmptyException` / 正文为空 `ContentEmptyException` / 规则为空等），上游已按维度
 * 打点；若在此再打「网站失效」，会把可用源误标死站，用户据此误删源（NEW-21 同族误判，本轮一并收口）。
 */
class CheckFailureClassificationTest {

    @Test
    fun timeout_mapsToTimeoutGroup() {
        // TimeoutCancellationException 构造函数为 internal ⇒ 用真实超时现场产出实例
        val timeout = kotlinx.coroutines.runBlocking {
            try {
                kotlinx.coroutines.withTimeout(1) { kotlinx.coroutines.delay(80) }
                null
            } catch (t: TimeoutCancellationException) {
                t
            }
        }
        assertTrue(timeout != null)
        assertEquals("校验超时", checkFailureGroupName(timeout!!))
    }

    @Test
    fun scriptException_mapsToJsGroup() {
        assertEquals("js失效", checkFailureGroupName(ScriptException("s")))
        assertEquals("js失效", checkFailureGroupName(org.mozilla.javascript.WrappedException(
            RuntimeException("inner")
        )))
        // Rhino 运行时常见形态：WrappedException 包着脚本体自己的异常
        assertEquals("js失效", checkFailureGroupName(org.mozilla.javascript.WrappedException(
            ScriptException("inner")
        )))
    }

    @Test
    fun businessException_addsNoGroup() {
        // 目录为空 / 正文为空 / 正则超时 / 通用业务结论：均不加分组（维度失败已在 doCheckSource 回写）
        assertNull(checkFailureGroupName(TocEmptyException("目录为空")))
        assertNull(checkFailureGroupName(ContentEmptyException("正文为空")))
        assertNull(checkFailureGroupName(RegexTimeoutException("regex timeout")))
        assertNull(checkFailureGroupName(NoStackTraceException("搜索链接规则为空")))
    }

    @Test
    fun networkError_mapsToSiteDeadGroup() {
        assertEquals("网站失效", checkFailureGroupName(IOException("connection reset")))
        assertEquals("网站失效", checkFailureGroupName(IllegalStateException("bad state")))
        // 目录取样空曾抛出的 NoSuchElementException 属"非业务异常" ⇒ 仍判网站失效；
        // 该情形已由 sampleProbeChapters 的空守卫消除（NEW-21），本断言锁定"异常类型→归因"映射本身
        assertEquals("网站失效", checkFailureGroupName(NoSuchElementException("List is empty.")))
    }
}
