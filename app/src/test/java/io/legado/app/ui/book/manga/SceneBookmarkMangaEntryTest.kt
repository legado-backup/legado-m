package io.legado.app.ui.book.manga

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.3（REQ-32）：**漫画路径打标入口**接线不变量。
 *
 * 该页菜单有一处**易失守点**：`ReadMangaActivity.upMenu` 会把 `mangaConfigMenuItems` 数组里的项
 * **全部置为 invisible**（它们改由「漫画配置」二级弹层承载）。新增菜单项若被误加进该数组，
 * 入口会在 `onCreateOptionsMenu` 之后立刻被隐藏 ⇒ 表现为「功能做了但用户看不见」。
 */
class SceneBookmarkMangaEntryTest {

    private fun menuXml(): String =
        SourceFileProbe.sourceTextByPath("src/main/res/menu/book_manga.xml")

    private val activity by lazy { SourceFileProbe.sourceText("ui/book/manga/ReadMangaActivity.kt") }

    @Test
    fun menuItemIsDeclaredInMangaMenu() {
        assertTrue(
            "漫画菜单缺「加入名场面」项",
            menuXml().contains("android:id=\"@+id/menu_add_scene_bookmark\"")
        )
    }

    @Test
    fun menuItemIsNotSwallowedByMangaConfigWhitelist() {
        val array = activity.substringAfter("private val mangaConfigMenuItems = intArrayOf(")
            .substringBefore(")")
        assertTrue(
            "新项**不得**进 mangaConfigMenuItems（进则被 upMenu 置为 invisible ⇒ 入口不可见）",
            !array.contains("menu_add_scene_bookmark")
        )
    }

    @Test
    fun tapCreatesMangaSceneWithPageAnchor() {
        assertTrue(
            "漫画菜单未分发到打标方法",
            activity.contains("R.id.menu_add_scene_bookmark -> addSceneBookmarkFromManga()")
        )
        assertTrue(
            "漫画路径 contentKind 必须为 KIND_MANGA",
            activity.contains("contentKind = SceneBookmarkHelper.KIND_MANGA")
        )
        assertTrue(
            "漫画锚点必须取当前页下标（durChapterPos）",
            activity.contains("anchor = SceneBookmarkHelper.mangaAnchor(ReadManga.durChapterPos)")
        )
    }
}
