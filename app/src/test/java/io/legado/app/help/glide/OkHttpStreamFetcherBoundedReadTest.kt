package io.legado.app.help.glide

import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.ResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * AD-03(enhance-switch-governance-fix): readBounded 有界缓冲单测（T6 JVM 层）
 * 覆盖：未超限 / 恰好等于 limit / 超限 / 空 body
 * chunked 无长度场景由 ResponseBody.create 不带 content-length 天然模拟（contentLength()=-1）
 */
class OkHttpStreamFetcherBoundedReadTest {

    private fun bodyOf(bytes: ByteArray): ResponseBody =
        ResponseBody.create("application/octet-stream".toMediaTypeOrNull(), bytes)

    @Test
    fun underLimitReturnsNotExceededWithFullBytes() {
        val data = ByteArray(1024) { (it % 251).toByte() }
        val r = OkHttpStreamFetcher.readBounded(bodyOf(data), limit = 10L * 1024 * 1024)
        assertFalse(r.exceeded)
        assertEquals(data.size, r.bytes.size)
        assertEquals(data[0], r.bytes[0])
        assertEquals(data[1023], r.bytes[1023])
    }

    @Test
    fun exactlyLimitIsNotExceeded() {
        // 与既有 contentLength > SKIP 语义一致：恰好等于阈值不算超大
        val data = ByteArray(1024)
        val r = OkHttpStreamFetcher.readBounded(bodyOf(data), limit = 1024L)
        assertFalse(r.exceeded)
        assertEquals(1024, r.bytes.size)
    }

    @Test
    fun overLimitIsExceededAndBufferWithinBound() {
        val data = ByteArray(2048)
        val r = OkHttpStreamFetcher.readBounded(bodyOf(data), limit = 1024L)
        assertTrue(r.exceeded)
        // 64KB 分块粒度：超出即停，缓冲量 > limit 但 ≤ limit + 64KB
        assertTrue(r.bytes.size > 1024)
        assertTrue(r.bytes.size <= 1024 + 64 * 1024)
    }

    @Test
    fun emptyBodyNotExceeded() {
        val r = OkHttpStreamFetcher.readBounded(bodyOf(ByteArray(0)), limit = 1024L)
        assertFalse(r.exceeded)
        assertEquals(0, r.bytes.size)
    }
}
