package io.legado.app.ui.book.read.config

import io.legado.app.help.config.AdvancedTitleConfig
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-56：**本书**高级标题拆分规则的**写入入口**接线守护。
 *
 * 缺陷背景：`AdvancedTitleConfig.setBookRule(book, rule)` 全仓**零调用**，而读侧
 * `bookRule(book)` / `effectiveRule(book)`（经 `split(title, book)` 与 Lottie 标题渲染）一直在活路径
 * ⇒ **单书规则只有读、没有写**：某个书名/章节前缀与全局拆分规则不适配时，用户在任何界面都**没有入口**
 * （属「半接线」用户可感缺口）。本类把「弹窗 ↔ 入口 ↔ 刷新通道 ↔ 字符串」四处接线固化。
 *
 * 为什么同时含行为断言：拆分规则本身是纯函数（`split(title, rule)` 不触 appCtx）⇒ 用带期望值的
 * 断言锁住语义（分隔符/正则/无命中三分支），避免"入口接上了但规则算错"。
 */
class AdvancedTitleBookRuleWiringTest {

    private fun code(rel: String): String = SourceFileProbe.sourceTextByPath(rel)

    @Test
    fun `split rule semantics stay correct`() {
        // 行为断言：分隔符模式
        val byDelimiter = AdvancedTitleConfig.split(
            "第1章 测试",
            AdvancedTitleConfig.SplitRule(
                mode = AdvancedTitleConfig.SPLIT_DELIMITER,
                delimiter = " "
            )
        )
        assertEquals("第1章", byDelimiter.s1)
        assertEquals("测试", byDelimiter.s2)

        // 行为断言：正则模式（默认正则：章节前缀 + 空格 + 标题）
        val byRegex = AdvancedTitleConfig.split(
            "第1章 测试",
            AdvancedTitleConfig.SplitRule(
                mode = AdvancedTitleConfig.SPLIT_REGEX,
                regex = AdvancedTitleConfig.DEFAULT_REGEX
            )
        )
        assertEquals("第1章", byRegex.s1)
        assertEquals("测试", byRegex.s2)

        // 行为断言：两种模式都命中不了时，s1 为空、s2 回落全标题（不抛异常、不丢标题）
        val noMatch = AdvancedTitleConfig.split(
            "没有分隔符的标题",
            AdvancedTitleConfig.SplitRule(
                mode = AdvancedTitleConfig.SPLIT_DELIMITER,
                delimiter = "-"
            )
        )
        assertEquals("", noMatch.s1)
        assertEquals("没有分隔符的标题", noMatch.s2)
    }

    @Test
    fun `book rule dialog persists through the single write entry`() {
        val src = code("src/main/java/io/legado/app/ui/book/read/config/AdvancedTitleBookRuleDialog.kt")
        assertTrue("须为 Compose 弹窗（与高级标题编辑同族）", src.contains("class AdvancedTitleBookRuleDialog : ComposeDialogFragment()"))
        assertTrue("必须走唯一写入口 setBookRule", src.contains("AdvancedTitleConfig.setBookRule(book ?: return, rule)"))
        assertTrue("必须取当前书籍（规则是 per-book）", src.contains("ReadBook.book"))
        assertTrue("保存/清除后必须发读页刷新事件", src.contains("postEvent(EventBus.UP_CONFIG, arrayListOf(5, 8))"))
        assertTrue("标题须用新登记字符串", src.contains("R.string.advanced_title_book_rule"))
        assertTrue("须提供「恢复跟随全局」（rule = null ⇒ 回落到全局规则）", src.contains("R.string.advanced_title_book_rule_reset"))
    }

    @Test
    fun `entry only appears in advanced title mode and opens the dialog`() {
        val tip = code("src/main/java/io/legado/app/ui/book/read/config/TipConfigDialog.kt")
        assertTrue("内容体须新增本书规则入口回调", tip.contains("onShowBookTitleRule: () -> Unit,"))
        assertTrue(
            "入口须仅在「高级标题」模式下出现（其余模式不消费拆分规则）",
            tip.contains("if (titleMode == AdvancedTitleConfig.TITLE_MODE_ADVANCED)")
        )
        assertTrue("入口须渲染本书规则行", tip.contains("R.string.advanced_title_book_rule"))
        assertTrue("入口点击须回调宿主", tip.contains("onClick = onShowBookTitleRule"))

        val padding = code("src/main/java/io/legado/app/ui/book/read/config/PaddingConfigDialog.kt")
        assertTrue(
            "宿主须把该回调透传给内容体",
            padding.contains("onShowBookTitleRule = onShowBookTitleRule,")
        )
        assertTrue(
            "宿主须实际打开本书规则弹窗（否则入口点了没反应）",
            padding.contains("AdvancedTitleBookRuleDialog().show(")
        )
    }

    @Test
    fun `new strings exist in both default and chinese resources`() {
        listOf(
            "src/main/res/values/strings.xml",
            "src/main/res/values-zh/strings.xml"
        ).forEach { rel ->
            val res = code(rel)
            listOf(
                "advanced_title_book_rule",
                "advanced_title_book_rule_hint",
                "advanced_title_book_rule_reset"
            ).forEach { name ->
                assertTrue("$rel 缺少 <string name=\"$name\">", res.contains("name=\"$name\""))
            }
        }
    }
}
