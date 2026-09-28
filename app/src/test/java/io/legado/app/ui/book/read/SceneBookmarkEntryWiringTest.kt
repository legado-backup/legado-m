package io.legado.app.ui.book.read

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.3（REQ-32）：**文字路径打标入口**接线不变量。
 *
 * 本仓在「选区动作」上已两次踩同一坑（B2.5 划线 / R14 编辑此处）：动作要经 **4 处链路**
 * 才可能被用户看到 —— `content_select_action.xml`（菜单项）→ `ContentSelectConfig`（动作常量 + 新用户默认集）
 * → `ContentSelectMenuConfigDialog.actionItems`（配置页白名单派生源，漏登记则用户保存一次后被静默剔除）
 * → `TextActionMenu.menuItemToActionId`（itemId→actionId 映射，漏登记则菜单里静默消失）。
 *
 * 另锁**阅读菜单双项**（打标 + 本书名场面）与打标载荷口径（文字路径必须带选中文本 + 章内坐标锚点）。
 */
class SceneBookmarkEntryWiringTest {

    private fun selectMenuXml(): String =
        SourceFileProbe.sourceTextByPath("src/main/res/menu/content_select_action.xml")

    private fun readMenuXml(): String =
        SourceFileProbe.sourceTextByPath("src/main/res/menu/book_read.xml")

    private fun config(): String = SourceFileProbe.sourceText("ui/book/read/ContentSelectConfig.kt")

    private fun actionMenu(): String = SourceFileProbe.sourceText("ui/book/read/TextActionMenu.kt")

    private fun configDialog(): String =
        SourceFileProbe.sourceText("ui/book/read/config/ContentSelectMenuConfigDialog.kt")

    private fun readActivity(): String =
        SourceFileProbe.sourceText("ui/book/read/ReadBookActivity.kt")

    @Test
    fun selectionActionIsWiredThroughAllFourTouchPoints() {
        assertTrue(
            "① 选区菜单 XML 未登记 menu_scene_bookmark",
            selectMenuXml().contains("android:id=\"@+id/menu_scene_bookmark\"")
        )
        assertTrue(
            "② 动作常量缺失",
            config().contains("const val ACTION_SCENE_BOOKMARK = \"scene_bookmark\"")
        )
        assertTrue(
            "③ 未登记进配置页白名单（保存一次后该动作会被静默剔除）",
            configDialog().contains("ActionItem(ContentSelectConfig.ACTION_SCENE_BOOKMARK")
        )
        assertTrue(
            "④ itemId→actionId 映射缺失（菜单项会被静默丢弃）",
            actionMenu().contains(
                "R.id.menu_scene_bookmark -> ContentSelectConfig.ACTION_SCENE_BOOKMARK"
            )
        )
    }

    @Test
    fun selectionActionIsVisibleForNewUsersWithoutTouchingLegacySets() {
        val s = config()
        val defaults = s.substringAfter("val defaultActions = setOf(")
            .substringBefore("val defaultOpenValues")
        val legacy = s.substringAfter("private val legacyDefaultActions = setOf(")
            .substringBefore("private val defaultActionsBeforeShare")
        assertTrue(
            "新用户默认集合应包含「加入名场面」",
            defaults.contains("ACTION_SCENE_BOOKMARK")
        )
        assertTrue(
            "legacy 迁移集合不得被改动（改动会使老用户偏好迁移失效）",
            !legacy.contains("ACTION_SCENE_BOOKMARK")
        )
    }

    @Test
    fun selectionMenuTapCreatesTextSceneWithAnchor() {
        val code = readActivity()
        assertTrue(
            "选区菜单未分发到打标方法",
            code.contains("R.id.menu_scene_bookmark -> {") &&
                code.contains("addSceneBookmarkBySelection()")
        )
        assertTrue(
            "文字路径必须带原文片段与章内坐标锚点",
            code.contains("text = text") &&
                code.contains("anchor = SceneBookmarkHelper.textAnchor(chapterPos)")
        )
        assertTrue(
            "文字路径 contentKind 必须为 KIND_TEXT",
            code.contains("contentKind = SceneBookmarkHelper.KIND_TEXT")
        )
    }

    @Test
    fun readMenuCarriesBothAddAndLibraryEntries() {
        val xml = readMenuXml()
        assertTrue(
            "阅读菜单缺「加入名场面」",
            xml.contains("android:id=\"@+id/menu_add_scene_bookmark\"")
        )
        assertTrue(
            "阅读菜单缺「本书名场面」",
            xml.contains("android:id=\"@+id/menu_scene_bookmark_list\"")
        )
        val code = readActivity()
        assertTrue(
            "打标菜单项未分发",
            code.contains("R.id.menu_add_scene_bookmark -> addSceneBookmarkFromReadMenu()")
        )
        assertTrue(
            "库页菜单项未分发",
            code.contains("R.id.menu_scene_bookmark_list -> openSceneBookmarkLibrary()")
        )
        assertTrue(
            "库页入口须按书过滤（bookIntent 带 bookUrl）",
            code.contains("SceneBookmarkActivity.bookIntent(this, book.bookUrl, book.name, book.author)")
        )
    }

    @Test
    fun sceneMenuIdsDoNotCollideWithOtherMenus() {
        val readIds = Regex("android:id=\"@\\+id/(menu_[a-z_]*scene[a-z_]*)\"")
            .findAll(readMenuXml()).map { it.groupValues[1] }.toSet()
        val selectIds = Regex("android:id=\"@\\+id/(menu_[a-z_]*scene[a-z_]*)\"")
            .findAll(selectMenuXml()).map { it.groupValues[1] }.toSet()
        assertTrue("两菜单不应复用同名 id（避免误分发）", readIds.intersect(selectIds).isEmpty())
    }
}
