package io.legado.app.ui.widget

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：`PopupAction`（`item_text` 宿主）的 View → Compose 换装。
 *
 * 换装前：`PopupWindow.contentView = popup_action.xml`（`FlexboxLayoutManager` + `RecyclerView`
 * + inner `RecyclerAdapter`，条目 inflate `item_text.xml`）。
 * 换装后：`contentView = ComposeView`，内容为 `FlowRow` + `Text`（同底色/同圆角/同内边距/同 14sp 单行）。
 *
 * 本测试锁住两条：①死布局不得复活 ②宿主对外契约（`setItems` / `onActionClick`）与
 * `ReadBookActivity` 的既有接线（`showAtLocation` / `dismiss`）不得被改坏。
 */
class PopupActionComposeOnlyTest {

    private fun layout(name: String): File = File(SourceFileProbe.layoutDir(), name)

    @Test
    fun deadLayoutsAreGone() {
        listOf("item_text.xml", "popup_action.xml").forEach { name ->
            assertFalse("死布局应已退役：$name", layout(name).isFile)
        }
    }

    @Test
    fun popupActionIsComposeNow() {
        val src = SourceFileProbe.sourceText("ui/widget/PopupAction.kt")
        assertFalse("不得再 inflate 旧布局", src.contains("ItemTextBinding") || src.contains("PopupActionBinding"))
        assertFalse("不得再继承 RecyclerAdapter", src.contains("RecyclerAdapter<"))
        assertTrue("内容容器应为 Compose FlowRow（等价原 FlexboxLayoutManager wrap 行为）", src.contains("FlowRow("))
        assertTrue("底色须走主题面 token（cardColor）", src.contains("themeUiPalette.cardColor"))
        assertTrue("文字色须走主题 token（primaryText）", src.contains("palette.primaryText"))
        assertTrue("圆角须走形状单源 AppShapes.Chip（等价 @dimen/corner_small）", src.contains("AppShapes.Chip"))
    }

    @Test
    fun externalContractUnchanged() {
        val src = SourceFileProbe.sourceText("ui/widget/PopupAction.kt")
        assertTrue("对外仍须暴露 setItems", src.contains("fun setItems(items: List<SelectItem<String>>)"))
        assertTrue("对外仍须暴露 onActionClick", src.contains("var onActionClick"))
        assertTrue("弹窗仍须为可聚焦、外部不可点（语义不变）", src.contains("isFocusable = true"))
        assertTrue(src.contains("isOutsideTouchable = false"))

        val host = SourceFileProbe.sourceText("ui/book/read/ReadBookActivity.kt")
        assertTrue("宿主仍以 setItems 投喂条目", host.contains("popupAction.setItems("))
        assertTrue("宿主仍消费 onActionClick", host.contains("popupAction.onActionClick ="))
        assertTrue("宿主展示/关闭调用点不变", host.contains("popupAction.showAtLocation(") && host.contains("popupAction.dismiss()"))
    }
}