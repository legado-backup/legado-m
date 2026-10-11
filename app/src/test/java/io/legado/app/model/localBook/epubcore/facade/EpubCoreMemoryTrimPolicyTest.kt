package io.legado.app.model.localBook.epubcore.facade

import android.content.ComponentCallbacks2
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读面内存压力释放**判据**（epub-md-rich-rendering S10 配对）。
 *
 * 判据本身要防两类错：
 * ①**漏释放**（压力信号已到却不动作 ⇒ 离屏 WebView 继续占 20~50MB/个，进程容易被系统杀掉）；
 * ②**过度释放**（没有压力信号也拆会话 ⇒ WebView 反复重建，翻页明显变慢）。
 */
class EpubCoreMemoryTrimPolicyTest {

    @Test
    fun `各级内存压力信号均触发释放`() {
        val levels = mapOf(
            "RUNNING_MODERATE" to ComponentCallbacks2.TRIM_MEMORY_RUNNING_MODERATE,
            "RUNNING_LOW" to ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW,
            "RUNNING_CRITICAL" to ComponentCallbacks2.TRIM_MEMORY_RUNNING_CRITICAL,
            "UI_HIDDEN" to ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN,
            "BACKGROUND" to ComponentCallbacks2.TRIM_MEMORY_BACKGROUND,
            "MODERATE" to ComponentCallbacks2.TRIM_MEMORY_MODERATE,
            "COMPLETE" to ComponentCallbacks2.TRIM_MEMORY_COMPLETE
        )
        levels.forEach { (name, level) ->
            assertTrue("$name($level) 必须触发释放", EpubCoreMemoryTrimPolicy.shouldRelease(level))
        }
    }

    @Test
    fun `低于最低压力信号不释放（避免无谓重建）`() {
        // 最低的"系统给出压力提示"档是 RUNNING_MODERATE；其下都不该动作
        val lowest = ComponentCallbacks2.TRIM_MEMORY_RUNNING_MODERATE
        assertFalse("低于最低档不得释放", EpubCoreMemoryTrimPolicy.shouldRelease(lowest - 1))
        assertFalse("0 不得释放", EpubCoreMemoryTrimPolicy.shouldRelease(0))
        assertFalse("负值不得释放", EpubCoreMemoryTrimPolicy.shouldRelease(-1))
        assertTrue("恰好等于最低档必须释放（边界）", EpubCoreMemoryTrimPolicy.shouldRelease(lowest))
    }

    @Test
    fun `阅读页不可见时同样释放（后台不占离屏 WebView）`() {
        assertTrue(
            "UI_HIDDEN 时阅读页已不可见 ⇒ 预取会话应释放",
            EpubCoreMemoryTrimPolicy.shouldRelease(ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN)
        )
    }
}