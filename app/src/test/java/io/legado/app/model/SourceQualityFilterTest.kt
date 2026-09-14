package io.legado.app.model

import io.legado.app.constant.BookSourceType
import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.RssSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 导入源质量过滤单元测试（import-source-quality-filter tasks 2.5）
 *
 * 覆盖：形态模板选择（file/video/纯发现/webview 不歧视）、归一化计分、
 * 用户层四态映射、三档判定规则表（suspect 强制放行/换词重试语义/存疑放行）、
 * L1 静态结构规则（RSS webview 型不误杀）、suspect 五类检测、内网地址判定
 */
class SourceQualityFilterTest {

    // === 形态模板选择（AD-02 零形态歧视） ===

    @Test
    fun `file型模板不含详情目录正文维度`() {
        val t = SourceQualityScorer.selectBookTemplate(BookSourceType.file, hasSearch = true, hasDiscovery = false)
        assertFalse(t.any { it.dim == QualityDim.INFO })
        assertFalse(t.any { it.dim == QualityDim.CATEGORY })
        assertFalse(t.any { it.dim == QualityDim.CONTENT })
    }

    @Test
    fun `纯发现源模板用发现维度而非搜索`() {
        val t = SourceQualityScorer.selectBookTemplate(BookSourceType.default, hasSearch = false, hasDiscovery = true)
        assertTrue(t.any { it.dim == QualityDim.DISCOVERY })
        assertFalse(t.any { it.dim == QualityDim.SEARCH })
    }

    @Test
    fun `RSS webview型模板用首屏维度`() {
        val t = SourceQualityScorer.selectRssTemplate(0, isWebView = true)
        assertTrue(t.any { it.dim == QualityDim.FIRST_SCREEN })
    }

    @Test
    fun `RSS视频型模板含线路集数维度`() {
        val t = SourceQualityScorer.selectRssTemplate(2, isWebView = false)
        assertTrue(t.any { it.dim == QualityDim.EPISODES })
    }

    // === 归一化计分 ===

    private fun bookReport(
        dims: Map<QualityDim, DimResult>,
        suspect: Boolean = false
    ): SourceQualityReport {
        return SourceQualityReport(
            sourceUrl = "https://a.com",
            sourceType = BookSourceType.default,
            checkedDepth = 2,
            dimensions = dims,
            suspect = suspect
        )
    }

