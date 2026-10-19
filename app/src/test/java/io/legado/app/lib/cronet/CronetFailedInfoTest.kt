package io.legado.app.lib.cronet

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 【2026-10-19 网络层修复】失败回调「三元信息」的**空安全**护栏（`failedInfoTriple`）。
 *
 * 语义：Cronet 在**失败/取消**路径会把 `UrlResponseInfo` 打回 **null** —— 若按非空处理，Kotlin 生成的非空检查
 * 会在回调里抛 `NullPointerException: Parameter specified as non-null is null`（真机 logcat 铁证：
 * 一轮巡检 onFailed **187** 次 + onCanceled **170** 次）⇒ `safeError()` 执行不到 ⇒ 挂起协程**不 resume**
 * ⇒ 只能等 OkHttp `callTimeout`（30s）超时 ⇒ **网络层自愈（坏 IP 重试）拿不到连接层异常而无法触发**
 * （真机失败耗时**中位数恰 30004ms** 即此症）。本函数保证 `null` 输入不抛、且 **URL 只落路径片段**（输出安全）。
 */
class CronetFailedInfoTest {

    @Test
    fun allNull_yieldsSafeDefaults() {
        val (protocol, code, path) = failedInfoTriple(null, null, null)
        assertEquals("", protocol)
        assertEquals(0, code)
        assertEquals("", path)
    }

    @Test
    fun normalValues_passThroughAndStripHostAndQuery() {
        val (protocol, code, path) = failedInfoTriple(
            "h2", 500, "https://abc.example/chapter/1?a=1#frag"
        )
        assertEquals("h2", protocol)
        assertEquals(500, code)
        // 只保留路径片段：**不含域名**（输出安全规范）
        assertEquals("chapter/1?a=1#frag", path)
    }

    @Test
    fun emptyProtocol_andZeroCode_arePreserved() {
        val (protocol, code, path) = failedInfoTriple("", 0, "http://h/x")
        assertEquals("", protocol)
        assertEquals(0, code)
        assertEquals("x", path)
    }
}
