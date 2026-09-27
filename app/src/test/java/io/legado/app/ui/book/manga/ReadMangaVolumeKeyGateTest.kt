package io.legado.app.ui.book.manga

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.3 / REQ-22：漫画页音量键翻页的**开关门禁**不变量。
 *
 * 关键点：关闭时必须在 `when` 之前 `return super.onKeyDown(...)` —— 既不消费事件（交回系统调音量），
 * 也不误判为翻页；若只把分支体清空而仍 `return true`，音量键会被静默吞掉。
 */
class ReadMangaVolumeKeyGateTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val activity by lazy {
        read("src/main/java/io/legado/app/ui/book/manga/ReadMangaActivity.kt")
    }

    private val onKeyDown by lazy {
        val start = activity.indexOf("override fun onKeyDown(")
        val end = activity.indexOf("override fun updateEepaper(", start)
        if (start > 0 && end > start) activity.substring(start, end) else activity
    }

    @Test
    fun gateReadsGlobalSwitchBeforeConsumingKey() {
        val gate = onKeyDown.indexOf("if (!AppConfig.mangaVolumeKeyPage)")
        val whenBlock = onKeyDown.indexOf("when (keyCode)")
        assertTrue("须读全局开关", gate > 0)
        assertTrue("门禁须在 when 之前（先判后消费）", gate in 1 until whenBlock)
    }

    @Test
    fun gateDelegatesToSuperSoSystemKeepsVolumeControl() {
        val gate = onKeyDown.indexOf("if (!AppConfig.mangaVolumeKeyPage)")
        val delegate = onKeyDown.indexOf("return super.onKeyDown(keyCode, event)", gate)
        assertTrue("关闭时须交回系统", delegate > gate)
    }

    @Test
    fun bothVolumeDirectionsStillMappedWhenEnabled() {
        assertTrue("音量上须翻上一页", onKeyDown.contains("KeyEvent.KEYCODE_VOLUME_UP"))
        assertTrue("音量下须翻下一页", onKeyDown.contains("KeyEvent.KEYCODE_VOLUME_DOWN"))
        assertTrue("翻页须消费事件", onKeyDown.contains("return true"))
    }
}