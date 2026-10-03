package io.legado.app.ui.main.bookshelf

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书架续读条**悬浮结构契约**回归测试。
 *
 * 演进：2026-10-01 缺陷⑤（被底栏遮挡 ⇒ 补避让）→ 2026-10-02 视觉迭代（悬空胶囊）→
 * **2026-10-02 二改**（用户原文：「续读条不能在一个父容器里面呢，就不能通过计算高度的方式紧贴底栏
 * 上部，中间哪怕你设置成透明色也比你现在的好看」）⇒ 由「Column 流式子项」改为 **Box overlay**。
 *
 * 断言的是 **结构即契约**：
 * ① 调用点必须是 `align(Alignment.BottomCenter)` 的 Box overlay（**不得回退为 Column 流式子项**）；
 * ② 底部留白必须取自「**底栏实际高度**」单源 `mainBottomBarActualHeight()`（= `main_bottom_bar_height`
 *    + `main_bottom_controls_bottom_padding` + 导航栏 inset）⇒ `padding(bottom = bottomBarInset)` **紧贴底栏上沿**
 *    （**不得**误用内容留白口径 `mainBottomBarContentPadding`，会多出 ~32dp 空档；也不得出现硬编码 bottom dp）；
 * ③ 配色/造型必须**跟随底栏**（`palette.bottomBar` / `palette.bottomBarText` + 底栏同款圆角 `main_bottom_bar_corner_radius`
 *    与左右内缩 `main_bottom_controls_horizontal_padding`，零硬编码色）；
 * ④ 列表/网格必须为悬浮条**预留高度**（`extraBottomReserve`），否则透明条会盖住最后一行。
 */
class BookshelfContinueBarInsetsContractTest {

    private val source: String by lazy {
        SourceFileProbe.sourceText("ui/main/bookshelf/BookshelfScreen.kt")
    }

    private fun body(signature: String): String {
        val start = source.indexOf(signature)
        assertTrue("未找到函数签名：$signature", start >= 0)
        val open = source.indexOf('{', start)
        var depth = 0
        var i = open
        while (i < source.length) {
            when (source[i]) {
                '{' -> depth++
                '}' -> {
                    depth--
                    if (depth == 0) return source.substring(open + 1, i)
                }
            }
            i++
        }
        throw AssertionError("函数体括号不匹配：$signature")
    }

    /** 续读条**调用点**窗口（函数定义在文件后部，故首次出现即调用点）——用于 overlay 结构断言 */
    private fun callSite(): String {
        val idx = source.indexOf("ContinueReadingBar(")
        assertTrue("未找到 ContinueReadingBar 调用点", idx >= 0)
        return source.substring(idx, minOf(source.length, idx + 260))
    }

    @Test
    fun continueBarIsBottomOverlayHuggingBottomBarWithTransparentBg() {
        val bar = body("private fun ContinueReadingBar(")
        val call = callSite()

        // ① 结构：必须是 Box overlay（align BottomCenter），不得回退为 Column 流式子项
        assertTrue(
            "续读条必须以 Box overlay + align(Alignment.BottomCenter) 悬浮定位（不得回退为 Column 流式子项）。" +
                "实得调用点片段：$call",
            "modifier = Modifier.align(Alignment.BottomCenter)" in call
        )
        // ② 紧贴底栏上沿：必须取「底栏实际高度」单源（用内容留白口径会多出 ~32dp 空档）
        assertTrue(
            "续读条底部留白必须取自「底栏实际高度」单源 mainBottomBarActualHeight()" +
                "（误用 mainBottomBarContentPadding() 会多出空档，用户 2026-10-02 报障）",
            "mainBottomBarActualHeight()" in bar
        )
        assertTrue(
            "续读条必须以 padding(bottom = bottomBarInset) 紧贴底栏上沿（不得出现硬编码 bottom dp）",
            "padding(bottom = bottomBarInset)" in bar
        )
        // ③ 配色/造型必须跟随底栏单源（磨砂玻璃同款）——用户第四轮：「跟底栏一样的配色样式方案」
        assertTrue(
            "续读条底色必须取主题底栏色 palette.bottomBar（跟随底栏配色方案）",
            "background(Color(palette.bottomBar)" in bar
        )
        assertTrue(
            "续读条图标/文字色必须取 palette.bottomBarText（跟随底栏配色方案）",
            "palette.bottomBarText" in bar
        )
        assertTrue(
            "续读条必须用底栏同款圆角 main_bottom_bar_corner_radius + 左右内缩 main_bottom_controls_horizontal_padding",
            "R.dimen.main_bottom_bar_corner_radius" in bar &&
                "R.dimen.main_bottom_controls_horizontal_padding" in bar
        )
        assertFalse(
            "禁止硬编码颜色（必须走主题 token）",
            Regex("Color\\(0x").containsMatchIn(bar)
        )
    }

    @Test
    fun bookshelfListsReserveHeightForFloatingContinueBar() {
        val hits = source.split("extraBottomReserve = continueBarReserve").size - 1
        assertTrue(
            "书架列表/网格（≥2 处调用）必须为悬浮续读条预留底部高度 extraBottomReserve，" +
                "否则透明条会盖住最后一行。命中=$hits",
            hits >= 2
        )
    }
}