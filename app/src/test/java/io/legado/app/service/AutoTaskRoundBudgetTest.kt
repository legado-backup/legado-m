package io.legado.app.service

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B2 · R6「FGS 分流 + 执行超时」不变量测试。
 *
 * 背景：一次执行窗口受短时 FGS 系统上限约束（`shortService` ≈3 分钟），而修复前对**单条规则耗时
 * 无任何约束** ⇒ 前面的规则卡住会被系统在任务中途掐断，且无「规则 id + 阶段 + 耗时」证据。
 * 修复：单轮预算护栏（`ROUND_BUDGET_MS`），预算用尽后不再启动新任务。
 *
 * 同时锁住 R6 明确要求**不得破坏**的既有不变量：**排程先于执行**（否则短任务超时会漏排下一次闹钟，
 * 导致整条定时链中断 —— 见源码 `:153-155` 的既有说明）。
 */
class AutoTaskRoundBudgetTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/service/AutoTaskService.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun roundBudgetGuard_sitsBeforeStartingNextTask() {
        val t = code()
        val budget = t.indexOf("ROUND_BUDGET_MS")
        val run = t.indexOf("runTask(task)")
        assertTrue("应存在单轮预算护栏", budget >= 0)
        assertTrue("必须在启动下一条任务前判定预算", run > budget)
        assertTrue("越界判定应体现为可读比较（elapsed > ROUND_BUDGET_MS）", t.contains("elapsed > ROUND_BUDGET_MS"))
    }

    @Test
    fun budgetLog_carriesRuleIdStageAndElapsed() {
        val t = code()
        assertTrue("日志必须带规则 id", t.contains("id=\${task.id}"))
        assertTrue("日志必须带阶段", t.contains("阶段="))
        assertTrue("日志必须带耗时", t.contains("已耗时="))
        assertTrue("跳过数量须回执到通知", t.contains("auto_task_round_budget_exceeded"))
    }

    @Test
    fun budgetIsSafelyBelowShortServiceCap() {
        val t = code()
        val m = Regex("ROUND_BUDGET_MS\\s*=\\s*([0-9_]+)L").find(t)
        assertTrue("未解析到 ROUND_BUDGET_MS 数值", m != null)
        val ms = m!!.groupValues[1].replace("_", "").toLong()
        assertTrue("预算($ms ms)必须小于短时 FGS 上限 180000ms 且留有余量", ms in 1..150_000)
    }

    @Test
    fun schedulingStillPrecedesExecution() {
        val t = code()
        val schedule = t.indexOf("scheduleNextRunFromRules()")
        val process = t.indexOf("processDueTasks()")
        assertTrue("排程调用应存在", schedule >= 0 && process >= 0)
        assertTrue("R6 要求「排程先于执行」不得被破坏", schedule < process)
    }
}