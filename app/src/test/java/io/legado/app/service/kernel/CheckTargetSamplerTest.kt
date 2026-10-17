package io.legado.app.service.kernel

import io.legado.app.data.entities.BookSourcePart
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B12：内置巡检「选源口径」纯函数 + 启动入口委托护栏。
 *
 * 目的：外部端到端巡检改为「启动 App 内置巡检任务 → 轮询 `/getCheckSourceReport`」，
 * 从而消费 App 统一结论（内置链路按维度路由 ⇒ 消除 `no-search-entry` 口径产物）。
 * 本用例锁住选源口径（启用过滤 / urls 过滤 / 步长 / 上限）与启动委托点。
 */
class CheckTargetSamplerTest {

    private fun part(url: String, enabled: Boolean = true) =
        BookSourcePart(bookSourceUrl = url, enabled = enabled)

    @Test
    fun `只取启用中的源`() {
        val all = listOf(part("a"), part("b", enabled = false), part("c"))
        assertEquals(listOf("a", "c"), sampleCheckTargets(all).map { it.bookSourceUrl })
    }

    @Test
    fun `urls非空时只留集合内成员`() {
        val all = listOf(part("a"), part("b"), part("c"))
        assertEquals(
            listOf("b", "c"),
            sampleCheckTargets(all, setOf("b", "c", "zz")).map { it.bookSourceUrl }
        )
    }

    @Test
    fun `步长按启用过滤后的序抽样且结果可复现`() {
        val all = listOf(part("a"), part("b", enabled = false), part("c"), part("d"), part("e"), part("f"))
        // 启用过滤后 = [a, c, d, e, f] ⇒ step=2 取 index 0/2/4 = [a, d, f]
        assertEquals(listOf("a", "d", "f"), sampleCheckTargets(all, step = 2).map { it.bookSourceUrl })
        assertEquals("同参数须恒同集合（可复现）", listOf("a", "d", "f"), sampleCheckTargets(all, step = 2).map { it.bookSourceUrl })
    }

    @Test
    fun `上限截断且0表示不限`() {
        val all = listOf(part("a"), part("b"), part("c"))
        assertEquals(listOf("a", "b"), sampleCheckTargets(all, limit = 2).map { it.bookSourceUrl })
        assertEquals(3, sampleCheckTargets(all, limit = 0).size)
    }

    @Test
    fun `组合口径顺序为启用到urls到步长到上限`() {
        val all = listOf(part("a"), part("b", enabled = false), part("c"), part("d"), part("e"), part("f", enabled = false))
        // 启用⇒[a,c,d,e]；urls⇒[c,d,e]；step=2⇒[c,e]；limit=1⇒[c]
        assertEquals(
            listOf("c"),
            sampleCheckTargets(all, setOf("b", "c", "d", "e", "f"), limit = 1, step = 2)
                .map { it.bookSourceUrl }
        )
    }

    @Test
    fun `启动入口必须委托内置巡检服务并回传生效口径`() {
        val src = SourceFileProbe.sourceText("service/kernel/SourceDebugKernel.kt")
        assertEquals(
            "须委托内置服务并下发运行期覆盖（否则外部巡检无法消费统一结论 / 深度与超时参数静默失效）",
            true,
            src.contains("CheckSource.start(appCtx, targets, runConfig)")
        )
        assertEquals("须回传实际生效口径（域名探测开关）", true, src.contains("\"checkDomain\" to CheckSource.checkDomain"))
        assertEquals("选源须走受测纯函数", true, src.contains("val targets = sampleCheckTargets("))
    }
}
