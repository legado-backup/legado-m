package io.legado.app.help

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 §3.1.2（Q2）：主线程卡顿自诊断
 *
 * 真机触发卡顿不可控 ⇒ 拆两层验证：
 * 1. 纯函数 [culpritStackTop] 的截断/格式（真机取证文本即由它产出）；
 * 2. 接线不变量（ping-pong 回执、阈值、冷却防抖、代次幂等）。
 */
class AppFreezeMonitorTest {

    private fun stackOf(size: Int) = Array(size) { idx ->
        StackTraceElement("com.example.Cls$idx", "method$idx", "Cls$idx.kt", idx + 1)
    }

    @Test
    fun culpritStackIsTruncatedToLimit() {
        val text = culpritStackTop(stackOf(60), 45)
        val lines = text.lines()
        assertEquals("必须截断到 45 行", 45, lines.size)
        assertEquals("at com.example.Cls0.method0(Cls0.kt:1)", lines.first())
    }

    @Test
    fun culpritStackKeepsAllWhenShorterThanLimit() {
        val text = culpritStackTop(stackOf(3), 45)
        assertEquals(3, text.lines().size)
    }

    @Test
    fun culpritStackHandlesMissingStack() {
        assertEquals("（无栈信息）", culpritStackTop(null, 45))
        assertEquals("（无栈信息）", culpritStackTop(emptyArray<StackTraceElement>(), 45))
        assertEquals("（无栈信息）", culpritStackTop(stackOf(3), 0))
    }

    @Test
    fun watchdogPingsMainThreadWithAckTimeout() {
        val code = SourceFileProbe.sourceText("help/AppFreezeMonitor.kt")
        assertTrue(
            "必须向主线程投递回执任务并在超时后判定卡顿",
            code.contains("mainHandler.post { acked.set(true) }") &&
                code.contains("if (!acked.get()) {")
        )
        assertTrue("主线程阈值应为 1s（远早于系统 5s ANR）", code.contains("MAIN_THREAD_STALL_MS = 1000L"))
        assertTrue("凶手栈上限应为 45 行", code.contains("CULPRIT_STACK_MAX_LINES = 45"))
        assertTrue(
            "凶手栈必须取主线程当前栈",
            code.contains("Looper.getMainLooper()?.thread?.stackTrace")
        )
    }

    @Test
    fun watchdogLogsWithCooldownAndAppLog() {
        val code = SourceFileProbe.sourceText("help/AppFreezeMonitor.kt")
        assertTrue("诊断日志必须走 AppLog（项目日志铁律）", code.contains("AppLog.put("))
        assertTrue("卡顿日志必须带冷却防抖", code.contains("STALL_LOG_COOLDOWN_MS = 3000L"))
        assertTrue(
            "冷却期内必须直接返回不再打日志",
            code.contains("if (now - lastStallLogAt < STALL_LOG_COOLDOWN_MS) return")
        )
    }

    @Test
    fun heartbeatIsIdempotentAndRestartable() {
        val code = SourceFileProbe.sourceText("help/AppFreezeMonitor.kt")
        assertTrue("重复 init 不得叠加循环", code.contains("if (heartbeatActive) return"))
        assertTrue("代次收口用于关闭后再开启", code.contains("val generation = ++heartbeatGeneration"))
        assertTrue(
            "旧代次循环必须自行退出",
            code.contains("if (!AppConfig.recordLog || generation != heartbeatGeneration) {")
        )
        assertTrue(
            "进程冻结检测（原能力）不得被删",
            code.contains("checkProcessFreeze()") &&
                code.contains("检测到应用被系统冻结")
        )
    }
}