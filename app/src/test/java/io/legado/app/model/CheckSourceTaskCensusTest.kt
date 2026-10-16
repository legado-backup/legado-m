package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-102：校验任务**失败归因计数**内置化（纯 JVM 行为级）。
 *
 * 缺陷背景：`FailureKind{TIMEOUT, SCRIPT, NETWORK}` 早已由 `SourceQualityChecker` /
 * `QualityReportApplier.failureKindOf` 推出，但此前**只用于写书源失效分组**，任务态不携带 ⇒
 * 用户看到的横幅 / 导出报告只有「失败 N」，无法区分「源站不可达」与「探测超时」「规则缺陷」；
 * 外部巡检脚本也只能自行归类（口径漂移 + 重复实现）。
 *
 * 本类固化两条新口径：
 *  ① 归因计数**只认 `FAILED`**（探测过程中可能写过归因、最终判「存疑跳过」的项不得重复计入失败）；
 *  ② 文案**单源**：页内横幅 / 导出 CSV / REST-MCP 出参共用 [CheckSourceTaskState.failureBreakdownText]。
 */
class CheckSourceTaskCensusTest {

    private fun item(
        origin: String,
        status: CheckSourceItemStatus,
        kind: FailureKind = FailureKind.NONE,
        suspect: Boolean = false,
    ) = CheckSourceItemState(
        origin = origin,
        sourceName = origin,
        sourceType = 1,
        status = status,
        failureKind = kind,
        suspect = suspect,
    )

    private fun completed(items: List<CheckSourceItemState>) = CheckSourceTaskState(
        runId = 1L,
        status = CheckSourceTaskStatus.COMPLETED,
        items = items,
    )

    private val passed = CheckSourceItemStatus.PASSED
    private val failed = CheckSourceItemStatus.FAILED
    private val blocked = CheckSourceItemStatus.BLOCKED
    private val cancelled = CheckSourceItemStatus.CANCELLED

    @Test
    fun failureCounts_splitByAttribution() {
        val state = completed(
            listOf(
                item("p", passed),
                item("t", failed, FailureKind.TIMEOUT),
                item("s", failed, FailureKind.SCRIPT),
                item("n", failed, FailureKind.NETWORK),
                item("r", failed, FailureKind.NONE),
            )
        )
        assertEquals("失败总数须为 4", 4, state.failedCount)
        assertEquals("超时归因计数", 1, state.timeoutCount)
        assertEquals("脚本归因计数", 1, state.scriptFailCount)
        assertEquals("站点归因计数", 1, state.siteFailCount)
        assertEquals("规则归因计数（无异常短路的维度失败）", 1, state.ruleFailCount)
    }

    @Test
    fun nonFailedStatus_doesNotCountTowardAttribution() {
        // 关键口径：探测中已写过 failureKind、最终判「存疑跳过」/「取消」/「通过」的项
        // **不得**计入失败归因 —— 否则「存疑不误杀」口径在统计层被击穿
        val state = completed(
            listOf(
                item("b", blocked, FailureKind.NONE, suspect = true),
                item("c", cancelled, FailureKind.TIMEOUT),
                item("p2", passed, FailureKind.TIMEOUT),
            )
        )
        assertEquals(0, state.timeoutCount)
        assertEquals(0, state.scriptFailCount)
        assertEquals(0, state.siteFailCount)
        assertEquals(0, state.ruleFailCount)
        assertEquals("存疑跳过单独计数", 1, state.suspectCount)
    }

    @Test
    fun failureBreakdownText_listsOnlyNonZeroKindsInFixedOrder() {
        val state = completed(
            listOf(
                item("t1", failed, FailureKind.TIMEOUT),
                item("t2", failed, FailureKind.TIMEOUT),
                item("n1", failed, FailureKind.NETWORK),
                item("r1", failed, FailureKind.NONE),
            )
        )
        assertEquals("超时 2 · 站点 1 · 规则 1", state.failureBreakdownText())
        assertEquals(
            "无失败时不得产出噪声",
            "",
            completed(listOf(item("p", passed))).failureBreakdownText(),
        )
    }

    @Test
    fun bannerText_completedCarriesAttribution() {
        val text = completed(listOf(item("p", passed), item("s", failed, FailureKind.SCRIPT)))
            .bannerText().orEmpty()
        assertTrue("须含结果计数: $text", text.contains("通过 1") && text.contains("失败 1"))
        assertTrue("须含归因摘要: $text", text.contains("归因 脚本 1"))
    }

    @Test
    fun bannerText_withoutFailure_hasNoAttributionNoise() {
        val text = completed(listOf(item("p", passed))).bannerText().orEmpty()
        assertFalse("无失败不得出现归因段: $text", text.contains("归因"))
    }

    @Test
    fun csvExport_carriesAttributionSummaryAndColumn() {
        val state = completed(listOf(item("源p", passed), item("源n", failed, FailureKind.NETWORK)))
        val csv = formatCheckSourceReportCsv(state, generatedAtMillis = 7L)
        assertTrue("首行须含归因摘要: $csv", csv.contains("归因=站点 1"))
        assertTrue("表头须含归因列", csv.contains("状态,阶段,耗时(ms),评分,归因,消息"))
        val failedRow = csv.lineSequence().first { it.startsWith("2,") }
        assertTrue("失败行须带站点归因: $failedRow", failedRow.contains(",站点,"))
        val passedRow = csv.lineSequence().first { it.startsWith("1,") }
        assertTrue("通过行归因列须留空: $passedRow", passedRow.contains("0,,,"))
    }

    @Test
    fun itemFailureKindText_onlyForFailedItems() {
        assertEquals("超时", item("t", failed, FailureKind.TIMEOUT).failureKindText())
        assertEquals("脚本", item("s", failed, FailureKind.SCRIPT).failureKindText())
        assertEquals("站点", item("n", failed, FailureKind.NETWORK).failureKindText())
        assertEquals("规则", item("r", failed, FailureKind.NONE).failureKindText())
        assertEquals("通过行不得产出归因", "", item("p", passed, FailureKind.TIMEOUT).failureKindText())
        assertEquals("跳过行不得产出归因", "", item("b", blocked, FailureKind.NETWORK).failureKindText())
    }
}
