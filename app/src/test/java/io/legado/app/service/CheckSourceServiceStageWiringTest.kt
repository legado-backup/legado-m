package io.legado.app.service

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.2.3 `Q-N5` 服务侧接线不变量（源码文本断言）：
 * `CheckSourceService` 必须把真实的七阶段推进与结果写入结构化状态机，且**不改判定结论**。
 */
class CheckSourceServiceStageWiringTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/service/CheckSourceService.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readText()
    }

    @Test
    fun sevenStagesAreMarked() {
        val t = code()
        // 六个显式阶段在服务侧打点；PREPARING 由 markRunning 统一置位（单源开始即准备阶段）
        listOf("DOMAIN", "SEARCH", "DISCOVERY", "INFO", "CATALOG", "CONTENT")
            .forEach { assertTrue("阶段未打点：$it", t.contains("CheckSourceStage.$it")) }
        assertTrue("单源开始须 markRunning", t.contains("CheckSourceTaskStore.markRunning("))
    }

    @Test
    fun taskLifecycleIsWired() {
        val t = code()
        assertTrue("任务开始须 begin", t.contains("CheckSourceTaskStore.begin("))
        assertTrue("成功须 markPassed", t.contains("CheckSourceTaskStore.markPassed("))
        assertTrue("失败须 markFailed", t.contains("CheckSourceTaskStore.markFailed("))
        assertTrue(
            "结束须 finish（含取消判定）",
            t.contains("CheckSourceTaskStore.finish(cancelled = cause is CancellationException)")
        )
    }

    @Test
    fun resultScoreReusesExistingWeight() {
        val t = code()
        // 结果评分必须沿用既有权重口径，禁止新造分数体系
        assertTrue("评分须取 source.weight", t.contains("score = source.weight"))
        assertTrue("权重仍由既有计算器产出", t.contains("SourceWeightCalculator.calculateBookWeightFromResult"))
    }

    @Test
    fun failureGroupingIsUnchanged() {
        val t = code()
        // 观测层不得改变既有分组/权重判定（回归护栏）。
        // 缺口6 → 缺口2 两步收敛后：分组名不再由服务自带，归因/分组名均**委托单源底座** ——
        // 字面量由 `SourceCheckGroupsTest` 锁定、归因与编排由 `SourceCheckFailureUnificationTest` 锁定（双保险）
        assertTrue("归因须委托单源分类器", t.contains("QualityReportApplier.failureKindOf(e)"))
        assertTrue("分组名须取自单源", t.contains("QualityReportApplier.failureKindGroup("))
    }

    @Test
    fun groupBackfillDelegatesToSharedOrchestration() {
        val t = code()
        // 缺口2 末尾：服务侧**不再自持**加组规则（旧约 50 行内联 add/removeGroup 已删），
        // 一律走「结果 → 维度态适配器 → 唯一编排」
        assertTrue(
            "须用结果→维度态适配器",
            t.contains("QualityReportApplier.bookResultToDimStates(result)")
        )
        assertTrue(
            "须走唯一编排写组",
            t.contains("QualityReportApplier.applyBookGroupsFromDims(")
        )
        assertTrue(
            "服务侧不得再直接引用分组词表（口径单源化）",
            !t.contains("SourceCheckGroups.")
        )
    }

    @Test
    fun suspectSkipClearsGroupsWrittenThisRound() {
        val t = code()
        // 存疑放行分支必须复清一次「失效」分组：本轮开头已清、探测中又按维度写下，
        // 若跳过时不复清则残留"失效"标签，与「存疑不写失败分组」自相矛盾
        val occurrences = Regex("source\\.removeInvalidGroups\\(\\)").findAll(t).count()
        assertTrue(
            "本轮开头 + 存疑放行分支须各清一次（实际 $occurrences 次）",
            occurrences >= 2
        )
    }

    @Test
    fun runConfigOverridesAreWired() {
        val t = code()
        // 程序化启动（REST /startCheckSource）下发的运行期覆盖必须被消费：超时与下游三维
        // 一律走「任务级覆盖优先、缺省沿用单例现值」的生效值，否则参数静默失效（调用方以为已生效）
        assertTrue("须消费运行期配置", t.contains("CheckSourceRunConfig.INTENT_KEY"))
        assertTrue("单源超时须走生效值", t.contains("withTimeout(effTimeout)"))
        listOf("effCheckInfo", "effCheckCategory", "effCheckContent").forEach {
            assertTrue("下游维度须走生效值：$it", t.contains("!$it"))
        }
    }
}