package io.legado.app.ui.book.read

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Q-N4 阅读侧接线不变量：阅读菜单（「替换净化」旁）入口 + 统一净化入口 + 选中文字分发。
 *
 * 为什么必须机检：该链路跨 5 个文件（回调数据结构 / 溢出列表 / 菜单宿主 / 接口 / Activity），
 * 任何一处漏改都表现为**点了没反应**——静态结构断言是「一次性抓出漏改点」的最低成本手段。
 */
class ReadMenuAiPurifyEntryTest {

    private fun composeComponents(): String =
        SourceFileProbe.sourceText("ui/book/read/ReadMenuComposeComponents.kt")

    private fun readMenu(): String = SourceFileProbe.sourceText("ui/book/read/ReadMenu.kt")

    private fun readBookActivity(): String = SourceFileProbe.sourceText("ui/book/read/ReadBookActivity.kt")

    @Test
    fun overflowList_hostsAiPurifyRowNextToReplaceRule() {
        val source = composeComponents()
        assertTrue("动作数据结构缺少 onAiPurifyClick 字段", source.contains("val onAiPurifyClick: () -> Unit"))
        assertTrue("溢出列表未接入 onAiPurifyClick", source.contains("onAiPurifyClick = actions.onAiPurifyClick"))
        val replaceIndex = source.indexOf("title = \"替换净化\"")
        val purifyIndex = source.indexOf("AI 净化选中文字")
        assertTrue("「AI 净化」应紧邻「替换净化」（替换净化旁入口）", purifyIndex > replaceIndex && replaceIndex >= 0)
    }

    @Test
    fun readMenu_wiresCallbackToActivityContract() {
        val source = readMenu()
        assertTrue(
            "阅读菜单未把回调接到 Activity 契约",
            source.contains("onAiPurifyClick = { callBack.purifySelection() }")
        )
        assertTrue("CallBack 接口缺少 purifySelection()", source.contains("fun purifySelection()"))
    }

    @Test
    fun activity_implementsBothEntriesThroughSinglePurifyPath() {
        val source = readBookActivity()
        assertTrue("Activity 未实现 purifySelection()", source.contains("override fun purifySelection()"))
        assertTrue("划词菜单未分发 menu_ai_purify", source.contains("R.id.menu_ai_purify -> {"))
        assertTrue("净化入口未落在 AiPurifyDialog", source.contains("AiPurifyDialog.create(text)"))
        assertTrue("未选中文字时应给出提示", source.contains("R.string.ai_purify_no_selection"))
    }
}