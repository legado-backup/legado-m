package io.legado.app.service.kernel

import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookProgress
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * BookKernel 单测（一期 · 2.1 / REQ-1-201 · REQ-1-202 · REQ-1-308 · REQ-1-309）。
 *
 * 三类断言：
 * 1. **纯逻辑直测**（无需 Android）：书架排序 / 进度校验 / 正文分页切片；
 * 2. **回归护栏**：决策 #12 的"不得据章节表判越界"必须成立 —— 若有人照原设计加硬拒，
 *    本测试会立刻变红（该端点被内置阅读器跨端同步使用，误拒＝真实功能回归）；
 * 3. **结构不变量（源码扫描）**：Kernel 内**零 `runBlocking`**、Controller **不碰 DAO** 且确实委派 Kernel。
 *    （本项目既有范式：appDb 依赖 Room+Context，纯 JVM 构造不出，故结构断言由源码扫描承担。）
 */
class BookKernelTest {

    private fun book(
        name: String,
        order: Int = 0,
        latestChapterTime: Long = 0L,
        durChapterTime: Long = 0L,
    ) = Book(
        bookUrl = "u-$name",
        name = name,
        author = "a",
        order = order,
        latestChapterTime = latestChapterTime,
        durChapterTime = durChapterTime,
    )

    // ------------------------------------------------------------ 书架排序

    @Test
    fun sortedByMode_mode1_sortsByLatestChapterTimeDesc() {
        val older = book("older", latestChapterTime = 100L)
        val newer = book("newer", latestChapterTime = 200L)
        assertEquals(listOf("newer", "older"), BookKernel.sortedByMode(listOf(older, newer), 1).map { it.name })
    }

    @Test
    fun sortedByMode_mode2_sortsByName() {
        val b = book("b")
        val a = book("a")
        assertEquals(listOf("a", "b"), BookKernel.sortedByMode(listOf(b, a), 2).map { it.name })
    }

    @Test
    fun sortedByMode_mode3_sortsByCustomOrderAsc() {
        val third = book("third", order = 3)
        val first = book("first", order = 1)
        assertEquals(listOf("first", "third"), BookKernel.sortedByMode(listOf(third, first), 3).map { it.name })
    }

    @Test
    fun sortedByMode_otherModes_fallBackToDurChapterTimeDesc() {
        val older = book("older", durChapterTime = 10L)
        val newer = book("newer", durChapterTime = 20L)
        listOf(0, 4, -1).forEach { mode ->
            assertEquals(
                "mode=$mode 应回落到最近阅读倒序",
                listOf("newer", "older"),
                BookKernel.sortedByMode(listOf(older, newer), mode).map { it.name },
            )
        }
    }

    @Test
    fun sortedByMode_emptyInput_staysEmpty() {
        assertTrue(BookKernel.sortedByMode(emptyList(), 1).isEmpty())
    }

    // ------------------------------------------------------------ 进度校验（决策 #12）

    private fun progress(index: Int, pos: Int) =
        BookProgress("n", "a", index, pos, 0L, null)

    @Test
    fun validateProgress_nonNegative_isAccepted() {
        assertNull(BookKernel.validateProgress(progress(0, 0)))
        assertNull(BookKernel.validateProgress(progress(12, 3456)))
    }

    @Test
    fun validateProgress_negativeFields_areRejectedWithMessage() {
        assertTrue(BookKernel.validateProgress(progress(-1, 0))!!.contains("章节序号"))
        assertTrue(BookKernel.validateProgress(progress(0, -5))!!.contains("阅读位置"))
    }

    @Test
    fun validateProgress_largeIndex_isAccepted_neverJudgedByChapterRange() {
        // 决策 #12 护栏：**不得**据"本机章节表"判越界 —— 目录可能尚未拉取或与其他端不一致，
        // 硬拒会让合法的跨端进度同步失败（该端点被内置阅读器使用）。
        assertNull("超大步长索引也必须放行（只校验非负）", BookKernel.validateProgress(progress(999_999, 0)))
    }

    // ------------------------------------------------------------ 正文分页（决策 #13）

    @Test
    fun sliceContent_noLimit_returnsWholeContent() {
        val text = "0123456789"
        assertEquals(text, BookKernel.sliceContent(text, 0, BookKernel.CONTENT_NO_LIMIT))
        assertEquals(text, BookKernel.sliceContent(text, 0, -1))
    }

    @Test
    fun sliceContent_withOffsetAndLength() {
        assertEquals("2345", BookKernel.sliceContent("0123456789", 2, 4))
    }

    @Test
    fun sliceContent_lengthOverflow_isClampedToEnd() {
        assertEquals("89", BookKernel.sliceContent("0123456789", 8, 100))
    }

    @Test
    fun sliceContent_offsetBeyondEnd_returnsEmpty() {
        assertEquals("", BookKernel.sliceContent("0123456789", 10, 5))
        assertEquals("", BookKernel.sliceContent("0123456789", 999, BookKernel.CONTENT_NO_LIMIT))
    }

    @Test
    fun sliceContent_negativeOffset_treatedAsZero() {
        assertEquals("01", BookKernel.sliceContent("0123456789", -3, 2))
    }

    // ------------------------------------------------------------ 结构不变量

    /** 剥整行注释后再断言（KDoc 里本就要写 `runBlocking` / `appDb.` 等字样）。 */
    private fun codeOf(relFromMain: String): String {
        val rel = "src/main/$relFromMain"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
            .firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun kernel_hasZeroRunBlocking() {
        val code = codeOf("java/io/legado/app/service/kernel/BookKernel.kt")
        assertTrue("Kernel 内不得出现 runBlocking（REQ-1-202 全链挂起）", !code.contains("runBlocking"))
        assertTrue("Kernel 必须用 withContext(IO) 承接 DAO 访问", code.contains("withContext(IO)"))
    }

    @Test
    fun controller_doesNotTouchDao_andDelegatesToKernel() {
        val code = codeOf("java/io/legado/app/api/controller/BookController.kt")
        assertTrue("Controller 不得再直访 appDb（tasks §2.1.6 判据）", !code.contains("appDb."))
        assertTrue("Controller 不得再出现 Dao 调用", !code.contains("Dao."))
        assertTrue("Controller 必须委派 BookKernel", code.contains("BookKernel."))
    }

    @Test
    fun kernel_doesNotDependOnController_orReturnData() {
        val code = codeOf("java/io/legado/app/service/kernel/BookKernel.kt")
        assertTrue("Kernel 不得 import api.controller（依赖方向门禁 §2.4.1）", !code.contains("api.controller"))
        assertTrue("Kernel 不得返回 HTTP 信封 ReturnData（否则二期 MCP 会被 HTTP 语义污染）", !code.contains("ReturnData"))
    }
}
