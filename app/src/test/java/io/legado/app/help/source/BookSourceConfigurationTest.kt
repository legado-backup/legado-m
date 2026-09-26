package io.legado.app.help.source

import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.rule.BookInfoRule
import io.legado.app.data.entities.rule.ContentRule
import io.legado.app.data.entities.rule.ReviewRule
import io.legado.app.data.entities.rule.SearchRule
import io.legado.app.data.entities.rule.TocRule
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.3.1（J10 硬阻断口径）：全空书源判定 [isEmptyConfiguration]
 *
 * 判据要点：**只判配置全空**（缺某个入口 / 联网失败不算无效）；显示类开关（canReName/imageStyle）
 * 不算抓取配置，但 `eventListener`/`customButton` 说明源有自定义行为 ⇒ 不算全空。
 */
class BookSourceConfigurationTest {

    private fun source(configure: BookSource.() -> Unit = {}): BookSource =
        BookSource(bookSourceName = "probe", bookSourceUrl = "l2probe://src").apply(configure)

    @Test
    fun blankSourceIsEmptyConfiguration() {
        assertTrue(source().isEmptyConfiguration())
    }

    @Test
    fun anyEntryFieldMakesItNonEmpty() {
        assertFalse(source { searchUrl = "https://a/s?q={kw}" }.isEmptyConfiguration())
        assertFalse(source { exploreUrl = "https://a/x" }.isEmptyConfiguration())
        assertFalse(source { jsLib = "function a(){}" }.isEmptyConfiguration())
        assertFalse(source { loginUrl = "https://a/login" }.isEmptyConfiguration())
        assertFalse(source { bookUrlPattern = "https://a/book/\\d+" }.isEmptyConfiguration())
        assertFalse(source { coverDecodeJs = "java.base64Decode(x)" }.isEmptyConfiguration())
        assertFalse(source { header = "{'UA':'x'}" }.isEmptyConfiguration())
        assertFalse(source { exploreScreen = "[]" }.isEmptyConfiguration())
    }

    @Test
    fun listRuleFieldsMakeItNonEmpty() {
        assertFalse(source { ruleSearch = SearchRule(bookList = "class.book") }.isEmptyConfiguration())
        assertFalse(source { ruleExplore = io.legado.app.data.entities.rule.ExploreRule(bookList = "class.book") }.isEmptyConfiguration())
    }

    @Test
    fun searchKeywordAloneMakesItNonEmpty() {
        assertFalse(source { ruleSearch = SearchRule(checkKeyWord = "key") }.isEmptyConfiguration())
    }

    @Test
    fun infoTocContentReviewRulesAreCovered() {
        assertFalse(source { ruleBookInfo = BookInfoRule(name = "h1") }.isEmptyConfiguration())
        assertFalse(source { ruleBookInfo = BookInfoRule(downloadUrls = "@js:[]") }.isEmptyConfiguration())
        assertFalse(source { ruleToc = TocRule(chapterList = "class.list") }.isEmptyConfiguration())
        assertFalse(source { ruleToc = TocRule(preUpdateJs = "java.log(1)") }.isEmptyConfiguration())
        assertFalse(source { ruleContent = ContentRule(content = "class.content") }.isEmptyConfiguration())
        assertFalse(source { ruleContent = ContentRule(imageDecode = "@js:x") }.isEmptyConfiguration())
        assertFalse(source { ruleReview = ReviewRule(reviewUrl = "https://a/r") }.isEmptyConfiguration())
    }

    @Test
    fun behaviorSwitchesCountAsConfigured() {
        assertFalse(source { eventListener = true }.isEmptyConfiguration())
        assertFalse(source { customButton = true }.isEmptyConfiguration())
    }

    @Test
    fun blankFieldsInsideRulesDoNotMakeItNonEmpty() {
        // 规则对象存在但字段全空 ⇒ 仍视为空配置（只判「是否真的有配置」）
        assertTrue(source { ruleSearch = SearchRule(bookList = "  ") }.isEmptyConfiguration())
        assertTrue(source { ruleContent = ContentRule(content = null) }.isEmptyConfiguration())
    }

    @Test
    fun fieldCoverageGuard() {
        val code = SourceFileProbe.sourceText("help/source/BookSourceConfiguration.kt")
        // 入口字段组（新增入口字段时必须同步进该组，否则空壳源会漏判）
        assertTrue(
            code.contains("searchUrl, exploreUrl, jsLib, loginUrl, loginUi, loginCheckJs,")
        )
        assertTrue(code.contains("bookUrlPattern, coverDecodeJs, header, exploreScreen,"))
        // 五类规则必须都被纳入判定
        assertTrue(code.contains("ruleSearch.emptyListRule()"))
        assertTrue(code.contains("ruleExplore.emptyListRule()"))
        assertTrue(code.contains("ruleBookInfo?.let"))
        assertTrue(code.contains("ruleToc?.let"))
        assertTrue(code.contains("ruleContent?.let"))
        assertTrue(code.contains("ruleReview?.let"))
    }
}