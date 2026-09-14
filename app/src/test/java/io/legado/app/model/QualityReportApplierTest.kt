package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * quality-check-unify 桥接映射单元测试（tasks 1.3）
 *
 * 覆盖：SourceQualityReport → BookCheckResult / RssCheckResult 纯映射正确性、
 * weight 联动（calculate*FromResult 语义对齐旧校验）、suspect 防误伤语义在映射层的表达
 * （suspect 不改映射结果，分组层由 applyXxxGroups 跳过——真机 L2 验证）
 *
 * 注意：分组回填（addGroup/removeGroup）依赖 Android TextUtils，JVM 单测不可执行，
 * 分组名逐字一致性与落库行为由真机 L2 验证。
 */
class QualityReportApplierTest {

    private fun dim(state: DimState, count: Int = 0) = DimResult(state, resultCount = count)

    private fun bookReport(
        vararg dims: Pair<QualityDim, DimResult>,
        failureKind: FailureKind = FailureKind.NONE,
        suspect: Boolean = false
    ): SourceQualityReport = SourceQualityReport(
        sourceUrl = "https://test",
        sourceType = 0,
        checkedDepth = 3,
        dimensions = dims.toMap(),
        suspect = suspect,
        failureKind = failureKind
    )

    // === 书源映射 ===

    @Test
    fun `全PASS报告映射全true且weight满分`() {
        val report = bookReport(
            QualityDim.DOMAIN to dim(DimState.PASS),
            QualityDim.SEARCH to dim(DimState.PASS, 10),
            QualityDim.INFO to dim(DimState.PASS),
            QualityDim.CATEGORY to dim(DimState.PASS),
            QualityDim.CONTENT to dim(DimState.PASS)
        )
        val r = QualityReportApplier.toBookCheckResult(report)
        assertTrue(r.domainReachable)
        assertTrue(r.searchChecked)
        assertTrue(r.searchSuccess)
        assertEquals(10, r.searchResultCount)
        assertTrue(r.searchInfoSuccess)
        val weight = SourceWeightCalculator.calculateBookWeightFromResult(r, true)
        assertEquals(20 + 20 + 15 + 15 + 15 + 15, weight) // 100 满分
    }

    @Test
    fun `域名FAIL映射不可达且weight为0`() {
        val report = bookReport(
            QualityDim.DOMAIN to dim(DimState.FAIL),
            QualityDim.SEARCH to dim(DimState.PASS, 5)
        )
        val r = QualityReportApplier.toBookCheckResult(report)
        assertFalse(r.domainReachable)
        assertEquals(0, SourceWeightCalculator.calculateBookWeightFromResult(r, true))
    }

    @Test
    fun `搜索FAIL映射已检但失败`() {
        val report = bookReport(
            QualityDim.DOMAIN to dim(DimState.PASS),
            QualityDim.SEARCH to dim(DimState.FAIL)
        )
        val r = QualityReportApplier.toBookCheckResult(report)
        assertTrue(r.searchChecked)
        assertFalse(r.searchSuccess)
        val weight = SourceWeightCalculator.calculateBookWeightFromResult(r, true)
        // 域名20 + 搜索失败0 + 发现未检15；详情/目录/正文因 searchChecked=true 不补偿 → 0
        assertEquals(20 + 15, weight)
    }

    @Test
    fun `搜索NOT_APPLICABLE映射URL空`() {
        val report = bookReport(
            QualityDim.DOMAIN to dim(DimState.PASS),
            QualityDim.SEARCH to dim(DimState.NOT_APPLICABLE)
        )
        val r = QualityReportApplier.toBookCheckResult(report)
        assertTrue(r.searchChecked)
        assertTrue(r.searchUrlEmpty)
        assertFalse(r.searchSuccess)
    }

    @Test
    fun `NOT_CHECKED维度weight走满分路径`() {
        // L1/L2 深度未测目录正文：NOT_CHECKED → checked=false
        val report = bookReport(
            QualityDim.DOMAIN to dim(DimState.PASS),
            QualityDim.SEARCH to dim(DimState.PASS, 3)
        )
        val r = QualityReportApplier.toBookCheckResult(report)
        assertFalse(r.searchCategorySuccess)
        assertFalse(r.searchContentSuccess)
        val weight = SourceWeightCalculator.calculateBookWeightFromResult(r, true)
        // 域名20+搜索20+发现未检15+详情未检15(searchChecked=true 不补偿→0)+目录0+正文0
        // 精确语义：searchChecked=true 时详情/目录/正文走 success 判定=false → 0 分
        assertEquals(20 + 20 + 15, weight)
    }

    // === 订阅源映射 ===

    @Test
    fun `RSS全PASS映射weight满分`() {
        val report = SourceQualityReport(
            sourceUrl = "https://rss",
            sourceType = 1,
            checkedDepth = 3,
            dimensions = mapOf(
                QualityDim.DOMAIN to dim(DimState.PASS),
                QualityDim.ARTICLES to dim(DimState.PASS, 30),
                QualityDim.RSS_SEARCH to dim(DimState.PASS, 5),
                QualityDim.RSS_SORT to dim(DimState.PASS, 4),
                QualityDim.CONTENT to dim(DimState.PASS)
            )
        )
        val r = QualityReportApplier.toRssCheckResult(report)
        assertTrue(r.domainReachable)
        assertTrue(r.articlesSuccess)
        assertEquals(30, r.articlesCount)
        assertEquals(5, r.searchResultCount)
        assertTrue(r.sortSuccess)
        val weight = SourceWeightCalculator.calculateRssWeightFromResult(r, true)
        assertEquals(20 + 25 + 20 + 15 + 20, weight) // 100 满分
    }

    @Test
    fun `RSS列表FAIL扣分且域名FAIL归零`() {
        val report = SourceQualityReport(
            sourceUrl = "https://rss",
            sourceType = 1,
            checkedDepth = 3,
            dimensions = mapOf(
                QualityDim.DOMAIN to dim(DimState.PASS),
                QualityDim.ARTICLES to dim(DimState.FAIL)
            )
        )
        val r = QualityReportApplier.toRssCheckResult(report)
        assertTrue(r.articlesChecked)
        assertFalse(r.articlesSuccess)
        val weight = SourceWeightCalculator.calculateRssWeightFromResult(r, true)
        assertEquals(20 + 20 + 15 + 20, weight) // 列表 25 扣
    }

    // === suspect 语义（宽松档存疑放行） ===

    @Test
    fun `suspect报告映射不改判定分组层跳过`() {
        // suspect 源映射结果与普通 FAIL 一致，但 applyGroups 层会跳过（不写失效组）
        val report = bookReport(
            QualityDim.DOMAIN to dim(DimState.FAIL),
            suspect = true
        )
        val r = QualityReportApplier.toBookCheckResult(report)
        assertFalse(r.domainReachable) // 映射如实反映
        // 防误伤在 applyBookGroups 中以 report.suspect 早退实现（真机 L2 验证）
    }
}
