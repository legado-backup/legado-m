package io.legado.app.ui.book.manga

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W7 8.1 / REQ-28：漫画**当前页长按 → 保存 / 分享**的接线不变量。
 *
 * 根因（实证）：`WebtoonRecyclerView.longTapListener`（声明 `WebtoonRecyclerView.kt:44`、
 * 调用 `:258`）此前**全仓零赋值** ⇒ 长按事件空转、用户长按无任何反馈。
 * 本批给宿主赋值，并强制复用 W5 的命名/分享单源（禁另起一套）。
 */
class ReadMangaLongTapSaveTest {

    private fun activity(): String =
        SourceFileProbe.sourceText("ui/book/manga/ReadMangaActivity.kt").replace("\r\n", "\n")

    @Test
    fun longTapListenerIsWired() {
        val s = activity()
        assertTrue(
            "必须给 `longTapListener` 赋值（否则长按空转，REQ-28 不成立）",
            s.contains("longTapListener = {")
        )
        assertTrue("长按须回调到操作菜单", s.contains("showMangaPageActions()"))
        assertTrue(
            "长按监听须返回 true（触发触感反馈，语义见 WebtoonRecyclerView.onLongTapConfirmed）",
            Regex("""longTapListener = \{[\s\S]{0,80}?true[\s\S]{0,20}?\}""").containsMatchIn(s)
        )
    }

    @Test
    fun saveAndShareReuseW5SingleSource() {
        val s = activity()
        assertTrue(
            "命名必须复用 `ImageFileNameBuilder.build(`（W5 6.5 单源）",
            s.contains("ImageFileNameBuilder.build(")
        )
        assertTrue(
            "目录内去重必须复用 `ImageFileNameBuilder.uniqueNameFor(`",
            s.contains("ImageFileNameBuilder.uniqueNameFor(")
        )
        assertTrue(
            "分享必须复用 `ImageShareHelper.shareImage(`（W5 6.4 单源，禁另起一套）",
            s.contains("ImageShareHelper.shareImage(")
        )
    }

    @Test
    fun currentPageTakenFromCenterView() {
        assertTrue(
            "当前页须取屏幕中心项（与宿主既有的 `findCenterViewPosition()` 口径一致）",
            activity().contains("findCenterViewPosition()")
        )
    }
}