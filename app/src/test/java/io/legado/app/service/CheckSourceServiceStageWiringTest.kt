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
        // 观测层不得改变既有分组/权重判定（回归护栏）
        listOf("\"校验超时\"", "\"js失效\"", "\"网站失效\"").forEach {
            assertTrue("既有失败分组丢失：$it", t.contains(it))
        }
    }
}