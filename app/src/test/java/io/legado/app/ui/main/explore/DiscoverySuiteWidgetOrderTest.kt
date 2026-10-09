package io.legado.app.ui.main.explore

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 配对单测（纯 JVM，无 Android / 无 Robolectric）：
 * 覆盖本次易用性优化抽出的**共享纯函数**（2.1.1 / 2.1.2 / 2.1.3）——
 * `withWaterfallPinnedBottom()`（AD-06 单源）、`widgetTargetsConstraint()`（约束真值单源）、
 * `isDiscoverySuiteConfigWithinLimit()`（AD-07 写盘判据同源）；
 * 另覆盖真实源真机实测后（2026-10-09）新增的两处语义：`suiteWidgetEmptyText()`（P5 文案归类）
 * 与 `STARTER_CANDIDATE_POOL` / `STARTER_MAX_USABLE_SOURCES` 的余量关系（P6）。
 *
 * 依据：`testing-iron-rule`（改源码即配对工程级测试）；本文件与被测源码同包
 * （`io.legado.app.ui.main.explore`），满足 `audit_code_change_has_test.py` 的同包配对口径。
 */
class DiscoverySuiteWidgetOrderTest {

    private fun widget(id: String, type: String) = DiscoverySuiteWidget(id = id, type = type)

    // ---------- withWaterfallPinnedBottom（AD-06） ----------

    @Test
    fun waterfallPinned_emptyList_staysEmpty() {
        assertEquals(emptyList<DiscoverySuiteWidget>(), emptyList<DiscoverySuiteWidget>().withWaterfallPinnedBottom())
    }

    @Test
    fun waterfallPinned_onlyRegular_keepsOrder() {
        val input = listOf(
            widget("a", DiscoverySuiteWidgetType.RandomBooks.value),
            widget("b", DiscoverySuiteWidgetType.TagBar.value),
            widget("c", DiscoverySuiteWidgetType.RankedList.value)
        )
        assertEquals(listOf("a", "b", "c"), input.withWaterfallPinnedBottom().map { it.id })
    }

    @Test
    fun waterfallPinned_onlyWaterfall_keepsOrder() {
        val input = listOf(
            widget("w1", DiscoverySuiteWidgetType.WaterfallBooks.value),
            widget("w2", DiscoverySuiteWidgetType.WaterfallBooks.value)
        )
        assertEquals(listOf("w1", "w2"), input.withWaterfallPinnedBottom().map { it.id })
    }

    @Test
    fun waterfallPinned_mixed_movesWaterfallToBottomPreservingRelativeOrder() {
        val input = listOf(
            widget("w1", DiscoverySuiteWidgetType.WaterfallBooks.value),
            widget("a", DiscoverySuiteWidgetType.RandomBooks.value),
            widget("w2", DiscoverySuiteWidgetType.WaterfallBooks.value),
            widget("b", DiscoverySuiteWidgetType.HorizontalBooks.value)
        )
        // 非瀑布流保持原相对顺序，瀑布流按原相对顺序整体后移
        assertEquals(listOf("a", "b", "w1", "w2"), input.withWaterfallPinnedBottom().map { it.id })
    }

    @Test
    fun waterfallPinned_isIdempotent() {
        val input = listOf(
            widget("a", DiscoverySuiteWidgetType.RandomBooks.value),
            widget("w1", DiscoverySuiteWidgetType.WaterfallBooks.value)
        )
        val once = input.withWaterfallPinnedBottom()
        assertEquals(once.map { it.id }, once.withWaterfallPinnedBottom().map { it.id })
    }

    // ---------- widgetTargetsConstraint（2.1.2 单源真值） ----------

    @Test
    fun targetConstraint_rankTypes_areThreeToNine() {
        assertEquals(WidgetTargetConstraint(3, 9), widgetTargetsConstraint(DiscoverySuiteWidgetType.RankButtons.value))
        assertEquals(WidgetTargetConstraint(3, 9), widgetTargetsConstraint(DiscoverySuiteWidgetType.RankedList.value))
    }

    @Test
    fun targetConstraint_horizontal_isExactlyOne() {
        assertEquals(
            WidgetTargetConstraint(1, 1),
            widgetTargetsConstraint(DiscoverySuiteWidgetType.HorizontalBooks.value)
        )
    }

    @Test
    fun targetConstraint_otherTypes_allowOneToMax() {
        val expected = WidgetTargetConstraint(1, MAX_WIDGET_TARGET_COUNT)
        assertEquals(expected, widgetTargetsConstraint(DiscoverySuiteWidgetType.RandomBooks.value))
        assertEquals(expected, widgetTargetsConstraint(DiscoverySuiteWidgetType.TagBar.value))
        assertEquals(expected, widgetTargetsConstraint(DiscoverySuiteWidgetType.WaterfallBooks.value))
    }

    @Test
    fun targetConstraint_historicalAndUnknownTypes_fallBackToRandomBooks() {
        // book_list 为历史类型，sanitize() 会归一为 random_books ⇒ 约束也应随之归一
        assertEquals(
            WidgetTargetConstraint(1, MAX_WIDGET_TARGET_COUNT),
            widgetTargetsConstraint("book_list")
        )
        assertEquals(
            WidgetTargetConstraint(1, MAX_WIDGET_TARGET_COUNT),
            widgetTargetsConstraint("something-not-exist")
        )
    }

