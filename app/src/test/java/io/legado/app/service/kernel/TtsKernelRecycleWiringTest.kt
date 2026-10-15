package io.legado.app.service.kernel

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-64（三端复用侧）：`TtsKernel.httpTtsDelete` 必须**删除前回收**。
 *
 * 为什么与 UI 路径分开断言：本仓业务逻辑只放内核层（Web 控制器 / MCP 工具只调 Kernel）⇒
 * 删除 HTTP TTS 存在**两条**独立删除路径（应用内 `SpeakEngineDialog` + 内核 `httpTtsDelete`，
 * 后者被 `TtsRoutes` / `TtsTools` 复用）；任一条漏回收，用户从该入口删除后仍不可恢复。
 */
class TtsKernelRecycleWiringTest {

    @Test
    fun `内核删除必须先回收再落库删除`() {
        val src = SourceFileProbe.sourceText("service/kernel/TtsKernel.kt")
        assertTrue("删除路径必须调用回收入口", src.contains("SourceRecycleBinHelp.recycleHttpTtsRules(listOf(exist))"))
        val recycleAt = src.indexOf("recycleHttpTtsRules")
        val deleteAt = src.indexOf("appDb.httpTTSDao.delete(exist)")
        assertTrue("回收必须早于 DAO 删除", recycleAt in 1 until deleteAt)
        assertEquals("回收异常不得阻断删除", true, src.contains("kotlin.runCatching { SourceRecycleBinHelp.recycleHttpTtsRules("))
    }

    @Test
    fun `删除契约仍为按 id 且缺失即抛`() {
        val src = SourceFileProbe.sourceText("service/kernel/TtsKernel.kt")
        assertEquals("按 id 取实体必须保留", true, src.contains("appDb.httpTTSDao.get(id) ?: throw NoSuchElementException"))
        assertEquals("返回结构契约必须保留", true, src.contains("mapOf(\"deleted\" to id, \"name\" to exist.name)"))
    }
}
