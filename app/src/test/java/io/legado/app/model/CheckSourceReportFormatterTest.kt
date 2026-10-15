package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 巡检报告导出（`formatCheckSourceReportCsv`）行为护栏 —— 缺口4 的"结果可留存/可上报"能力。
 *
 * 关键不变量：①汇总行计数与任务态一致；②单源行映射到列（含状态/阶段/耗时/评分/消息）；
 * ③CSV 转义（逗号/引号/换行）；④**空任务也导出表头**（避免"空文件"假象）。
 */
class CheckSourceReportFormatterTest {

    private fun item(
        name: String = "源A",
        origin: String = "http://a.example",
        status: CheckSourceItemStatus = CheckSourceItemStatus.PASSED,
        stage: CheckSourceStage = CheckSourceStage.CONTENT,
        message: String = "",
        duration: Long = 1234L,
        score: Int = 95,
    ) = CheckSourceItemState(
        origin = origin,
        sourceName = name,
        sourceType = 0,
        status = status,
        stage = stage,
        message = message,
        durationMillis = duration,
        score = score,
    )

    private fun state(vararg items: CheckSourceItemState) = CheckSourceTaskState(
        runId = 1L,
        status = CheckSourceTaskStatus.COMPLETED,
        items = items.toList(),
    )

    @Test
    fun summaryLine_carriesCountsAndAverageScore() {
        val csv = formatCheckSourceReportCsv(
            state(
                item(status = CheckSourceItemStatus.PASSED, score = 90),
                item(status = CheckSourceItemStatus.PASSED, score = 100),
                item(status = CheckSourceItemStatus.BLOCKED, message = "存疑（登录依赖）", score = 0),
                item(status = CheckSourceItemStatus.FAILED, message = "校验失败", score = 0),
            ),
            generatedAtMillis = 42L,
        )
        val summary = csv.lineSequence().first()
        assertTrue(summary.startsWith("# 巡检报告 生成时间=42 状态=已完成"))
        assertTrue("总数须为 4", summary.contains("总数=4"))
        assertTrue("通过须为 2", summary.contains("通过=2"))
        assertTrue("失败须为 1", summary.contains("失败=1"))
        assertTrue("跳过须为 1", summary.contains("跳过=1"))
        assertTrue("平均分须为 95", summary.contains("平均分=95"))
    }

    @Test
    fun itemRow_mapsAllColumns() {
        val csv = formatCheckSourceReportCsv(state(item()), generatedAtMillis = 1L)
        val rows = csv.trimEnd('\n').split('\n')
        assertEquals("序号,书源名称,书源地址,状态,阶段,耗时(ms),评分,消息", rows[1])
        assertEquals("1,源A,http://a.example,通过,正文,1234,95,", rows[2])
        assertEquals(3, rows.size)
    }

    @Test
    fun itemRow_statusAndStageTextsFollowTaskVocabulary() {
        val csv = formatCheckSourceReportCsv(
            state(
                item(status = CheckSourceItemStatus.BLOCKED, message = "存疑（登录依赖）"),
                item(status = CheckSourceItemStatus.FAILED, message = "校验失败:x"),
                item(status = CheckSourceItemStatus.CANCELLED),
            ),
            generatedAtMillis = 1L,
        )
        val rows = csv.trimEnd('\n').split('\n')
        assertTrue(rows[2].contains(",跳过,正文,"))
        assertTrue(rows[3].contains(",失败,"))
        assertTrue(rows[4].contains(",已取消,"))
    }

    @Test
    fun fieldsWithCommaQuoteNewline_areEscaped() {
        val csv = formatCheckSourceReportCsv(
            state(
                item(
                    name = "源,带逗号",
                    message = "第一行\n第二行\"引号\"",
                    status = CheckSourceItemStatus.FAILED,
                )
            ),
            generatedAtMillis = 1L,
        )
        assertTrue("含逗号的名称须整字段加引号", csv.contains("\"源,带逗号\""))
        assertTrue("消息内的引号须翻倍", csv.contains("\"\"引号\"\""))
    }

    @Test
    fun emptyState_stillEmitsSummaryAndHeader() {
        val csv = formatCheckSourceReportCsv(
            CheckSourceTaskState(),
            generatedAtMillis = 7L,
        )
        val rows = csv.trimEnd('\n').split('\n')
        assertEquals(2, rows.size)
        assertTrue(rows[0].contains("状态=未开始"))
        assertTrue(rows[0].contains("总数=0"))
        assertEquals("序号,书源名称,书源地址,状态,阶段,耗时(ms),评分,消息", rows[1])
    }

    @Test
    fun zeroScore_isLeftBlankButDurationKept() {
        val csv = formatCheckSourceReportCsv(
            state(item(status = CheckSourceItemStatus.BLOCKED, score = 0, duration = 0L)),
            generatedAtMillis = 1L,
        )
        assertTrue("未产出评分留空（与界面口径一致）", csv.contains(",正文,0,,"))
    }
}