    @Test
    fun `全维度通过得满分`() {
        val template = SourceQualityScorer.selectBookTemplate(BookSourceType.default, hasSearch = true, hasDiscovery = false)
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.PASS, resultCount = 5),
                QualityDim.INFO to DimResult(DimState.PASS),
                QualityDim.CATEGORY to DimResult(DimState.PASS),
                QualityDim.CONTENT to DimResult(DimState.PASS)
            )
        )
        assertEquals(100, SourceQualityScorer.score(report, template).score)
    }

    @Test
    fun `未校验维度不计分母-只测域名通过得满分但覆盖度低`() {
        val template = SourceQualityScorer.selectBookTemplate(BookSourceType.default, hasSearch = true, hasDiscovery = false)
        val scored = SourceQualityScorer.score(
            bookReport(mapOf(QualityDim.DOMAIN to DimResult(DimState.PASS))),
            template
        )
        // 归一化口径：已校验维度全过=100
        assertEquals(100, scored.score)
        // 覆盖度 1/5 补偿语义
        assertEquals(0.2f, scored.coverage, 0.001f)
    }

    @Test
    fun `NOT_APPLICABLE维度不扣分-纯发现源可满分`() {
        val template = SourceQualityScorer.selectBookTemplate(BookSourceType.default, hasSearch = false, hasDiscovery = true)
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.DISCOVERY to DimResult(DimState.PASS, resultCount = 3),
                QualityDim.INFO to DimResult(DimState.PASS),
                QualityDim.CATEGORY to DimResult(DimState.PASS),
                QualityDim.CONTENT to DimResult(DimState.PASS)
            )
        )
        assertEquals(100, SourceQualityScorer.score(report, template).score)
    }

    // === 用户层四态映射 ===

    @Test
    fun `四态映射-失效优先于存疑优先于未测`() {
        val failed = SourceQualityScorer.toUserState(
            bookReport(mapOf(QualityDim.DOMAIN to DimResult(DimState.FAIL))))
        assertEquals(SourceQualityScorer.UserState.FAILED, failed)

        val suspect = SourceQualityScorer.toUserState(
            bookReport(
                mapOf(
                    QualityDim.DOMAIN to DimResult(DimState.PASS),
                    QualityDim.SEARCH to DimResult(DimState.FAIL)
                ),
                suspect = true
            )
        )
        assertEquals(SourceQualityScorer.UserState.SUSPECT, suspect)

        val untested = SourceQualityScorer.toUserState(
            bookReport(
                mapOf(
                    QualityDim.DOMAIN to DimResult(DimState.PASS),
                    QualityDim.SEARCH to DimResult(DimState.NOT_CHECKED)
                )
            )
        )
        assertEquals(SourceQualityScorer.UserState.UNTESTED, untested)

        val usable = SourceQualityScorer.toUserState(
            bookReport(mapOf(QualityDim.DOMAIN to DimResult(DimState.PASS)))
        )
        assertEquals(SourceQualityScorer.UserState.USABLE, usable)
    }

    // === 三档判定规则表（AD-04） ===

    @Test
    fun `宽松档-域名不可达过滤`() {
        val report = bookReport(mapOf(QualityDim.DOMAIN to DimResult(DimState.FAIL, failedByException = true)))
        val (filtered, reason) = SourceQualityScorer.isFiltered(report, CheckStrictness.LENIENT)
        assertTrue(filtered)
        assertTrue(reason.contains("打不开"))
    }

    @Test
    fun `宽松档-搜索0结果过滤`() {
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.FAIL, evidence = "搜索不到结果")
            )
        )
        val (filtered, _) = SourceQualityScorer.isFiltered(report, CheckStrictness.LENIENT)
        assertTrue(filtered)
    }

    @Test
    fun `宽松档-搜索网络异常存疑放行`() {
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.FAIL, failedByException = true, evidence = "请求超时")
            )
        )
        val (filtered, _) = SourceQualityScorer.isFiltered(report, CheckStrictness.LENIENT)
        assertFalse(filtered)
    }

    @Test
    fun `标准档-搜索网络异常过滤`() {
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.FAIL, failedByException = true, evidence = "请求超时")
            )
        )
        val (filtered, _) = SourceQualityScorer.isFiltered(report, CheckStrictness.STANDARD)
        assertTrue(filtered)
    }

    @Test
    fun `宽松标准档-suspect源强制放行`() {
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.FAIL, failedByException = true)
            ),
            suspect = true
        )
        assertFalse(SourceQualityScorer.isFiltered(report, CheckStrictness.LENIENT).first)
        assertFalse(SourceQualityScorer.isFiltered(report, CheckStrictness.STANDARD).first)
        // 严格档：suspect 源进复核由用户显式选择
        assertTrue(SourceQualityScorer.isFiltered(report, CheckStrictness.STRICT).first)
    }

    @Test
    fun `严格档-目录正文失败过滤`() {
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.PASS, resultCount = 3),
                QualityDim.INFO to DimResult(DimState.PASS),
                QualityDim.CATEGORY to DimResult(DimState.FAIL, evidence = "目录为空"),
                QualityDim.CONTENT to DimResult(DimState.PASS)
            )
        )
        assertFalse(SourceQualityScorer.isFiltered(report, CheckStrictness.LENIENT).first)
        assertFalse(SourceQualityScorer.isFiltered(report, CheckStrictness.STANDARD).first)
        assertTrue(SourceQualityScorer.isFiltered(report, CheckStrictness.STRICT).first)
    }

    @Test
    fun `宽松档-同host限额推断失败不算确定性失败`() {
        val report = bookReport(
            mapOf(
                QualityDim.DOMAIN to DimResult(DimState.PASS),
                QualityDim.SEARCH to DimResult(DimState.FAIL, failedByException = true, evidence = "同站首测未过(推断)")
            )
        )
        assertFalse(SourceQualityScorer.isFiltered(report, CheckStrictness.LENIENT).first)
    }

    // === L1 静态结构规则 ===

    @Test
    fun `L1-书源无搜索且非发现-结构残缺`() {
        val source = BookSource(bookSourceUrl = "https://a.com", searchUrl = "", enabledExplore = false)
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertTrue(report.deterministicFail)
    }

    @Test
    fun `L1-纯发现源不判残缺`() {
        val source = BookSource(
            bookSourceUrl = "https://a.com",
            searchUrl = "",
            enabledExplore = true,
            exploreUrl = "/xyz/{\"source\":\"分类\"}"
        )
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertFalse(report.deterministicFail)
    }

    @Test
    fun `L1-RSS列表规则缺失不判残缺-webview型合法`() {
        val source = RssSource(
            sourceUrl = "https://a.com",
            startHtml = "<html></html>",
            loadWithBaseUrl = true
        )
        val report = SourceQualityChecker.l1StaticCheckRssSource(source)
        assertFalse(report.deterministicFail)
        assertTrue(report.suspect)
        assertTrue(report.suspectReasons.contains(SuspectReason.WEB_VIEW))
    }

    @Test
    fun `L1-RSS源地址为空-结构残缺`() {
        val source = RssSource(sourceUrl = "")
        val report = SourceQualityChecker.l1StaticCheckRssSource(source)
        assertTrue(report.deterministicFail)
    }

    // === suspect 五类静态检测 ===

    @Test
    fun `suspect-登录依赖`() {
        val source = BookSource(bookSourceUrl = "https://a.com", searchUrl = "/search", loginUi = "{\"k\":\"v\"}")
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertTrue(report.suspectReasons.contains(SuspectReason.LOGIN))
    }

    @Test
    fun `suspect-源变量依赖`() {
        val source = BookSource(
            bookSourceUrl = "https://a.com",
            searchUrl = "/search?key={{source.getVariable()}}"
        )
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertTrue(report.suspectReasons.contains(SuspectReason.SOURCE_VARIABLE))
    }

    @Test
    fun `suspect-useWebView依赖`() {
        val source = BookSource(
            bookSourceUrl = "https://a.com",
            searchUrl = "/search,{\"useWebView\":true}"
        )
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertTrue(report.suspectReasons.contains(SuspectReason.WEB_VIEW))
    }

    @Test
    fun `suspect-jsLib依赖`() {
        val source = BookSource(
            bookSourceUrl = "https://a.com",
            searchUrl = "@js:result+'?q={{key}}'",
            jsLib = "function helper(){}"
        )
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertTrue(report.suspectReasons.contains(SuspectReason.JS_LIB))
    }

    @Test
    fun `suspect-正常源不误标`() {
        val source = BookSource(bookSourceUrl = "https://a.com", searchUrl = "/search?q={{key}}")
        val report = SourceQualityChecker.l1StaticCheckBookSource(source)
        assertFalse(report.suspect)
    }

    // === 内网地址判定（S1 防内网扫描） ===

    @Test
    fun `内网地址-字面回环与私有网段判定`() {
        assertTrue(SourceQualityChecker.isPrivateAddress("http://127.0.0.1:8080/x"))
        assertTrue(SourceQualityChecker.isPrivateAddress("http://192.168.1.1/x"))
        assertTrue(SourceQualityChecker.isPrivateAddress("http://10.0.0.2/x"))
        assertTrue(SourceQualityChecker.isPrivateAddress("http://172.16.0.1/x"))
        assertTrue(SourceQualityChecker.isPrivateAddress("http://169.254.169.254/latest"))
        assertFalse(SourceQualityChecker.isPrivateAddress("https://www.example.com/x"))
        assertFalse(SourceQualityChecker.isPrivateAddress("http://8.8.8.8/x"))
    }
}
