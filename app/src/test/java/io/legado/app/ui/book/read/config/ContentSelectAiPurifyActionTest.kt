package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Q-N4 选中文字「AI 净化」动作的**配置白名单**不变量。
 *
 * 缺陷型（B2.5 划线 / R14 编辑此处已两次踩过同一坑）：`ContentSelectMenuConfigDialog.sanitizeActionIds`
 * 的白名单由 `actionItems` 列表派生 —— 新增动作若**未登记**在此，用户在选区菜单配置页保存一次后
 * 该动作会被**静默剔除**、菜单里永久消失（表现「功能做完了但用户看不到」）。
 */
class ContentSelectAiPurifyActionTest {

    private fun configDialog(): String =
        SourceFileProbe.sourceText("ui/book/read/config/ContentSelectMenuConfigDialog.kt")

    private fun selectConfig(): String =
        SourceFileProbe.sourceText("ui/book/read/ContentSelectConfig.kt")

    private fun menuXml(): String =
        SourceFileProbe.sourceTextByPath("src/main/res/menu/content_select_action.xml")

    private fun actionMenu(): String = SourceFileProbe.sourceText("ui/book/read/TextActionMenu.kt")

    @Test
    fun aiPurifyAction_isRegisteredInWhitelist() {
        val code = configDialog()
        assertTrue(
            "「AI 净化」必须登记在 actionItems（否则保存配置后会被静默剔除）",
            code.contains("ActionItem(ContentSelectConfig.ACTION_AI_PURIFY")
        )
        assertTrue("动作文案须有字符串资源", code.contains("R.string.ai_purify"))
    }

    @Test
    fun aiPurifyAction_isWiredThroughMenuPipeline() {
        assertTrue(
            "动作常量缺失",
            selectConfig().contains("const val ACTION_AI_PURIFY = \"ai_purify\"")
        )
        assertTrue(
            "菜单 XML 未登记 menu_ai_purify",
            menuXml().contains("android:id=\"@+id/menu_ai_purify\"")
        )
        assertTrue(
            "itemId → actionId 映射缺失（菜单项会被静默丢弃）",
            actionMenu().contains("R.id.menu_ai_purify -> ContentSelectConfig.ACTION_AI_PURIFY")
        )
    }

    @Test
    fun aiPurifyAction_isDefaultVisibleForNewUsers() {
        val code = selectConfig()
        val start = code.indexOf("val defaultActions = setOf(")
        val end = code.indexOf("val defaultOpenValues", start)
        assertTrue("defaultActions 边界漂移", start >= 0 && end > start)
        assertTrue(
            "新用户默认集合应包含 AI 净化（老用户偏好集合保持不动）",
            code.substring(start, end).contains("ACTION_AI_PURIFY")
        )
    }
}