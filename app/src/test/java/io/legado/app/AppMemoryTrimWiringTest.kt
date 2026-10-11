package io.legado.app

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `App` 内存压力链路对**阅读面**的接线契约（epub-md-rich-rendering S10 配对）。
 *
 * 背景：`App.trimAppMemory` 早已联动清理 WebViewPool / CacheManager / ImageProvider / Glide，
 * 但**阅读面自己的离屏 WebView 会话不在其中**（那是阅读链路最大的内存头，单实例 20~50MB）
 * ⇒ 低内存下阅读页照样被系统杀掉。本批把它纳入同一条链路；本测试钉住该接线，
 * 防止后续重构把这一行悄悄摘掉（症状是"低内存被杀"这种**很晚才被发现**的问题）。
 */
class AppMemoryTrimWiringTest {

    private fun app(): String = SourceFileProbe.sourceText("App.kt")

    @Test
    fun `内存压力链路必须覆盖阅读面释放`() {
        val s = app()
        assertTrue(
            "trimAppMemory 必须调用 EpubCoreProvider.onMemoryPressure(level)",
            s.contains("EpubCoreProvider.onMemoryPressure(level)")
        )
        assertTrue(
            "必须导入阅读面提供者（否则调用无从谈起）",
            s.contains("import io.legado.app.model.localBook.epubcore.facade.EpubCoreProvider")
        )
    }

    @Test
    fun `阅读面释放必须与既有内存清理同处一条链路`() {
        val s = app()
        val body = s.substringAfter("private fun trimAppMemory(level: Int) {")
            .substringBefore("\n    }")
        assertTrue("阅读面释放必须在 trimAppMemory 内", body.contains("EpubCoreProvider.onMemoryPressure(level)"))
        assertTrue(
            "不得挤掉既有清理（WebViewPool/CacheManager 仍在同一链路）",
            body.contains("WebViewPool.trimMemory()") && body.contains("CacheManager.trimMemory(level)")
        )
        assertTrue(
            "且外套 runCatching（内存压力路径绝不允许因单个清理器抛错而中断其余清理）",
            s.substringAfter("private fun trimAppMemory(level: Int) {").contains("runCatching")
        )
    }
}