package io.legado.app.service

import io.legado.app.exception.NoStackTraceException
import io.legado.app.exception.TocEmptyException
import kotlinx.coroutines.TimeoutCancellationException
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException
import java.net.UnknownHostException

/**
 * 【AD-10，2026-10-18】「网络类失败重试」判据（`shouldRetryNetworkFailure`）的行为护栏。
 *
 * 语义：**仅网络类异常且非存疑源**才重试 —— 瞬时网络抖动 / 站点限流不应把其实可用的源判死
 * （实测「校验所选」SEARCH/DISCOVERY 段约 1/3 失败在本机无法复现，bug_report B-52）；
 * 超时 / 脚本 / 规则类为**确定性失败**，重试无益只涨耗时；存疑源失败不可归因于源本身，走跳过口径。
 */
class CheckSourceNetworkRetryTest {

    /** `TimeoutCancellationException` 构造函数为 internal ⇒ 用**真实超时现场**产出实例（同 `CheckFailureClassificationTest`）。 */
    private fun timeout(): TimeoutCancellationException = kotlinx.coroutines.runBlocking {
        try {
            kotlinx.coroutines.withTimeout(1) { kotlinx.coroutines.delay(80) }
            throw AssertionError("应当超时")
        } catch (t: TimeoutCancellationException) {
            t
        }
    }

    @Test
    fun networkException_isRetriable() {
        assertTrue(shouldRetryNetworkFailure(UnknownHostException("h"), null, elapsedMs = 300))
        assertTrue(shouldRetryNetworkFailure(IOException("boom"), null, elapsedMs = 1_500))
    }

    @Test
    fun timeout_isNotRetriable() {
        assertFalse(shouldRetryNetworkFailure(timeout(), null, elapsedMs = 300))
    }

    @Test
    fun slowFailure_isNotRetriable() {
        // 实测失败耗时中位数 = 30004ms（打满 HTTP 超时）⇒ 重试只会再等一个超时，不重试
        assertFalse(shouldRetryNetworkFailure(UnknownHostException("h"), null, elapsedMs = 30_004))
        assertFalse(
            shouldRetryNetworkFailure(
                IOException("read timeout"), null, elapsedMs = NETWORK_RETRY_FAST_FAIL_MS
            )
        )
    }

    @Test
    fun businessException_isNotRetriable() {
        // NoStackTraceException 携带引擎侧明确结论（目录/正文/规则为空）⇒ 确定性失败
        assertFalse(shouldRetryNetworkFailure(TocEmptyException("目录为空"), null, 200))
        assertFalse(shouldRetryNetworkFailure(NoStackTraceException("规则为空"), null, 200))
    }

    @Test
    fun suspectSource_isNotRetriableEvenIfNetwork() {
        // 存疑源失败不可归因于源本身（登录/jsLib/源变量/webView/内网）⇒ 不重试，直接走跳过
        assertFalse(
            shouldRetryNetworkFailure(
                UnknownHostException("h"),
                suspectLabel = "存疑（登录依赖）",
                elapsedMs = 300,
            )
        )
    }
}
