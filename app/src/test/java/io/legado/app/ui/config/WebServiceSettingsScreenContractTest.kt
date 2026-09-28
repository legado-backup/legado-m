package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「Web 服务与 AI 接入」页的**真机缺陷防回归**（2026-09-29 实测沉淀，详见 `../issues-found.md`）。
 *
 * 为何用源码不变量：这两条都是"渲染出来才看得见"的视觉缺陷（按钮与卡面同色 / 重复文案），
 * 单测无法覆盖像素，但**成因是取色与文案的接线错误**，可用源码断言精确锁死。
 */
class WebServiceSettingsScreenContractTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val screen by lazy {
        read("src/main/java/io/legado/app/ui/config/WebServiceSettingsScreen.kt")
    }
    private val strings by lazy { read("src/main/res/values/strings.xml") }
    private val stringsZh by lazy { read("src/main/res/values-zh/strings.xml") }

    @Test
    fun secondaryButtonFaceIsNotTheCardFace() {
        // IF-01：卡面上的次级按钮若沿用 miuix.surfaceVariant（= colors.row，与卡面同色）会完全不可见；
        // 换 rowPressed 亦无效（不透明主题下二者同值）⇒ 终版必须用与卡面必然异值的面 token。
        assertTrue(
            "次级按钮底须换成页面面（与卡面 row 必然异值）",
            screen.contains("palette.miuix.copy(surfaceVariant = palette.settings.page)")
        )
        assertFalse(
            "不得回退到 rowPressed（layoutAlpha=1 时与 row 同值 ⇒ 按钮仍不可见）",
            screen.contains("surfaceVariant = Color(palette.settings.rowPressed)")
        )
    }

    @Test
    fun offStateAddressCardDoesNotRepeatSameText() {
        // IF-02：未开启时标题与副标题不得复用同一句文案
        assertTrue(
            "未开启时副标题须给可操作提示（独立文案键）",
            screen.contains("R.string.web_address_hint_when_off")
        )
        listOf(strings, stringsZh).forEach { file ->
            assertTrue("文案键须存在于两份 strings", file.contains("""name="web_address_hint_when_off""""))
        }
    }

    @Test
    fun secondaryButtonsAllUseTheActionPalette() {
        // 所有非主按钮都必须走 actionPalette；漏传会静默退回不可见的 miuix.surfaceVariant
        val buttonCalls = Regex("""LegadoMiuixActionButton\(""").findAll(screen).count()
        val paletteArgs = Regex("""palette = buttons,""").findAll(screen).count()
        assertTrue("本页按钮数应 ≥ 5（地址 1 / 令牌 3 / 引导 4）", buttonCalls >= 5)
        assertTrue(
            "每个按钮都须用 actionPalette（实际 $paletteArgs / $buttonCalls）",
            paletteArgs >= buttonCalls
        )
    }
}
