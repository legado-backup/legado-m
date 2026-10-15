package io.legado.app.model

import com.script.ScriptException
import io.legado.app.exception.TocEmptyException
import kotlinx.coroutines.TimeoutCancellationException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

/**
 * 失败归因 + 分组回填的**单源化**护栏（缺口2 收敛第一步）。
 *
 * 收敛前：分组名词表、归因分类器、分组回填编排各有 2 份（服务侧内联 / 体检侧 `QualityReportApplier`），
 * 靠"逐字一致（单测锁定）"维系。现在唯一来源＝`QualityReportApplier`（`failureKindOf` /
 * `failureKindGroup` / `failureGroupNames` / `applyBookGroupsFromDims`），服务侧与体检侧同调。
 *
 * 断言口径说明：编排判定用**纯函数 `failureGroupNames`**（无副作用）断言；`applyBookGroupsFromDims`
 * 只负责把清单逐个 `addGroup`（写库侧语义由既有 `QualityReportApplierTest` 的 report 路径覆盖）。
 */
class SourceCheckFailureUnificationTest {

    private fun timeoutInstance(): Throwable = kotlinx.coroutines.runBlocking {
        try {
            kotlinx.coroutines.withTimeout(1) { kotlinx.coroutines.delay(80) }
            error("unreachable")
        } catch (t: TimeoutCancellationException) {
            t
        }
    }

    @Test
    fun failureKindOf_classifiesByExceptionType() {
        assertEquals(FailureKind.TIMEOUT, QualityReportApplier.failureKindOf(timeoutInstance()))
        assertEquals(FailureKind.SCRIPT, QualityReportApplier.failureKindOf(ScriptException("s")))
        assertEquals(
            FailureKind.SCRIPT,
            QualityReportApplier.failureKindOf(org.mozilla.javascript.WrappedException(RuntimeException("inner")))
        )
        assertEquals(FailureKind.NETWORK, QualityReportApplier.failureKindOf(IOException("reset")))
        // 业务异常（引擎侧已给结论）⇒ NONE，不得再打"网站失效"
        assertEquals(FailureKind.NONE, QualityReportApplier.failureKindOf(TocEmptyException("目录为空")))
    }

    @Test
    fun failureKindGroup_mapsToSingleSourceVocabulary() {
        assertEquals(SourceCheckGroups.CHECK_TIMEOUT, QualityReportApplier.failureKindGroup(FailureKind.TIMEOUT))
        assertEquals(SourceCheckGroups.SCRIPT_FAIL, QualityReportApplier.failureKindGroup(FailureKind.SCRIPT))
        assertEquals(SourceCheckGroups.SITE_FAIL, QualityReportApplier.failureKindGroup(FailureKind.NETWORK))
        assertNull(QualityReportApplier.failureKindGroup(FailureKind.NONE))
    }

    @Test
    fun groupNames_byDims_respectDimensionStates() {
        val names = QualityReportApplier.failureGroupNames(
            dims = mapOf(
                QualityDim.SEARCH to DimState.FAIL,
                QualityDim.DISCOVERY to DimState.FAIL,
                QualityDim.CATEGORY to DimState.FAIL,
                QualityDim.CONTENT to DimState.FAIL,
                QualityDim.INFO to DimState.PASS,
                QualityDim.DOMAIN to DimState.FAIL,
            ),
            failureKind = FailureKind.NONE,
            suspect = false,
            checkDomain = false,
        )
        assertEquals(
            listOf(
                SourceCheckGroups.SEARCH_FAIL,
                SourceCheckGroups.DISCOVERY_FAIL,
                SourceCheckGroups.SEARCH_CATEGORY_FAIL,
                SourceCheckGroups.SEARCH_CONTENT_FAIL,
            ),
            names
        )
        assertTrue("域名开关关闭时不得打域名失效", SourceCheckGroups.DOMAIN_FAIL !in names)
    }

