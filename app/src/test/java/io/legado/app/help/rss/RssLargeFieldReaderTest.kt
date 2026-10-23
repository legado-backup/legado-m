package io.legado.app.help.rss

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * 订阅大字段安全读取器（2026-10-23 js-source-parity-and-crash-fix R5）。
 *
 * 真机铁证：`SQLiteBlobTooBigException: Row too big to fit into CursorWindow`
 * —— 单行 `image` 超窗即崩。本测试用**内存假数据源**钉住全部分支，不依赖 Room/设备。
 */
class RssLargeFieldReaderTest {

    /** 假数据源：模拟"字段存在库里"的 length/substr 语义（offset 为 0 基）。 */
    private fun sourceOf(value: String?): Pair<suspend () -> Long?, suspend (Int, Int) -> String?> {
        val lengthOf: suspend () -> Long? = { value?.length?.toLong() }
        val chunk: suspend (Int, Int) -> String? = { offset, count ->
            value?.substring(offset, minOf(offset + count, value.length))
        }
        return lengthOf to chunk
    }

    @Test
    fun smallFieldReadInSingleChunk() = runBlocking {
        val value = "a".repeat(RssLargeFieldReader.ChunkChars)
        val (lengthOf, chunk) = sourceOf(value)
        var chunkCalls = 0
        val result = RssLargeFieldReader.read(lengthOf) { offset, count ->
            chunkCalls++
            chunk(offset, count)
        }
        // 恰好等于阈值 ⇒ 仍走一次取回（行为与改造前逐字节一致）
        assertEquals(1, chunkCalls)
        assertEquals(value, result)
    }

    @Test
    fun oversizedFieldIsConcatenatedCompletely() = runBlocking {
        val value = "第一章正文。".repeat(200_000) // 1,200,000 字符 > 256K 阈值
        val (lengthOf, chunk) = sourceOf(value)
        val offsets = mutableListOf<Int>()
        val result = RssLargeFieldReader.read(lengthOf) { offset, count ->
            offsets += offset
            chunk(offset, count)
        }
        assertEquals("分块读取必须完整还原原值（不裁剪、不置空）", value, result)
        assertEquals("每块必须是 ChunkChars", RssLargeFieldReader.ChunkChars, offsets[1] - offsets[0])
        assertEquals("块数应为 ceil(len/chunk)", 5, offsets.size)
    }

    @Test
    fun nullAndEmptyFieldHandled() = runBlocking {
        val (nullLength, nullChunk) = sourceOf(null)
        assertNull("字段为 NULL ⇒ 返回 null", RssLargeFieldReader.read(nullLength, nullChunk))

        val (emptyLength, emptyChunk) = sourceOf("")
        assertEquals("空串 ⇒ 返回空串（不是 null）", "", RssLargeFieldReader.read(emptyLength, emptyChunk))
    }

    @Test
    fun readExceptionYieldsNullInsteadOfCrash() = runBlocking {
        val lengthOf: suspend () -> Long? = { 10L }
        val failingChunk: suspend (Int, Int) -> String? = { _, _ -> throw IllegalStateException("boom") }
        assertNull(
            "读取失败必须返回 null（不崩、也不静默截断）",
            RssLargeFieldReader.read(lengthOf, failingChunk)
        )
    }

    @Test
    fun lengthExceptionYieldsNullInsteadOfCrash() = runBlocking {
        val failingLength: suspend () -> Long? = { throw IllegalStateException("boom") }
        val chunk: suspend (Int, Int) -> String? = { _, _ -> "x" }
        assertNull(RssLargeFieldReader.read(failingLength, chunk))
    }

    @Test
    fun chunkFailureMidwayYieldsNullNotPartialValue() = runBlocking {
        val value = "x".repeat(RssLargeFieldReader.ChunkChars * 2 + 10)
        val (lengthOf, chunk) = sourceOf(value)
        var calls = 0
        val result = RssLargeFieldReader.read(lengthOf) { offset, count ->
            calls++
            // 第 2 块失败：绝不能返回"前半截"内容当正文
            if (calls == 2) throw IllegalStateException("boom")
            chunk(offset, count)
        }
        assertNull(result)
    }

    @Test
    fun exceededChunkCapYieldsNull() = runBlocking {
        val length = (RssLargeFieldReader.MaxChunks.toLong() + 1) * RssLargeFieldReader.ChunkChars
        val lengthOf: suspend () -> Long? = { length }
        var chunkCalls = 0
        val result = RssLargeFieldReader.read(lengthOf) { _, _ ->
            chunkCalls++
            "x"
        }
        assertNull("超过上限必须判为不可读", result)
        assertEquals("超限必须在读取前短路，不得逐块读完", 0, chunkCalls)
    }
}
