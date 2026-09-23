package io.legado.app.ui.book.audio

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B7 余项 · 听书页（豁免页）View 侧主题刷新的配对不变量（源码级）。
 *
 * 为什么单独守：本页 `recreateOnThemeChange=false`（沉浸页不重建，避免打断播放），
 * 主题变更只能靠 `EventBus.RECREATE` **原位**刷新；而歌词时间轴字色取自 `accentColor`
 * （View 侧 `LyricViewX`）⇒ 一旦有人删掉该订阅或那句重设，主题切换后字色会静默停留旧主题
 * （无异常、无日志，肉眼也易被"看起来差不多"掩盖）。
 *
 * 该页为 Activity（依赖 AudioPlay 服务/媒体栈），JVM 侧无法低成本真起实例，
 * 故沿用项目既有做法（`HighlightDrawFontRestoreTest`）用源码不变量固化接线。
 */
class AudioPlayThemeInPlaceTest {

    private fun source(): String {
        val rel = "src/main/java/io/legado/app/ui/book/audio/AudioPlayActivity.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readText()
    }

    @Test
    fun recreateEventRefreshesLyricThemeInPlace() {
        val code = source()
        val observeBlock = code.substringAfter("override fun observeLiveBus()")
        assertTrue(
            "observeLiveBus 必须订阅 EventBus.RECREATE",
            observeBlock.contains("observeEvent<String>(EventBus.RECREATE)")
        )
        val recreateHandler = observeBlock
            .substringAfter("observeEvent<String>(EventBus.RECREATE)")
            .substringBefore("observeEvent<Boolean>(EventBus.MEDIA_BUTTON)")
        assertTrue(
            "RECREATE 处理内必须调用 refreshLyricThemeInPlace()",
            recreateHandler.contains("refreshLyricThemeInPlace()")
        )
    }

    @Test
    fun refreshReappliesTimelineTextColor() {
        val body = source()
            .substringAfter("private fun refreshLyricThemeInPlace()")
            .substringBefore("\n    }")
        assertTrue(
            "必须重设歌词时间轴字色（取自 accentColor）",
            body.contains("setTimelineTextColor(accentColor)")
        )
        assertTrue("歌词未加载时无需处理，必须有 lyricOn 守卫", body.contains("if (lyricOn)"))
    }

    /** 原「核实结论」注释已失实，不得回退（B7 修正注释里会引用该结论作为反例，故按整句判定）。 */
    @Test
    fun staleNoViewSideColorCommentMustNotReturn() {
        assertFalse(
            "「T3 核实：本页无 View 侧主题色消费，豁免+ThemeSync 覆盖完整」与实现矛盾" +
                "（歌词时间轴字色即 View 侧主题色），禁止回退该核实结论",
            source().contains("核实：本页无 View 侧主题色消费，豁免+ThemeSync 覆盖完整")
        )
    }
}
