package io.legado.app.ui.main.bookshelf

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书架续读条**悬空半透明胶囊契约**回归测试（2026-10-01 缺陷⑤ → 2026-10-02 视觉迭代）。
 *
 * 背景：用户先报障「书架左下角『继续阅读…』被底栏遮住」⇒ 补 `Modifier.mainBottomBarPadding()`；
 * 后反馈「样式丑、偏大、太高，想要悬空半透明小条」⇒ 修饰符链整体重排（悬空/半透明/胶囊/瘦身）。
 *
 * 断言的是 **modifiers 顺序即契约**：
 * `mainBottomBarPadding(extra = 8.dp)`（底栏避让 + 悬空间隙，防缺陷⑤回归）→ `padding(start/end/top)`（悬空留白）
 * → `clip(AppShapes.Capsule)`（胶囊造型）→ `background(row.copy(alpha = 0.72f))`（半透明底色）
 * → `clickable`（点击区随内容上移，底栏区域不可误触）→ `padding`（内容内边距）。
 * 顺序被调换（例如 padding 放到 clickable 之后、或此前 background 先于避让铺满整宽）都会破坏悬空/造型/热区。
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

    @Test
    fun continueBarIsFloatingTranslucentCapsuleAboveBottomBar() {
        val bar = body("private fun ContinueReadingBar(")
        val inset = bar.indexOf(".mainBottomBarPadding(extra = 8.dp)")
        val margin = bar.indexOf(".padding(start = 12.dp, end = 12.dp, top = 6.dp)")
        val clip = bar.indexOf(".clip(AppShapes.Capsule)")
        val bg = bar.indexOf(".background(Color(palette.row).copy(alpha = 0.72f))")
        val click = bar.indexOf(".clickable(onClick = onClick)")

        assertTrue(
            "续读条必须补底栏避让留白 mainBottomBarPadding(extra = 8.dp)（否则被底栏遮住 / 无悬空间隙）",
            inset >= 0
        )
        assertTrue(
            "未找到悬空留白 padding(start = 12.dp, end = 12.dp, top = 6.dp)",
            margin >= 0
        )
        assertTrue("未找到胶囊裁剪 clip(AppShapes.Capsule)", clip >= 0)
        assertTrue(
            "未找到半透明底色 background(Color(palette.row).copy(alpha = 0.72f))",
            bg >= 0
        )
        assertTrue("未找到 clickable(onClick = onClick)", click >= 0)

        assertTrue(
            "顺序契约：mainBottomBarPadding → 悬空 padding → clip → background → clickable。" +
                "实得 inset=$inset margin=$margin clip=$clip bg=$bg click=$click",
            inset < margin && margin < clip && clip < bg && bg < click
        )

        // 旧「整宽不透明」写法必须消失（本文档缺陷根因：background 先于避让 padding 铺满整宽）
        assertTrue(
            "旧整宽不透明底色 background(Color(palette.row)) 残留（应改为悬空裁剪 + 半透明）",
            bar.indexOf(".background(Color(palette.row))") < 0
        )
    }
}