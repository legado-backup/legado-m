package io.legado.app.help.config

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读产品指标单测（epub-md-rich-rendering 补充任务 S4 配对；审计 SP-09）。
 *
 * 覆盖：①四项计数各自累加；②派生比率正确；③分母为 0 ⇒ 比率 0.0（**不得** NaN/Infinity）；
 * ④`reset` 只清本类白名单键；⑤**隐私契约**：持久层只出现固定键、取值只能是 Int（无书名/链接/正文）。
 */
class ReaderMetricsTest {

    /** 记录型存储：既做计数存取，也留痕"到底写了哪些键/什么类型"。 */
    private class FakeStore : ReaderMetrics.MetricStore {
        val values = mutableMapOf<String, Int>()
        val writtenKeys = mutableListOf<String>()
        val writtenTypes = mutableListOf<Any>()

        override fun getInt(key: String): Int = values[key] ?: 0
        override fun putInt(key: String, value: Int) {
            values[key] = value
            writtenKeys += key
            writtenTypes += value
        }
    }

    @Test
    fun `四项计数各自累加且比率正确`() {
        val store = FakeStore()
        val m = ReaderMetrics(store)
        m.bookOpened(isMarkdown = true)         // 1 本 md
        m.bookOpened(isMarkdown = false)        // 1 本非 md
        m.bookOpened(isMarkdown = true)         // 2 本 md / 共 3 本
        m.templateSurfaceUsed()
        m.templateSurfaceUsed()                 // 模板面用上 2 次
        m.templateDegraded()                    // 降级 1 次
        m.richRenderRequested()
        m.richRenderRequested()
        m.richRenderRequested()
        m.richRenderRequested()                 // 请求 4 次
        m.richRenderFailed()                    // 失败 1 次

        val s = m.snapshot()
        assertEquals(3, s.bookOpens)
        assertEquals(2, s.mdOpens)
        assertEquals(2, s.templateOpens)
        assertEquals(1, s.templateDegrades)
        assertEquals(4, s.richAttempts)
        assertEquals(1, s.richFailures)
        assertEquals(2.0 / 3.0, s.mdUsageRate, 1e-9)
        assertEquals(2.0 / 3.0, s.templateUsageRate, 1e-9)
        assertEquals(0.5, s.degradeTriggerRate, 1e-9)
        assertEquals(0.25, s.richFailureRate, 1e-9)
    }

    @Test
    fun `分母为零时比率必须是零而不是 NaN 或无穷`() {
        val s = ReaderMetrics(FakeStore()).snapshot()
        listOf(s.mdUsageRate, s.templateUsageRate, s.degradeTriggerRate, s.richFailureRate)
            .forEach { rate ->
                assertEquals("空数据下比率必须为 0.0", 0.0, rate, 0.0)
                assertFalse("不得出现 NaN", rate.isNaN())
                assertFalse("不得出现 Infinity", rate.isInfinite())
            }
    }

    @Test
    fun `reset 只清本类白名单键`() {
        val store = FakeStore()
        store.values["otherFeature.flag"] = 7
        val m = ReaderMetrics(store)
        m.bookOpened(true)
        m.templateSurfaceUsed()
        m.templateDegraded()
        m.richRenderRequested()
        m.richRenderFailed()

        m.reset()

        assertEquals(7, store.values["otherFeature.flag"])
        val s = m.snapshot()
        assertEquals(0, s.bookOpens)
        assertEquals(0, s.templateDegrades)
        assertEquals(0, s.richFailures)
    }

    @Test
    fun `隐私契约 只写固定键且取值只能是 Int`() {
        val store = FakeStore()
        val m = ReaderMetrics(store)
        m.bookOpened(isMarkdown = true)
        m.templateSurfaceUsed()
        m.templateDegraded()
        m.richRenderRequested()
        m.richRenderFailed()
        m.reset()

        assertTrue("至少要写过键", store.writtenKeys.isNotEmpty())
        store.writtenKeys.forEach { key ->
            assertTrue("落盘键必须是白名单内（实际 $key）", key in ReaderMetrics.MetricKeys)
            assertTrue("键必须带固定前缀", key.startsWith(ReaderMetrics.KeyPrefix))
        }
        store.writtenTypes.forEach { value ->
            assertTrue("只允许写 Int（实际 ${value::class.simpleName}）", value is Int)
        }
        // 键名本身不得携带任何业务字段语义（书名/链接/正文/设备）
        val forbidden = listOf("bookUrl", "origin", "title", "name", "content", "device", "token")
        ReaderMetrics.MetricKeys.forEach { key ->
            forbidden.forEach { bad ->
                assertFalse("指标键不得含业务字段名 $bad：$key", key.contains(bad, ignoreCase = true))
            }
        }
    }
}
