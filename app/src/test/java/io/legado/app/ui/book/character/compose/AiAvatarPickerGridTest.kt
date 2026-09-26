package io.legado.app.ui.book.character.compose

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：`item_ai_generated_image` 退役（AI 图库头像选择网格 View → Compose）。
 *
 * 换装前：`BookCharacterEditActivity` 内 `GalleryAvatarAdapter : RecyclerAdapter<…, ItemAiGeneratedImageBinding>`
 * + `RecyclerView(GridLayoutManager(3))`，条目 inflate `item_ai_generated_image.xml`（`CardView` 卡片）。
 * 换装后：`ComposeView` + `AiAvatarPickerGrid`（`LazyVerticalGrid(Fixed(3))`），卡片为 Compose 实现。
 *
 * 锁住三条：①死布局不得复活 ②宿主不得残留 View 版 Adapter 痕迹 ③新网格必须走主题面 token（禁硬编码色）。
 */
class AiAvatarPickerGridTest {

    private fun mainJava(rel: String): File =
        File(SourceFileProbe.mainJavaRoot(), "io/legado/app/$rel")

    private fun gridSource(): String =
        SourceFileProbe.sourceText("ui/book/character/compose/AiAvatarPickerGrid.kt")

    private fun hostSource(): String =
        SourceFileProbe.sourceText("ui/book/character/BookCharacterEditActivity.kt")

    @Test
    fun deadItemLayoutIsGone() {
        assertFalse(
            "死 item 布局应已退役：item_ai_generated_image.xml",
            File(SourceFileProbe.layoutDir(), "item_ai_generated_image.xml").isFile
        )
    }

    @Test
    fun hostNoLongerHasViewAdapter() {
        val host = hostSource()
        assertFalse(host.contains("ItemAiGeneratedImageBinding"))
        assertFalse(host.contains("GalleryAvatarAdapter"))
        assertFalse(host.contains("RecyclerAdapter<"))
        assertFalse(host.contains("GridLayoutManager"))
        assertTrue("宿主须改挂 Compose 网格单源", host.contains("AiAvatarPickerGrid("))
        assertTrue("过滤结果须以 state 驱动重组（替代 adapter.setItems）", host.contains("gridItems.value ="))
    }

    @Test
    fun gridUsesThreeColumnsAndThemeTokens() {
        val grid = gridSource()
        assertTrue(grid.contains("LazyVerticalGrid("))
        assertTrue("列数须与原 GridLayoutManager(3) 等价", grid.contains("GridCells.Fixed(3)"))
        assertTrue("卡片底色须走主题面 token（cardColor）", grid.contains("themeUiPalette.cardColor"))
        assertTrue("文字色须走主题 token（primaryText/secondaryText）",
            grid.contains("palette.primaryText") && grid.contains("palette.secondaryText"))
        assertTrue("收藏态字色须走 accent token", grid.contains("palette.accent"))
        // 禁止硬编码色字面量（合 theme-consistency-iron-rule：取色只走 token）
        assertFalse(
            "不得出现 Color(0x…) 这类硬编码色",
            Regex("Color\\(0x").containsMatchIn(grid)
        )
    }

    @Test
    fun promptRowSemanticsPreserved() {
        val grid = gridSource()
        // 原 convert 的 buildList 口径：书名/章节/角色 非空才拼，末尾追加提示词（压空白、截 48 字）
        assertTrue(grid.contains("item.bookName.takeIf { it.isNotBlank() }?.let(::add)"))
        assertTrue(grid.contains("item.chapterTitle.takeIf { it.isNotBlank() }?.let(::add)"))
        assertTrue(grid.contains("item.characterName.takeIf { it.isNotBlank() }?.let(::add)"))
        assertTrue(grid.contains("joinToString(\" · \")"))
    }
}