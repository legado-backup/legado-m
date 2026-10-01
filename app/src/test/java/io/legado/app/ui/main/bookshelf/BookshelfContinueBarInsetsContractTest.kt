package io.legado.app.ui.main.bookshelf

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书架续读条**底栏避让契约**回归测试（2026-10-01 缺陷⑤）。
 *
 * 背景：用户报障「书架左下角『继续阅读…』被底栏遮住，要不是底栏半透明都不知道有这提示」。
 * 根因：续读条渲染在 Lazy 列表**之外**（外层 Column 末项），而底栏避让此前只做在列表的
 * `contentPadding` 上 ⇒ 本条落在底栏覆盖区。修复 = 补 `Modifier.mainBottomBarPadding()`。
 *
 * 断言的是 **modifiers 顺序即契约**：
 * `background`（底色铺满含避让区）→ `mainBottomBarPadding`（内容上移到「底栏高 + 导航栏」之上）
 * → `clickable`（点击区随内容上移，底栏区域不可误触）。
 * 顺序被调换（例如把 padding 放到 clickable 之后或 background 之前）会重新破坏避让或点击热区。
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
    fun continueBarAppliesBottomBarInsetBetweenBackgroundAndClickable() {
        val bar = body("private fun ContinueReadingBar(")
        val bg = bar.indexOf(".background(Color(palette.row))")
        val inset = bar.indexOf(".mainBottomBarPadding()")
        val click = bar.indexOf(".clickable(onClick = onClick)")

        assertTrue("续读条必须补底栏避让留白 mainBottomBarPadding()（否则被底栏遮住）", inset >= 0)
        assertTrue("未找到 background(Color(palette.row))", bg >= 0)
        assertTrue("未找到 clickable(onClick = onClick)", click >= 0)

        assertTrue(
            "顺序契约：background → mainBottomBarPadding → clickable（底色铺满含避让区、内容与点击区上移）。" +
                "实得 bg=$bg inset=$inset click=$click",
            bg < inset && inset < click
        )
    }
}