package io.legado.app.model

import io.legado.app.data.entities.BookSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 分组名词表**单源**（`SourceCheckGroups`）护栏 —— 缺口6（扩大测试基准揪出的"靠测试锁住的重复"）。
 *
 * 关键不变量：①字面量与历史口径**逐字不变**（否则下游分组筛选/自动清除全部错位）；
 * ②`BookSource.getInvalidGroupNames()` 的隐式口径（"失效"子串 / "校验超时"全等）与表内命名保持一致
 * —— **新增分组名时须确认是否该被下一轮校验清除**。
 */
class SourceCheckGroupsTest {

    @Test
    fun bookDimensionGroups_keepHistoricalWording() {
        assertEquals("域名失效", SourceCheckGroups.DOMAIN_FAIL)
        assertEquals("搜索链接规则为空", SourceCheckGroups.SEARCH_URL_EMPTY)
        assertEquals("搜索失效", SourceCheckGroups.SEARCH_FAIL)
        assertEquals("搜索目录失效", SourceCheckGroups.SEARCH_CATEGORY_FAIL)
        assertEquals("搜索正文失效", SourceCheckGroups.SEARCH_CONTENT_FAIL)
        assertEquals("发现规则为空", SourceCheckGroups.DISCOVERY_RULE_EMPTY)
        assertEquals("发现失效", SourceCheckGroups.DISCOVERY_FAIL)
        assertEquals("发现目录失效", SourceCheckGroups.DISCOVERY_CATEGORY_FAIL)
        assertEquals("发现正文失效", SourceCheckGroups.DISCOVERY_CONTENT_FAIL)
    }

    @Test
    fun failureAttributionGroups_keepHistoricalWording() {
        assertEquals("校验超时", SourceCheckGroups.CHECK_TIMEOUT)
        assertEquals("js失效", SourceCheckGroups.SCRIPT_FAIL)
        assertEquals("网站失效", SourceCheckGroups.SITE_FAIL)
    }

    @Test
    fun rssGroups_keepHistoricalWording() {
        assertEquals("列表失效", SourceCheckGroups.RSS_ARTICLES_FAIL)
        assertEquals("分类失效", SourceCheckGroups.RSS_SORT_FAIL)
        assertEquals("正文失效", SourceCheckGroups.RSS_CONTENT_FAIL)
        assertEquals("重复源", SourceCheckGroups.RSS_DUPLICATE)
    }

    @Test
    fun duplicateMarker_isNotInAutoCleanupSetByDesign() {
        // 自动清除集判据＝`"失效" in group || group == "校验超时"`（RssSource.getInvalidGroupNames，
        // 私有实现，JVM 不可直调）⇒ 用同一判据在常量上断言。两条都不满足 ⇒ 「重复源」**不会**被
        // removeInvalidGroups() 自动清 ⇒ 必须由 CheckRssSourceService 每轮显式清一次
        // （若日后把它改成"重复失效"，反而会推翻"去重标记不是失败结论"的语义）
        assertFalse(
            "去重标记不得落入自动清除判据（否则每轮会被清掉，去重结论丢失）",
            SourceCheckGroups.RSS_DUPLICATE.contains("失效")
        )
        assertFalse(
            "去重标记不得等于「校验超时」",
            SourceCheckGroups.RSS_DUPLICATE == SourceCheckGroups.CHECK_TIMEOUT
        )
    }

    @Test
    fun invalidGroupCleanup_matchesVocabularyConvention() {
        val source = BookSource(
            bookSourceName = "t",
            bookSourceUrl = "http://example.com",
            bookSourceGroup = "域名失效,自建分组,校验超时",
        )
        val invalid = source.getInvalidGroupNames()
        assertTrue("含「失效」的分组应被判定为待清除", invalid.contains(SourceCheckGroups.DOMAIN_FAIL))
        assertTrue("「校验超时」全等亦属待清除", invalid.contains(SourceCheckGroups.CHECK_TIMEOUT))
        assertFalse("用户自建分组不得被清除", invalid.contains("自建分组"))
    }

    @Test
    fun newGroupNaming_mustContainFailSuffixToBeCleanable() {
        // 口径说明（防未来加组时踩坑）：只有**含「失效」**的分组会被 removeInvalidGroups 清理；
        // 因此"发现目录失效/发现正文失效"等维度组天然可清，"存疑跳过"类**故意不属**该集合（不应被清理）
        assertTrue(SourceCheckGroups.DISCOVERY_CATEGORY_FAIL.contains("失效"))
        assertTrue(SourceCheckGroups.DISCOVERY_CONTENT_FAIL.contains("失效"))
        assertFalse("存疑跳过类分组不应落入自动清除集合", "存疑跳过".contains("失效"))
    }
}
