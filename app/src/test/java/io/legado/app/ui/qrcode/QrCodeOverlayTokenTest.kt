package io.legado.app.ui.qrcode

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** B7 R28/F1-F3 扫码覆盖层取色不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。 */
class QrCodeOverlayTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/qrcode/QrCodeOverlay.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    /** 提示条/权限卡底必须走面 token（原取 M3 派生键 surface/surfaceVariant/outline ⇒ 卡面不跟随主题）。 */
    @Test
    fun cardSurfacesUseFaceTokens() {
        val t = code()
        assertTrue("提示条/卡底应走 cardColor", t.contains("cardColor"))
        assertTrue("未选按钮底应走 tabBackgroundColor", t.contains("tabBackgroundColor"))
        assertTrue("描边应走 dividerColor", t.contains("dividerColor"))
        assertFalse("不得再用 colorScheme.surface", t.contains("colorScheme.surface"))
        assertFalse("不得再用 colorScheme.surfaceVariant", t.contains("colorScheme.surfaceVariant"))
        assertFalse("不得再用 colorScheme.outline", t.contains("colorScheme.outline"))
    }
}