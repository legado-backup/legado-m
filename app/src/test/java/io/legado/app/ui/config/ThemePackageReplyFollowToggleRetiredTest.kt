package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-87（第一部分）：主题包编辑弹窗的「回复栏跟随圆角」开关**退役**守护。
 *
 * 缺陷背景：该设置**无可感效果** —— 唯一功能性消费点 `UiCorner.replyRadius()` 全仓零调用，
 * 且仓内不存在任何「回复栏 / reply bar」视图或布局；**上游 Archive 同样零消费**
 * （`docs/analysis/archive-src` 中该符号仅出现在定义处）⇒ 摆一个点了没反应的开关属误导性 UI。
 *
 * 本用例锁定三件事：
 * ① 弹窗不再渲染该行（含不再读写 `pendingUiCornerReplyFollow`）；
 * ② 兄弟行「搜索框跟随圆角」（其消费点 `UiCorner.searchRadius → TopBarSearchStyle` **活跃**）不受影响，防误删；
 * ③ 存储链（`PreferKey` / `ThemeConfig` 字段 / `UiCorner.replyRadius`）与本字符串本批**刻意保留**，
 *    随**主题 schema 批次**一并清理（中途不拆存储链，避免改坏主题包兼容性）。
 */
class ThemePackageReplyFollowToggleRetiredTest {

    private val dialog by lazy { SourceFileProbe.sourceText("ui/config/ThemePackageEditDialog.kt") }

    @Test
    fun `回复栏跟随圆角开关行已退役`() {
        assertEquals(
            "弹窗不得再渲染「回复栏跟随圆角」行", false,
            dialog.contains("R.string.ui_corner_reply_follow")
        )
        assertEquals(
            "不得再翻转 pendingUiCornerReplyFollow", false,
            dialog.contains("host.pendingUiCornerReplyFollow = !host.pendingUiCornerReplyFollow")
        )
    }

    @Test
    fun `兄弟开关搜索框跟随圆角必须保留`() {
        assertEquals(
            "兄弟行「搜索框跟随圆角」必须仍在渲染", true,
            dialog.contains("R.string.ui_corner_search_follow")
        )
        assertEquals(
            "其翻转逻辑须仍在", true,
            dialog.contains("host.pendingUiCornerSearchFollow = !host.pendingUiCornerSearchFollow")
        )
    }
}
