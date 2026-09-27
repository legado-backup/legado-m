package io.legado.app.model

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W3 / REQ-15（AD-06）：听书时长**接入每日统计单源**的接线不变量。
 *
 * 现状实证（本轮校准）：`AudioPlay.upReadTime()` 原先**只**写 `readRecord`（个人总时长），
 * 从不调用 `ReadRecordDailyHelper.record()`（每日目标/排行组件的唯一数据源）⇒ 产品承诺
 * 「听得算数」无法兑现；且被调用点只有「章节切换」一处 ⇒ 会话内时长几乎不结算。
 *
 * 四条约定（对应代码中的三处改动 + 循环接线）：
 * ① `upReadTime` 同处调用 `ReadRecordDailyHelper.record(delta, now)`（单源，与阅读一致）；
 * ② **先结算再重置**：`readStartTime` 在派发前同步前移（防 executor 异步竞态导致重复计数）；
 * ③ 结算**节流**（播放进度循环 500ms/次 ⇒ 无节流会变成每秒写库）；
 * ④ 暂停与章节切换用 `force = true` 结清；播放中由服务进度循环周期性结算、暂停态不结算。
 */
class AudioPlayReadTimeSettleTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            // 工作副本可能是 CRLF（Windows 检出）⇒ 归一到 LF，保证多行断言稳定
            .replace("\r\n", "\n")

    private val audioPlay by lazy { read("src/main/java/io/legado/app/model/AudioPlay.kt") }
    private val service by lazy { read("src/main/java/io/legado/app/service/AudioPlayService.kt") }

    @Test
    fun readTimeIsRecordedThroughDailySingleSource() {
        assertTrue(
            "听书时长须走每日统计单源（与阅读同口径）",
            audioPlay.contains("ReadRecordDailyHelper.record(delta, now, forceWidgetUpdate = false)")
        )
        assertTrue("须保留原有 readRecord 个人总时长写入", audioPlay.contains("readRecord.readTime = readRecord.readTime + delta"))
    }

    @Test
    fun settleHappensBeforeTimestampReset() {
        val start = audioPlay.indexOf("fun upReadTime(force: Boolean = false)")
        assertTrue("upReadTime 须可强制结算", start > 0)
        val resetAt = audioPlay.indexOf("readStartTime = now", start)
        val dispatchAt = audioPlay.indexOf("executor.execute {", start)
        assertTrue("readStartTime 须在派发前同步前移（防异步竞态重复计数）", resetAt in (start + 1)..dispatchAt)
        assertTrue(
            "须保留 enableReadRecord 早退语义",
            audioPlay.substring(start, dispatchAt).contains("if (!AppConfig.enableReadRecord)")
        )
    }

    @Test
    fun settleIsThrottledToAvoidPerSecondWrites() {
        assertTrue(
            "须有结算节流间隔常量（真机节拍 500ms ⇒ 10s）",
            audioPlay.contains("READ_TIME_SETTLE_INTERVAL_MS = 10_000L")
        )
        assertTrue(
            "非强制调用须受节流约束（force 才绕过）",
            audioPlay.contains("if (!force && now - lastReadTimeSettleAt < READ_TIME_SETTLE_INTERVAL_MS)")
        )
    }

    @Test
    fun pauseAndChapterSwitchForceSettle() {
        assertTrue("暂停须先结算再重置（B5 偏差修复）", audioPlay.contains("upReadTime(force = true)\n            // 计量关闭时"))
        assertTrue("章节切换须强制结算", audioPlay.contains("upReadTime(force = true)"))
    }

    @Test
    fun playbackLoopSettlesPeriodicallyButNotWhilePaused() {
        assertTrue(
            "服务进度循环须周期性结算",
            service.contains("if (!pause) {\n                    AudioPlay.upReadTime()\n                }")
        )
    }
}