package io.legado.app.ui.main.bookshelf

import io.legado.app.testkit.SourceFileProbe
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
 * ② 底部留白必须由避让单源 `mainBottomBarContentPadding(...).calculateBottomPadding()` 算出后
 *    `padding(bottom = bottomBarInset)` ⇒ **紧贴底栏上沿**（不得出现裸的硬编码 bottom dp）；
 * ③ 背景**透明**（不得回退为整宽不透明/半透明色块）；
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
        // ② 紧贴底栏上沿：底部留白取自避让单源（底栏高 + 导航栏）
        assertTrue(
            "续读条底部留白必须取自避让单源 mainBottomBarContentPadding(...)",
            "mainBottomBarContentPadding(" in bar
        )
        assertTrue(
            "续读条必须用 calculateBottomPadding() 算出底栏高度并以 padding(bottom = bottomBarInset) 紧贴底栏上沿",
            "calculateBottomPadding()" in bar && "padding(bottom = bottomBarInset)" in bar
        )
        // ③ 背景透明（不做色块）——用户明确「哪怕设置成透明色也比现在的好看」
        assertTrue(
            "续读条必须为透明背景（不得回退为整宽不透明/半透明色块）",
            ".background(" !in bar
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