package io.legado.app.ui.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-87：主题包「回复栏跟随圆角」幽灵设置的**退役守护**（第一部分 UI 入口 + 第二部分存储链）。
 *
 * 缺陷背景：该设置**无可感效果** —— 唯一功能性消费点 `UiCorner.replyRadius()` 全仓零调用，
 * 且仓内不存在任何「回复栏 / reply bar」视图或布局；**上游 Archive 同样零消费**
 * （`docs/analysis/archive-src` 中该符号仅出现在定义处）⇒ 摆一个点了没反应的开关属误导性 UI。
 *
 * 本用例锁定四件事：
 * ① 弹窗不再渲染该行（含不再读写 `pendingUiCornerReplyFollow`）；
 * ② `ThemeManageActivity` 的 pending 态与 helper 一并退役（存储链不留半截）；
 * ③ 兄弟行「搜索框跟随圆角」（其消费点 `UiCorner.searchRadius` **活跃**）不受影响，防误删；
 * ④ 存储链（`PreferKey` / `ThemeConfig` 字段 / `replyRadius`）与 `ui_corner_reply_follow` 字符串
 *    已整体退役（键名入 `BackupConfig.ignorePrefKeys`，防旧备份写回）。
 *
 * 键声明侧由 `constant/RetiredPreferKeyTest` 与 `help/storage/BackupRestoreParityTest` 分别守护。
 */
class ThemePackageReplyFollowToggleRetiredTest {

    private val dialog by lazy { SourceFileProbe.sourceText("ui/config/ThemePackageEditDialog.kt") }
    private val themeManage by lazy {
        SourceFileProbe.sourceText("ui/config/ThemeManageActivity.kt")
    }

    @Test
    fun `回复栏跟随圆角开关行已退役`() {
        assertEquals(
            "弹窗不得再渲染「回复栏跟随圆角」行", false,
            dialog.contains("R.string.ui_corner_reply_follow")
        )
        assertEquals(
            "弹窗不得再读写 pendingUiCornerReplyFollow", false,
            dialog.contains("pendingUiCornerReplyFollow")
        )
    }

    @Test
    fun `幽灵设置存储链已整体退役`() {
        assertEquals(
            "ThemeManageActivity 不得再保留 pendingUiCornerReplyFollow 编辑态", false,
            themeManage.contains("pendingUiCornerReplyFollow")
        )
        assertEquals(
            "ThemeManageActivity 不得再保留 themeUiCornerReplyFollow helper", false,
            themeManage.contains("themeUiCornerReplyFollow")
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
