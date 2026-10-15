package io.legado.app.help.http

import io.legado.app.testkit.fakeInterceptorChain
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

/**
 * core-flow-test-coverage tasks 3.2 / spec R-05 —— 拦截器链行为测试。
 *
 * 用伪造 `Interceptor.Chain`（[fakeInterceptorChain]，AD-01 缝 B）驱动拦截器，
 * 覆盖「异常分类」与「取消异常必须重抛」两条契约。
 *
 * **实测校准（2026-10-15）**：`isStreamResetException` 的判据是**异常类名**
 * （`cause.javaClass.name` 含 `StreamResetException`，或同时含 `http2` 与 `reset`），
 * **不是异常消息** ⇒ 用例改用类名替身构造（首版用 `IOException("http2Reset")` 属误判，已纠正）。
 * 另：`OkHttpExceptionInterceptor` 的 `AppLog` 调用在纯 JVM 下**可用**（3 个用例实测通过）。
 */
class InterceptorChainBehaviorTest {

    /** 类名含 `StreamResetException` 的替身（判据即类名匹配，兼容 R8 混淆）。 */
    private class StreamResetException(msg: String) : IOException(msg)

    /** 类名同时含 `http2` 与 `reset`（大小写不敏感）的替身。 */
    private class Http2ResetException(msg: String) : IOException(msg)

    /** 类名含 `http2` 但**不含** `reset` 的替身（防过度匹配）。 */
    private class Http2GoAwayException(msg: String) : IOException(msg)

    // ===== StreamResetRetryInterceptor.isStreamResetException（纯函数）=====

    @Test
    fun isStreamResetException_directMatch_isTrue() {
        assertTrue(StreamResetRetryInterceptor.isStreamResetException(StreamResetException("reset")))
    }

    @Test
    fun isStreamResetException_causeChain_isTrue() {
        assertTrue(
            StreamResetRetryInterceptor.isStreamResetException(
                IOException("outer", StreamResetException("inner"))
            )
        )
    }

    @Test
    fun isStreamResetException_http2AndResetInClassName_isTrue() {
        assertTrue(StreamResetRetryInterceptor.isStreamResetException(Http2ResetException("reset")))
    }

    @Test
    fun isStreamResetException_http2WithoutReset_isFalse() {
        assertFalse(StreamResetRetryInterceptor.isStreamResetException(Http2GoAwayException("goaway")))
    }

    @Test
    fun isStreamResetException_plainIoException_isFalse() {
        assertFalse(StreamResetRetryInterceptor.isStreamResetException(IOException("timeout")))
    }

    // ===== StreamResetRetryInterceptor.intercept：非 StreamReset 必须原样抛出 =====

    @Test
    fun streamReset_intercept_nonResetIoException_rethrownUnchanged() {
        val original = IOException("plain failure")
        val chain = fakeInterceptorChain { throw original }
        var thrown: Throwable? = null
        try {
            StreamResetRetryInterceptor.intercept(chain)
        } catch (t: Throwable) {
            thrown = t
        }
        assertSame("非 StreamReset 的 IOException 必须原样抛出（不得包装/吞掉）", original, thrown)
    }

    // ===== OkHttpExceptionInterceptor.intercept：取消异常必须重抛 =====

    @Test
    fun okHttpException_intercept_cancellationException_rethrownUnchanged() {
        val original = kotlinx.coroutines.CancellationException("cancelled")
        val chain = fakeInterceptorChain { throw original }
        var thrown: Throwable? = null
        try {
            OkHttpExceptionInterceptor.intercept(chain)
        } catch (t: Throwable) {
            thrown = t
        }
        assertSame(
            "CancellationException 必须重新抛出（不得被包装成 IOException）",
            original,
            thrown
        )
    }

    @Test
    fun okHttpException_intercept_ioException_rethrownUnchanged() {
        val original = IOException("io failure")
        val chain = fakeInterceptorChain { throw original }
        var thrown: Throwable? = null
        try {
            OkHttpExceptionInterceptor.intercept(chain)
        } catch (t: Throwable) {
            thrown = t
        }
        assertSame("IOException 须原样抛出", original, thrown)
    }
}
