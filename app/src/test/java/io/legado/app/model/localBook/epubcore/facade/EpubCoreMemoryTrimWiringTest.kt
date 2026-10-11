package io.legado.app.model.localBook.epubcore.facade

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读面内存压力释放的**接线契约**（epub-md-rich-rendering S10 配对）。
 *
 * 为什么单列接线测试：判据（[EpubCoreMemoryTrimPolicy]）正确但**没被接上**时，症状与"完全没做"
 * 一模一样（低内存下阅读页照旧占着离屏 WebView 被系统杀掉），而两者修复成本天差地别。
 *
 * 三条不变量（`App` 侧的链路接线由 `io.legado.app.AppMemoryTrimWiringTest` 覆盖）：
 * ①`EpubCoreProvider` 的释放入口必须受判据把关，且无持有时不动作（不伪造"已释放"）；
 * ②释放**只动可重建资源**：关闭**背景**布局会话 + 清字体/图片缓存；**不得**拆前台会话、
 *   也**不得**整书 `close()`（那会把正在读的书整个关掉，用户看到的是"书突然没了"）；
 * ③背景会话上限是**显式决策点**：本仓现值为 5（≠ 设计文中的 2），理由见 S10 条 AOAdapt
 *   （`slot % cap` 复用语义下把 5 降到 2 会让预取章节**逐个重建 WebView**，属性能回退；
 *   要改必须先有实测数据）⇒ 本测试**钉住现值**，使任何静默改动立即失败并指向台账。
 */
class EpubCoreMemoryTrimWiringTest {

    private fun facade(): String = SourceFileProbe.sourceText("model/localBook/epubcore/facade/EpubCoreFacade.kt")
    private fun provider(): String = SourceFileProbe.sourceText("model/localBook/epubcore/facade/EpubCoreProvider.kt")

    @Test
    fun `释放入口必须受判据把关且无持有时不动作`() {
        val s = provider()
        assertTrue("必须用判据把关（否则任何 level 都拆会话）", s.contains("EpubCoreMemoryTrimPolicy.shouldRelease(level)"))
        assertTrue("无持有（holder 为 null）时必须直接返回，不伪造动作", s.contains("val current = holder ?: return false"))
        assertTrue("必须真调用门面的释放入口", s.contains("current.facade.releaseForMemoryPressure()"))
        assertTrue("必须留痕（真机 L2 凭此取证）", s.contains("EPUB 阅读面内存释放"))
    }

    @Test
    fun `释放只动可重建资源不拆前台不整书关闭`() {
        val s = facade()
        val body = s.substringAfter("fun releaseForMemoryPressure(): Int {").substringBefore("\n    }")
        assertTrue("必须关闭背景布局会话", body.contains("closeBackgroundLayoutSessions()"))
        assertTrue("必须清图片内存缓存", body.contains("imageResolver.clear()"))
        assertTrue("必须清字体内存缓存", body.contains("typefaceResolver?.clear()"))
        assertFalse("不得拆前台会话（正在显示的页会被拆成空白）", body.contains("cancelForegroundLayout"))
        assertFalse("不得整书 close（会把正在读的书整个关掉）", body.contains("close()"))
    }

    @Test
    fun `背景会话上限被钉住为显式决策点`() {
        val s = facade()
        assertTrue(
            "上限常量必须显式命名（便于按台账决策）",
            s.contains("MaxBackgroundWebLayoutSessions")
        )
        assertEquals(
            "背景 WebView 会话上限现值为 5（≠ 设计文中的 2）：见 tasks.md S10 条 AOAdapt —— " +
                "`slot % cap` 复用语义下降到 2 会让预取章节逐个重建 WebView（性能回退），" +
                "要改必须先有实测数据并同步台账，故此处钉住现值防静默改动",
            5,
            Regex("private const val MaxBackgroundWebLayoutSessions = (\\d+)")
                .find(s)?.groupValues?.get(1)?.toInt()
        )
    }
}