package io.legado.app.ui.book.read

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 阅读页搜索菜单「底部菜单背景」单源化守护。
 *
 * 缺陷背景（重复实现）：`SearchMenu.refreshUI()` 曾**内联手抄**了 `ReaderSheetStyle.blockDrawable`
 * 的逐字等价体（`cornerRadius = UiCorner.scaledDp(radius)` + `setColor(fill)` + `setStroke(1.dpToPx(), stroke)`），
 * 而该 helper 本身**全仓零引用** ⇒ 同一口径两处手抄，任一处改动即静默分叉。
 *
 * 本类守护：①内联手抄改走单源 helper；②手抄体不得回流；③单源 helper 必须保留且语义不变。
 */
class SearchMenuTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val main = "src/main/java/io/legado/app/ui/book/"

    @Test
    fun `底部菜单背景已走单源 helper`() {
        val src = code(main + "read/SearchMenu.kt")
        assertEquals("须引用单源 helper", true, src.contains("ReaderSheetStyle.blockDrawable("))
        assertEquals("内联手抄的角半径不得回流", false, src.contains("cornerRadius = UiCorner.scaledDp(18F)"))
    }

    @Test
    fun `单源 helper 保留且语义不变`() {
        val sheet = code(main + "read/config/ReaderSheetStyle.kt")
        assertEquals("blockDrawable 必须保留", true, sheet.contains("fun blockDrawable("))
        assertEquals("角半径按 UiCorner 缩放口径保留", true, sheet.contains("cornerRadius = UiCorner.scaledDp(radiusDp)"))
        assertEquals("描边口径保留", true, sheet.contains("setStroke(1.dpToPx(), strokeColor)"))
    }
}
