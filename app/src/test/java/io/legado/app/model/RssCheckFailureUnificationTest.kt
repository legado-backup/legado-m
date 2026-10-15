package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅源侧「分组回填口径单源化」护栏（缺口2 续：订阅源侧补齐）。
 *
 * 收敛前：`CheckRssSourceService` 自带一套内联 `add/removeGroup`（14 处字面量）与自有归因 `when`，
 * 与体检侧 `QualityReportApplier.applyRssGroups` 是**两份"加组规则"**（靠"逐字一致"维系）；
 * `SourceCheckGroups` 的 `RSS_*` 常量只被体检路径消费。
 *
 * 收敛后唯一来源＝`QualityReportApplier`：`rssFailureGroupNames`（纯函数判定内核）、
 * `rssResultToDimStates`（`RssCheckResult` → 维度态唯一适配器）、`applyRssGroupsFromDims`（写库编排）。
 *
 * 断言口径说明：与书源侧同理，分组写库依赖 Android `TextUtils`（JVM 不可执行）⇒ 判定内核以**纯函数**
 * 断言；写库侧语义由既有 `QualityReportApplierTest` 的 report 路径覆盖。
 */
class RssCheckFailureUnificationTest {

    private fun namesOf(
        result: RssCheckResult,
        checkDomain: Boolean = false,
        failureKind: FailureKind = FailureKind.NONE,
        suspect: Boolean = false,
    ): List<String> = QualityReportApplier.rssFailureGroupNames(
        dims = QualityReportApplier.rssResultToDimStates(result),
        failureKind = failureKind,
        suspect = suspect,
        checkDomain = checkDomain,
    )

    // ---------- 适配器（旧内联语义对拍） ----------

    @Test
    fun adapter_ruleBlank_keepsDimensionUnchecked() {
        // 旧内联：`checkArticles && !ruleArticles.isNullOrBlank()` 才进分支 ⇒ 规则为空时该维**既不检也不打组**
        val result = RssCheckResult()
        assertEquals(emptyList<String>(), namesOf(result))
    }

    @Test
    fun adapter_articlesFailed_addsArticlesGroup() {
        val result = RssCheckResult(articlesChecked = true, articlesSuccess = false)
        assertEquals(listOf(SourceCheckGroups.RSS_ARTICLES_FAIL), namesOf(result))
    }

    @Test
    fun adapter_searchFailed_usesSharedSearchVocabulary() {
        // 旧内联：搜索失败 ⇒ `搜索失效`（与书源侧共用同一词条）
        val result = RssCheckResult(searchChecked = true, searchSuccess = false)
        assertEquals(listOf(SourceCheckGroups.SEARCH_FAIL), namesOf(result))
    }

    @Test
    fun adapter_sortFailed_addsSortGroup() {
        val result = RssCheckResult(sortChecked = true, sortSuccess = false)
        assertEquals(listOf(SourceCheckGroups.RSS_SORT_FAIL), namesOf(result))
    }

    @Test
    fun adapter_contentFailed_addsContentGroup() {
        val result = RssCheckResult(contentChecked = true, contentSuccess = false)
        assertEquals(listOf(SourceCheckGroups.RSS_CONTENT_FAIL), namesOf(result))
    }

    @Test
    fun adapter_allPass_addsNothing() {
        val result = RssCheckResult(
            domainReachable = true,
            articlesChecked = true, articlesSuccess = true,
            searchChecked = true, searchSuccess = true,
            sortChecked = true, sortSuccess = true,
            contentChecked = true, contentSuccess = true,
        )
        assertTrue(namesOf(result, checkDomain = true).isEmpty())
    }

    @Test
    fun adapter_allFourDimsFailed_addsFourGroupsInFixedOrder() {
        // 顺序即写入顺序（旧内联按 列表→搜索→分类→正文 逐段处理）
        val result = RssCheckResult(
            articlesChecked = true,
            searchChecked = true,
            sortChecked = true,
            contentChecked = true,
        )
        assertEquals(
            listOf(
                SourceCheckGroups.RSS_ARTICLES_FAIL,
                SourceCheckGroups.SEARCH_FAIL,
                SourceCheckGroups.RSS_SORT_FAIL,
                SourceCheckGroups.RSS_CONTENT_FAIL,
            ),
            namesOf(result)
        )
    }

    // ---------- 域名开关 ----------

    @Test
    fun domain_groupOnlyWhenCheckDomainEnabled() {
        val result = RssCheckResult(domainReachable = false)
        assertEquals(listOf(SourceCheckGroups.DOMAIN_FAIL), namesOf(result, checkDomain = true))
        assertTrue("域名校验关闭时不得因不可达打组", namesOf(result, checkDomain = false).isEmpty())
    }

    // ---------- 归因短路 / 存疑放行 ----------

    @Test
    fun failureKind_shortCircuitsDims() {
        val result = RssCheckResult(articlesChecked = true, contentChecked = true)
        assertEquals(
            "归因短路：只打超时组（旧内联 when 同语义）",
            listOf(SourceCheckGroups.CHECK_TIMEOUT),
            namesOf(result, checkDomain = true, failureKind = FailureKind.TIMEOUT)
        )
        assertEquals(
            listOf(SourceCheckGroups.SCRIPT_FAIL),
            namesOf(result, failureKind = FailureKind.SCRIPT)
        )
        assertEquals(
            listOf(SourceCheckGroups.SITE_FAIL),
            namesOf(result, failureKind = FailureKind.NETWORK)
        )
    }

    @Test
    fun suspectSource_isEmpty() {
        val result = RssCheckResult(articlesChecked = true, contentChecked = true)
        assertEquals(
            "存疑放行：不得写任何失效分组（防误伤）",
            emptyList<String>(),
            namesOf(result, checkDomain = true, suspect = true)
        )
    }

    // ---------- 与书源侧口径的差异必须显式锁住（防日后照搬书源口径） ----------

    @Test
    fun rssVocabularyDiffersFromBookVocabulary() {
        // 订阅源无「链接规则为空 / 目录」两类结论 ⇒ 其纯函数**不得**产出书源侧专属词条
        val dims = mapOf(
            QualityDim.SEARCH to DimState.NOT_APPLICABLE,
            QualityDim.DISCOVERY to DimState.NOT_APPLICABLE,
            QualityDim.CATEGORY to DimState.FAIL,
        )
        val names = QualityReportApplier.rssFailureGroupNames(
            dims = dims,
            failureKind = FailureKind.NONE,
            suspect = false,
            checkDomain = false,
        )
        assertTrue("订阅源不得产出「搜索链接规则为空」", names.none { it == SourceCheckGroups.SEARCH_URL_EMPTY })
        assertTrue("订阅源不得产出「搜索目录失效」", names.none { it == SourceCheckGroups.SEARCH_CATEGORY_FAIL })
        assertEquals(emptyList<String>(), names)
    }
}
