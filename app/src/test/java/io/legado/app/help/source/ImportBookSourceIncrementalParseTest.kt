package io.legado.app.help.source

import io.legado.app.data.entities.BookSource
import io.legado.app.exception.NoStackTraceException
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonArray
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * REQ-05 / AD-13：书源 JSON 数组**增量解析**单测。
 *
 * 验收口径（tasks 1.2.1）：① 「流式 vs 一次性」逐条结果一致；② 超 [BookSourceIncrementalParser.MAX_IMPORT_COUNT]
 * 与超 maxBytes 在**读取阶段**拒绝；③ 失败**不留半成品**；④ 首条空 URL / 空数组语义与原实现一致。
 */
class ImportBookSourceIncrementalParseTest {

    private fun sourceJson(name: String, url: String): String =
        """{"bookSourceName":"$name","bookSourceUrl":"$url","bookSourceGroup":"g"}"""

    private fun arrayJson(vararg items: String): String = items.joinToString(",", "[", "]")

    private fun sampleArray(count: Int): String = arrayJson(
        *Array(count) { sourceJson("源$it", "https://example.com/$it") }
    )

    @Test
    fun incrementalResultMatchesOneShotForEachItem() = runBlocking {
        val json = sampleArray(50)
        val incremental = runBlocking {
            val list = arrayListOf<BookSource>()
            BookSourceIncrementalParser.parseBookSourcesIncrementalInto(
                json.byteInputStream(), list
            )
            list
        }
        val oneShot = GSON.fromJsonArray<BookSource>(json).getOrThrow()
        assertEquals("条目数须与一次性解析一致", oneShot.size, incremental.size)
        oneShot.forEachIndexed { index, expected ->
            assertEquals("第 $index 条 bookSourceName 不一致", expected.bookSourceName, incremental[index].bookSourceName)
            assertEquals("第 $index 条 bookSourceUrl 不一致", expected.bookSourceUrl, incremental[index].bookSourceUrl)
        }
    }

    @Test
    fun exceedingMaxCountIsRejectedAtReadStage() = runBlocking {
        val json = sampleArray(5)
        val target = arrayListOf<BookSource>()
        val error = assertThrows(ImportLimitExceededException::class.java) {
            runBlocking {
                BookSourceIncrementalParser.parseBookSourcesIncrementalInto(
                    json.byteInputStream(), target, maxCount = 2
                )
            }
        }
        assertTrue("超条目数提示须含上限值", error.message!!.contains("2"))
        assertTrue("失败后不得留半成品", target.isEmpty())
    }

    @Test
    fun exceedingMaxBytesIsRejectedWhileReading() {
        val json = sampleArray(200)
        val target = arrayListOf<BookSource>()
        assertThrows(ImportLimitExceededException::class.java) {
            runBlocking {
                BookSourceIncrementalParser.parseBookSourcesIncrementalInto(
                    json.byteInputStream(), target, maxBytes = 64
                )
            }
        }
        assertTrue("超字节上限被拒绝时不得留半成品", target.isEmpty())
    }

    @Test
    fun malformedItemCarriesIndexAndLeavesNoHalfProduct() {
        val json = arrayJson(
            sourceJson("好源1", "https://example.com/1"),
            sourceJson("好源2", "https://example.com/2"),
            """{"bookSourceName":"坏源","bookSourceUrl":}"""
        )
        val target = arrayListOf<BookSource>()
        val error = assertThrows(ImportItemParseException::class.java) {
            runBlocking {
                BookSourceIncrementalParser.parseBookSourcesIncrementalInto(json.byteInputStream(), target)
            }
        }
        assertEquals("异常须携带出错条目序号（0 起）", 2, error.index)
        assertTrue("失败必须回滚已并入条目（不留半成品）", target.isEmpty())
    }

    @Test
    fun emptyArrayIsNoOpAndNotEmptyIsRejected() = runBlocking {
        val target = arrayListOf<BookSource>()
        val count = BookSourceIncrementalParser.parseBookSourcesIncrementalInto(
            "[]".byteInputStream(), target
        )
        assertEquals("空数组不产生条目", 0, count)
        assertTrue(target.isEmpty())

        val blankUrlTarget = arrayListOf<BookSource>()
        assertThrows(NoStackTraceException::class.java) {
            runBlocking {
                BookSourceIncrementalParser.parseBookSourcesIncrementalInto(
                    arrayJson("""{"bookSourceName":"x","bookSourceUrl":""}""").byteInputStream(),
                    blankUrlTarget
                )
            }
        }
        assertTrue("首条空 URL 判「不是书源」时也不得留半成品", blankUrlTarget.isEmpty())
    }

    @Test
    fun intoWrapperAppendsToExistingTargetWithoutDroppingPreviousItems() = runBlocking {
        val target = arrayListOf(BookSource(bookSourceName = "既有源", bookSourceUrl = "https://old.example.com"))
        val count = BookSourceIncrementalParser.parseBookSourcesIncrementalInto(
            arrayJson(sourceJson("新源", "https://new.example.com")).byteInputStream(), target
        )
        assertEquals(1, count)
        assertEquals("既有条目不得被清掉", 2, target.size)
        assertEquals("既有源", target[0].bookSourceName)
        assertEquals("新源", target[1].bookSourceName)
    }

    @Test
    fun limitedInputStreamStopsExactlyAtBudget() {
        val bytes = ByteArray(100) { it.toByte() }
        val limited = LimitedInputStream(bytes.inputStream(), maxBytes = 10)
        val buffer = ByteArray(8)
        assertEquals(8, limited.read(buffer))
        assertEquals(8L, limited.bytesRead)
        // 第二次读越界：抛上限异常（不把整个流读完）
        assertThrows(ImportLimitExceededException::class.java) { limited.read(buffer) }
    }
}