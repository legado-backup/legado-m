package io.legado.app.utils

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * B1 · R1「Cron 单值步进语义」回归测试。
 *
 * 缺陷（修复前）：`parseField` 对「单值 + 步进」恒取 `value..value` ⇒ 步进被静默吃掉，
 * 例如 `0/15` 只在整点触发（而非每 15 分钟），`5/15` 只匹配第 5 分。
 * 修复：单值 + 步进 = 从该值起步长延伸到字段上界（标准 cron 语义）。
 *
 * 断言走**公开行为** `CronSchedule.parse(...).nextTimeAfter(...)`（`matches` 为私有），
 * 固定 `ZoneId.of("UTC")` 保证确定性（不依赖运行机器时区）。
 */
class CronScheduleTest {

    private val utc: ZoneId = ZoneId.of("UTC")
    private val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")

    private fun next(expr: String, fromIso: String): String? =
        CronSchedule.parse(expr)
            ?.nextTimeAfter(Instant.parse(fromIso).toEpochMilli(), utc)
            ?.let { Instant.ofEpochMilli(it).atZone(utc).format(fmt) }

    // ---- R1-1：单值 + 步进从该值延伸到上界 ----
    @Test
    fun r1_1_singleValueWithStep_expandsToUpperBound() {
        val e = "5/15 * * * *"
        assertEquals("2026-01-01 00:05", next(e, "2026-01-01T00:00:00Z"))
        assertEquals("2026-01-01 00:20", next(e, "2026-01-01T00:05:00Z"))
        assertEquals("2026-01-01 00:35", next(e, "2026-01-01T00:20:00Z"))
        assertEquals("2026-01-01 00:50", next(e, "2026-01-01T00:35:00Z"))
        // 50 之后本小时无更多命中 ⇒ 顺延到下一小时的 :05
        assertEquals("2026-01-01 01:05", next(e, "2026-01-01T00:50:00Z"))
    }

    // ---- R1-2：最常见的 `0/15`（每 15 分钟）----
    @Test
    fun r1_2_zeroStep_meansEveryNMinutes() {
        val e = "0/15 * * * *"
        assertEquals("2026-01-01 00:15", next(e, "2026-01-01T00:01:00Z"))
        assertEquals("2026-01-01 00:30", next(e, "2026-01-01T00:15:00Z"))
        assertEquals("2026-01-01 00:45", next(e, "2026-01-01T00:30:00Z"))
        assertEquals("2026-01-01 01:00", next(e, "2026-01-01T00:45:00Z"))
        assertEquals("2026-01-01 01:15", next(e, "2026-01-01T01:00:00Z"))
    }

    // ---- R1-3：既有语义不回归（`*` / 区间 / 列表 / 区间+步进 / 通配+步进）----
    @Test
    fun r1_3_existingSemanticsNotRegressed() {
        assertEquals("2026-01-01 00:01", next("* * * * *", "2026-01-01T00:00:30Z"))
        assertEquals("2026-01-01 01:01", next("1-5 * * * *", "2026-01-01T00:05:00Z"))
        assertEquals("2026-01-01 00:03", next("1,3,5 * * * *", "2026-01-01T00:02:00Z"))
        assertEquals("2026-01-01 00:21", next("1-30/10 * * * *", "2026-01-01T00:11:00Z"))
        assertEquals("2026-01-01 00:10", next("*/10 * * * *", "2026-01-01T00:00:00Z"))
        // 小时字段同样适用（`9/6` → 9,15,21）
        assertEquals("2026-01-01 09:00", next("0 9/6 * * *", "2026-01-01T00:00:00Z"))
        assertEquals("2026-01-01 15:00", next("0 9/6 * * *", "2026-01-01T09:00:00Z"))
        assertEquals("2026-01-01 21:00", next("0 9/6 * * *", "2026-01-01T15:00:00Z"))
    }

    // ---- R1-4：越界 / 非法 ⇒ 解析失败（不得静默产生空集合后按「永不触发」跑）----
    @Test
    fun r1_4_outOfRangeOrIllegal_isRejected() {
        assertNull("分钟 > 59", CronSchedule.parse("60/5 * * * *"))
        assertNull("小时 > 23", CronSchedule.parse("0 24 * * *"))
        assertNull("日 > 31", CronSchedule.parse("0 0 32 * *"))
        assertNull("月 > 12", CronSchedule.parse("0 0 1 13 *"))
        assertNull("步进 0", CronSchedule.parse("*/0 * * * *"))
        assertNull("区间倒序", CronSchedule.parse("1-0 * * * *"))
        assertNull("段数不为 5", CronSchedule.parse("* * * *"))
        assertNull("空段", CronSchedule.parse("1,,2 * * * *"))
    }
}