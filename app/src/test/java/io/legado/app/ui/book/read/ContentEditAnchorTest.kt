package io.legado.app.ui.book.read

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R14「选中文字定位编辑」单测。
 *
 * 需求口径（spec R14-1/R14-2）：**offset 优先**（有选区章内坐标即落到选中位置），
 * **缺省回退**（无坐标或章节不一致 ⇒ 沿用既有阅读进度定位，不回归）。
 */
class ContentEditAnchorTest {

    // ---- R14-1：offset 优先 ----
    @Test
    fun r14_1_selectionOffset_winsOverProgress() {
        assertEquals(
            "有选区坐标时必须用选区坐标",
            1200,
            ContentEditAnchor.resolve(
                anchorChapterIndex = 3,
                anchorPos = 1200,
                currentChapterIndex = 3,
                durChapterPos = 10
            )
        )
    }

    /** 章内偏移 0 是合法落点（首段），不得被当成"无坐标"而回退。 */
    @Test
    fun r14_1b_zeroOffset_isStillValidAnchor() {
        assertEquals(
            0,
            ContentEditAnchor.resolve(
                anchorChapterIndex = 3,
                anchorPos = 0,
                currentChapterIndex = 3,
                durChapterPos = 999
            )
        )
    }

    // ---- R14-2：缺省回退 ----
    @Test
    fun r14_2_noAnchor_fallsBackToProgress() {
        assertEquals(
            "无选区坐标（-1）必须回退阅读进度",
            10,
            ContentEditAnchor.resolve(
                anchorChapterIndex = -1,
                anchorPos = -1,
                currentChapterIndex = 3,
                durChapterPos = 10
            )
        )
    }

    /** 选区与当前章节不一致（换章后残留坐标）⇒ 回退进度，避免落到错章位置。 */
    @Test
    fun r14_2b_chapterMismatch_fallsBackToProgress() {
        assertEquals(
            10,
            ContentEditAnchor.resolve(
                anchorChapterIndex = 3,
                anchorPos = 1200,
                currentChapterIndex = 5,
                durChapterPos = 10
            )
        )
    }

    /**
     * 接线不变量（对应设计表「4 入口接线」）：四个既有入口与新增选区入口必须全部经由
     * `ContentEditDialog.create(...)` 统一入口，禁止再出现裸 `ContentEditDialog()` 直接构造，
     * 否则新增入口的锚点语义会被绕过。
     */
    @Test
    fun allEntryPoints_goThroughUnifiedFactory() {
        val rel = "src/main/java/io/legado/app/ui/book/read/ReadBookActivity.kt"
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        val file = candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        val code = file.readLines()
            .filterNot { it.trimStart().startsWith("*") || it.trimStart().startsWith("//") }
            .joinToString("\n")

        val factoryHits = Regex("ContentEditDialog\\.create\\(").findAll(code).count()
        assertTrue("统一入口 ContentEditDialog.create(...) 至少应出现 1 次，实际 $factoryHits", factoryHits >= 1)

        val rawHits = Regex("showDialogFragment\\(ContentEditDialog\\(\\)\\)").findAll(code).count()
        assertEquals("不得残留裸构造的入口（应改走统一入口）", 0, rawHits)

        val editHereHits = Regex("R\\.id\\.menu_edit_here").findAll(code).count()
        assertTrue("选中菜单「编辑此处」入口必须已接线，实际 $editHereHits", editHereHits >= 1)
    }
}