    @Test
    fun groupNames_domainFail_onlyWhenCheckDomainEnabled() {
        val names = QualityReportApplier.failureGroupNames(
            dims = mapOf(QualityDim.DOMAIN to DimState.FAIL, QualityDim.SEARCH to DimState.PASS),
            failureKind = FailureKind.NONE,
            suspect = false,
            checkDomain = true,
        )
        assertEquals(listOf(SourceCheckGroups.DOMAIN_FAIL), names)
    }

    @Test
    fun groupNames_ruleEmptyDim_takesRuleEmptyGroup() {
        val names = QualityReportApplier.failureGroupNames(
            dims = mapOf(
                QualityDim.SEARCH to DimState.NOT_APPLICABLE,
                QualityDim.DISCOVERY to DimState.NOT_APPLICABLE,
            ),
            failureKind = FailureKind.NONE,
            suspect = false,
            checkDomain = false,
        )
        assertEquals(
            listOf(SourceCheckGroups.SEARCH_URL_EMPTY, SourceCheckGroups.DISCOVERY_RULE_EMPTY),
            names
        )
    }

    @Test
    fun groupNames_failureKind_shortCircuitsDims() {
        val names = QualityReportApplier.failureGroupNames(
            dims = mapOf(QualityDim.SEARCH to DimState.FAIL, QualityDim.CONTENT to DimState.FAIL),
            failureKind = FailureKind.TIMEOUT,
            suspect = false,
            checkDomain = true,
        )
        assertEquals("归因短路：只打超时组，不再按维度加组", listOf(SourceCheckGroups.CHECK_TIMEOUT), names)
    }

    @Test
    fun groupNames_suspectSource_isEmpty() {
        val names = QualityReportApplier.failureGroupNames(
            dims = mapOf(QualityDim.SEARCH to DimState.FAIL, QualityDim.CONTENT to DimState.FAIL),
            failureKind = FailureKind.NONE,
            suspect = true,
            checkDomain = true,
        )
        assertEquals("存疑放行：不得写任何失效分组（防误伤）", emptyList<String>(), names)
    }

    @Test
    fun groupNames_notCheckedDim_addsNothing() {
        val names = QualityReportApplier.failureGroupNames(
            dims = mapOf(QualityDim.SEARCH to DimState.NOT_CHECKED, QualityDim.DISCOVERY to null),
            failureKind = FailureKind.NONE,
            suspect = false,
            checkDomain = false,
        )
        assertEquals(emptyList<String>(), names)
    }

    // ---------- 旧服务结果 → 维度态适配器（缺口2 第二步的内核；断言口径＝旧内联语义） ----------

    private fun namesOf(result: BookCheckResult, checkDomain: Boolean = false): List<String> =
        QualityReportApplier.failureGroupNames(
            dims = QualityReportApplier.bookResultToDimStates(result),
            failureKind = FailureKind.NONE,
            suspect = false,
            checkDomain = checkDomain,
        )

    @Test
    fun adapter_searchFailed_givesNoCatalogConclusion() {
        // 旧内联：搜索失败时只打「搜索失效」，**不判**目录/正文（否则会同时出现 搜索失效+搜索目录失效）
        val result = BookCheckResult(searchChecked = true, searchSuccess = false)
        assertEquals(listOf(SourceCheckGroups.SEARCH_FAIL), namesOf(result))
    }

    @Test
    fun adapter_searchSuccess_judgesCatalogAndContent() {
        val result = BookCheckResult(
            searchChecked = true,
            searchSuccess = true,
            searchCategorySuccess = false,
            searchContentSuccess = true,
        )
        assertEquals(listOf(SourceCheckGroups.SEARCH_CATEGORY_FAIL), namesOf(result))
    }

    @Test
    fun adapter_discoverySourced_usesDiscoveryDimNames() {
        val result = BookCheckResult(
            discoveryChecked = true,
            discoverySuccess = true,
            discoveryCategorySuccess = false,
            discoveryContentSuccess = true,
        )
        assertEquals(listOf(SourceCheckGroups.DISCOVERY_CATEGORY_FAIL), namesOf(result))
    }

