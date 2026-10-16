package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 阅读页底部面板「窗口设置单源化」守护。
 *
 * 缺陷背景（重复实现）：`ReaderBottomSheetComposeDialogFragment.onStart()` 曾**内联复制**了
 * `Window.applyReaderBottomSheetWindow` 的整段窗口设置（清 dim 标记 / 透明背景 / 去 decor padding /
 * `dimAmount=0` / `gravity=BOTTOM` /墨水屏零动画 / `setLayout(MATCH_PARENT, WRAP_CONTENT)`），
 * 而该扩展函数本身**全仓零引用** ⇒ 同一口径两处手抄，任一处改动即静默分叉。
 *
 * 本类守护：①基类改调单源扩展；②内联复制不得回流；③单源扩展必须存在（不得被误删）。
 */
class ReaderComposeComponentsTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val main = "src/main/java/io/legado/app/ui/book/read/config/"

    @Test
    fun `底部面板窗口设置已单源化`() {
        val components = code(main + "ReaderComposeComponents.kt")
        assertEquals(
            "基类 onStart 必须调用单源扩展",
            true,
            components.contains("dialog?.window?.applyReaderBottomSheetWindow()")
        )
        assertEquals(
            "内联复制的重力设置不得回流",
            false,
            components.contains("attr.gravity = Gravity.BOTTOM")
        )
    }

    @Test
    fun `单源扩展仍须存在且保持原语义`() {
        val window = code(main + "ReaderDialogWindow.kt")
        assertEquals("单源扩展必须保留", true, window.contains("fun Window.applyReaderBottomSheetWindow("))
        assertEquals("墨水屏零动画口径必须保留", true, window.contains("attr.windowAnimations = if (AppConfig.isEInkMode) 0"))
        assertEquals("底部重力口径必须保留", true, window.contains("attr.gravity = Gravity.BOTTOM"))
    }
}
