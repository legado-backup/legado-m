package io.legado.app.ui.book.source.debug

import io.legado.app.constant.BookSourceType
import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.rule.SearchRule
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 调试示例生成单元测试（design AD-02 / tasks 3.1 / spec Requirement A-1）。
 *
 * 断言要点：
 * 1. **JS 单文件源规则字段全空**时，五档目标（搜索/发现/详情/目录/正文）**均有可用示例**；
 * 2. **声明优先**：已有声明式发现分类时，占位不覆盖它；
 * 3. **声明式源行为不变**：非 JS 源不引入额外占位示例（改造前后等价）。
 *
 * 测试对象为纯函数 `buildDebugExamples`，不触发 Android/Room。
 */
class BookSourceDebugExamplesTest {

    private fun jsSource(url: String = "https://site-a.example/") = BookSource(
        bookSourceUrl = url,
        bookSourceName = "js",
        bookSourceType = BookSourceType.video,
        mainJs = "var config = {bookSourceUrl:'$url'};",
    )

    private fun declarativeSource() = BookSource(
        bookSourceUrl = "https://site-b.example/",
        bookSourceName = "decl",
        bookSourceType = BookSourceType.default,
        ruleSearch = SearchRule(checkKeyWord = "总裁"),
    )

    @Test
    fun jsSourceWithEmptyRules_hasExampleForEveryTarget() {
        val examples = buildDebugExamples(jsSource(), kinds = emptyList())
        val targets = examples.map { it.target }.toSet()
        BookDebugTarget.entries.forEach { target ->
            assertTrue(
                "JS 源规则字段全空时，$target 档必须有可用示例（不得出现空示例）",
                target in targets,
            )
        }
        assertTrue("示例值不得为空串", examples.all { it.value.isNotBlank() })
    }

    @Test
    fun jsSourcePlaceholders_useSourceUrlAsValue() {
        val url = "https://site-a.example/"
        val examples = buildDebugExamples(jsSource(url), kinds = emptyList())
        val byTarget = examples.associateBy { it.target }
        assertEquals("详情占位应指向源地址", url, byTarget.getValue(BookDebugTarget.INFO).value)
        assertEquals("目录占位应指向源地址", url, byTarget.getValue(BookDebugTarget.TOC).value)
        assertEquals("正文占位应指向源地址", url, byTarget.getValue(BookDebugTarget.CONTENT).value)
    }

    @Test
    fun declaredKinds_winOverPlaceholder() {
        val examples = buildDebugExamples(
            jsSource(),
            kinds = listOf("真人剧" to "https://site-a.example/category/real-drama"),
        )
        val explore = examples.filter { it.target == BookDebugTarget.EXPLORE }
        assertEquals("已有声明式分类时不得再加占位发现示例", 1, explore.size)
        assertEquals("声明优先（值应为声明 URL）", "https://site-a.example/category/real-drama", explore[0].value)
        assertEquals("标签用声明标题", "真人剧", explore[0].label)
    }

    @Test
    fun declarativeSource_hasNoExtraPlaceholders() {
        val examples = buildDebugExamples(declarativeSource(), kinds = emptyList())
        val targets = examples.map { it.target }.toSet()
        assertEquals(
            "声明式源只应有搜索示例（行为与改造前一致）",
            setOf(BookDebugTarget.SEARCH),
            targets,
        )
        assertEquals(
            "搜索示例应为 checkKeyWord + 系统",
            listOf("总裁", "系统"),
            examples.map { it.value },
        )
    }

    @Test
    fun kindsWithBlankUrl_areSkipped() {
        val examples = buildDebugExamples(declarativeSource(), kinds = listOf("空分类" to ""))
        assertTrue(
            "URL 为空的分类不得产出示例",
            examples.none { it.target == BookDebugTarget.EXPLORE },
        )
    }
}