    @Test
    fun adapter_discoveryFailed_doesNotEmitDiscoveryCatalogGroups() {
        val result = BookCheckResult(discoveryChecked = true, discoverySuccess = false)
        assertEquals(listOf(SourceCheckGroups.DISCOVERY_FAIL), namesOf(result))
    }

    @Test
    fun adapter_ruleEmpty_takesRuleEmptyGroups() {
        val result = BookCheckResult(
            searchChecked = true,
            searchUrlEmpty = true,
            discoveryChecked = true,
            discoveryRuleEmpty = true,
        )
        assertEquals(
            listOf(SourceCheckGroups.SEARCH_URL_EMPTY, SourceCheckGroups.DISCOVERY_RULE_EMPTY),
            namesOf(result)
        )
    }

    @Test
    fun adapter_domainReachable_noDomainGroupEvenWhenChecked() {
        // 域名可达 ⇒ 不打「域名失效」；目录/正文均通过 ⇒ 三组皆无
        val result = BookCheckResult(
            domainReachable = true,
            searchChecked = true,
            searchSuccess = true,
            searchCategorySuccess = true,
            searchContentSuccess = true,
        )
        assertTrue(namesOf(result, checkDomain = true).isEmpty())
    }

    @Test
    fun adapter_domainUnreachable_withCheckDomain_addsDomainGroup() {
        val result = BookCheckResult(domainReachable = false)
        assertEquals(listOf(SourceCheckGroups.DOMAIN_FAIL), namesOf(result, checkDomain = true))
        assertTrue("域名校验关闭时不得因不可达打组", namesOf(result, checkDomain = false).isEmpty())
    }

    // ---------- 待清空诊断组（缺口2 最后一步：删内联时的等价性补偿） ----------

    @Test
    fun groupsToClear_rulePresent_clearsRuleEmptyMarker() {
        // 旧内联：搜索已检且链接非空 ⇒ removeGroup(搜索链接规则为空)；发现同理
        assertEquals(
            listOf(SourceCheckGroups.SEARCH_URL_EMPTY),
            QualityReportApplier.groupsToClear(
                mapOf(
                    QualityDim.SEARCH to DimState.PASS,
                    QualityDim.DISCOVERY to DimState.NOT_CHECKED,
                )
            )
        )
        assertEquals(
            listOf(SourceCheckGroups.DISCOVERY_RULE_EMPTY),
            QualityReportApplier.groupsToClear(mapOf(QualityDim.DISCOVERY to DimState.FAIL))
        )
    }

    @Test
    fun groupsToClear_ruleEmptyOrUnchecked_keepsMarker() {
        // 规则为空（NOT_APPLICABLE）⇒ 本轮结论就是"为空"，不得清；未校验（NOT_CHECKED）/缺项同理
        val dims = mapOf(
            QualityDim.SEARCH to DimState.NOT_APPLICABLE,
            QualityDim.DISCOVERY to DimState.NOT_CHECKED,
        )
        assertEquals(emptyList<String>(), QualityReportApplier.groupsToClear(dims))
        assertEquals(emptyList<String>(), QualityReportApplier.groupsToClear(emptyMap()))
    }

    @Test
    fun groupsToClear_neverOverlapsFailureGroupNames() {
        // 等价性闭环：同轮"清空集"与"新增集"不得相交 —— 否则同一组会先清后加（无意义且顺序敏感）
        val dims = mapOf(
            QualityDim.SEARCH to DimState.PASS,
            QualityDim.DISCOVERY to DimState.NOT_APPLICABLE,
        )
        val clear = QualityReportApplier.groupsToClear(dims)
        val add = QualityReportApplier.failureGroupNames(dims, FailureKind.NONE, false, false)
        assertEquals(listOf(SourceCheckGroups.SEARCH_URL_EMPTY), clear)
        assertEquals(listOf(SourceCheckGroups.DISCOVERY_RULE_EMPTY), add)
        assertTrue("清空集与新增集必须不相交", clear.toSet().intersect(add.toSet()).isEmpty())
    }
}
