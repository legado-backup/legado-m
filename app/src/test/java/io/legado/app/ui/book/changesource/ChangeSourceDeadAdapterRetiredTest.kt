package io.legado.app.ui.book.changesource

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 死件退役配对测试（换源对话框族）。
 *
 * 背景（实测取证 2026-09-26）：`ChangeBookSourceAdapter` / `ChangeChapterSourceAdapter` /
 * `ChangeChapterTocAdapter` 三个 View 层 Adapter 的宿主界面已整体 Compose 化
 * （`ChangeBookSourceDialog` / `ChangeChapterSourceDialog` 用 `LazyColumn` + 行内 `@Composable`），
 * 三个 Adapter **从未被实例化**（全仓仅自身文件命中）⇒ 连同其 inflate 的
 * `item_change_source` / `item_chapter_list` 一并退役，仅保留回调接口（移至
 * `ChangeSourceCallbacks.kt`）。
 *
 * 本测试锁住「不得回退」：死件与死布局不得复活，且对话框必须改挂新契约。
 */
class ChangeSourceDeadAdapterRetiredTest {

    private fun mainJava(rel: String): File =
        File(SourceFileProbe.mainJavaRoot(), "io/legado/app/$rel")

    private fun layout(name: String): File =
        File(SourceFileProbe.layoutDir(), name)

    @Test
    fun deadAdaptersAreGone() {
        listOf(
            "ui/book/changesource/ChangeBookSourceAdapter.kt",
            "ui/book/changesource/ChangeChapterSourceAdapter.kt",
            "ui/book/changesource/ChangeChapterTocAdapter.kt"
        ).forEach { rel ->
            assertFalse("死 Adapter 应已退役：$rel", mainJava(rel).isFile)
        }
    }

    @Test
    fun deadItemLayoutsAreGone() {
        listOf("item_change_source.xml", "item_chapter_list.xml").forEach { name ->
            assertFalse("死 item 布局应已退役：$name", layout(name).isFile)
        }
    }

    @Test
    fun callbackContractsMovedOutOfAdapterNamespace() {
        val contract = SourceFileProbe.sourceText("ui/book/changesource/ChangeSourceCallbacks.kt")
        listOf(
            "interface ChangeBookSourceCallback",
            "interface ChangeChapterSourceCallback",
            "interface ChangeChapterTocCallback"
        ).forEach { decl ->
            assertTrue("回调契约缺失：$decl", contract.contains(decl))
        }
    }

    @Test
    fun dialogsImplementNewContracts() {
        val book = SourceFileProbe.sourceText("ui/book/changesource/ChangeBookSourceDialog.kt")
        assertTrue("ChangeBookSourceDialog 应实现 ChangeBookSourceCallback", book.contains("ChangeBookSourceCallback"))
        assertFalse(
            "ChangeBookSourceDialog 不得再引用已退役的 Adapter 契约",
            book.contains("ChangeBookSourceAdapter")
        )

        val chapter = SourceFileProbe.sourceText("ui/book/changesource/ChangeChapterSourceDialog.kt")
        assertTrue(
            "ChangeChapterSourceDialog 应实现 ChangeChapterSourceCallback",
            chapter.contains("ChangeChapterSourceCallback")
        )
        assertTrue(
            "ChangeChapterSourceDialog 应实现 ChangeChapterTocCallback",
            chapter.contains("ChangeChapterTocCallback")
        )
        assertFalse(
            "ChangeChapterSourceDialog 不得再引用已退役的 Adapter 契约",
            chapter.contains("ChangeChapterSourceAdapter") || chapter.contains("ChangeChapterTocAdapter")
        )
    }
}