    @Test
    fun targetConstraint_acceptsBoundaries() {
        val rank = widgetTargetsConstraint(DiscoverySuiteWidgetType.RankedList.value)
        assertFalse("2 个不足，应拒绝", rank.accepts(2))
        assertTrue("3 个是下边界，应接受", rank.accepts(3))
        assertTrue("9 个是上边界，应接受", rank.accepts(9))
        assertFalse("10 个超出上限，应拒绝", rank.accepts(10))

        val horizontal = widgetTargetsConstraint(DiscoverySuiteWidgetType.HorizontalBooks.value)
        assertFalse(horizontal.accepts(0))
        assertTrue(horizontal.accepts(1))
        assertFalse(horizontal.accepts(2))
    }

    // ---------- toggleSuiteTargetKey（编辑器选中规则，B2 约束） ----------

    @Test
    fun toggle_newKey_isAdded() {
        assertEquals(setOf("a"), toggleSuiteTargetKey(setOf(), "a", singleSelection = false, maxCount = 9))
    }

    @Test
    fun toggle_existingKey_isRemoved() {
        assertEquals(
            setOf("b"),
            toggleSuiteTargetKey(setOf("a", "b"), "a", singleSelection = false, maxCount = 9)
        )
    }

    @Test
    fun toggle_atMaxCount_isIgnored() {
        val full = setOf("a", "b", "c")
        assertEquals(full, toggleSuiteTargetKey(full, "d", singleSelection = false, maxCount = 3))
    }

    @Test
    fun toggle_singleSelection_replacesInsteadOfAccumulating() {
        assertEquals(
            setOf("b"),
            toggleSuiteTargetKey(setOf("a"), "b", singleSelection = true, maxCount = 1)
        )
        assertEquals(
            setOf("a"),
            toggleSuiteTargetKey(setOf("a"), "a", singleSelection = true, maxCount = 1)
        )
    }

    // ---------- looksLikeEngineError（引擎错误串伪装成标签的拦截，2026-10-09 实测） ----------

    @Test
    fun engineError_rhinoEcmaError_isDetected() {
        // 模拟器实测原文（站点侧 exploreUrl 的 JS 求值失败）
        assertTrue(
            (
                "ERROR:org.mozilla.javascript.EcmaError: TypeError: 无法调用 undefined 的方法 " +
                    "“getLoginHeader” (<Unknown source>#1) in <Unknown source> at line number 1"
                ).looksLikeEngineError()
        )
        assertTrue("ERROR:something bad".looksLikeEngineError())
        assertTrue("org.mozilla.javascript.EvaluatorException: ...".looksLikeEngineError())
        assertTrue("TypeError: x is not a function".looksLikeEngineError())
    }

    @Test
    fun engineError_normalTagTitles_areNotDetected() {
        assertFalse("玄幻".looksLikeEngineError())
        assertFalse("分类导航".looksLikeEngineError())
        assertFalse("最近更新".looksLikeEngineError())
        assertFalse("".looksLikeEngineError())
        assertFalse("   ".looksLikeEngineError())
    }

    @Test
    fun engineError_overlongTitle_isTreatedAsSuspect() {
        assertTrue("字".repeat(81).looksLikeEngineError())
    }

    // ---------- isDiscoverySuiteConfigWithinLimit（AD-07 判据同源） ----------

    @Test
    fun configLimit_boundaries() {
        assertTrue("空串在上限内", isDiscoverySuiteConfigWithinLimit(""))
        assertTrue(
            "恰好等于上限应在限内（判据为 <=）",
            isDiscoverySuiteConfigWithinLimit("x".repeat(MAX_DISCOVERY_SUITE_CONFIG_CHARS))
        )
        assertFalse(
            "超过上限一个字符即拒绝",
            isDiscoverySuiteConfigWithinLimit("x".repeat(MAX_DISCOVERY_SUITE_CONFIG_CHARS + 1))
        )
    }

    // ---------- suiteWidgetEmptyText（P5：区分「没配置」与「配置了但没加载到内容」） ----------

    @Test
    fun emptyText_loading_winsOverBothStates() {
        assertEquals(SuiteWidgetEmptyText.Loading, suiteWidgetEmptyText(isLoading = true, hasTargets = true))
        assertEquals(SuiteWidgetEmptyText.Loading, suiteWidgetEmptyText(isLoading = true, hasTargets = false))
    }

    @Test
    fun emptyText_noTargets_meansNotConfigured() {
        assertEquals(
            SuiteWidgetEmptyText.NotConfigured,
            suiteWidgetEmptyText(isLoading = false, hasTargets = false)
        )
    }

    @Test
    fun emptyText_hasTargetsButNoBooks_meansNoContent() {
        // 🔴 关键回归（2026-10-09 真实源真机实测）：targets 有值但源站没出书时，
        // 绝不能显示「尚未配置」—— 那会让用户以为自己的配置丢了。
        assertEquals(
            SuiteWidgetEmptyText.NoContent,
            suiteWidgetEmptyText(isLoading = false, hasTargets = true)
        )
    }

    // ---------- 一键生成候选池语义（P6：候选池必须远大于"可用源"目标数） ----------

    @Test
    fun starterPool_isMuchLargerThanUsableTarget() {
        // 真实库实测大量源无发现标签或规则求值失败 ⇒ 候选池过小会"一个可用的都凑不齐"、
        // 生成出空套件（用户第一印象=功能不可用）。锁住"候选池 ≥ 4 倍可用上限"的余量。
        assertTrue(
            "候选池应显著大于可用源上限",
            STARTER_CANDIDATE_POOL >= STARTER_MAX_USABLE_SOURCES * 4
        )
        assertEquals("一次生成最多纳入 5 个可用源", 5, STARTER_MAX_USABLE_SOURCES)
    }
}
