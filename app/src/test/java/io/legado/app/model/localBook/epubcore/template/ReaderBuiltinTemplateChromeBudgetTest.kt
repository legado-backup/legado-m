package io.legado.app.model.localBook.epubcore.template

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 模板页眉/页脚"装饰带"高度预算单测（2026-10-13 用户真机铁证：开篇头/页脚过宽 ⇒ 正文区被压缩）。
 *
 * 为什么钉成机检契约：模板 CSS 里的 `vh` 装饰带（开篇图 / 天际线 / 波形页脚）与 em 内边距直接吃掉
 * 正文窗口高 —— 真机实测 `builtin.cyber-city` 开篇头 **239px（占页高 28%）**、`builtin.ink`/`builtin.star-chart`
 * 页脚 **80~83px**、左右正文内边距高达 **1.4~1.5em**，而参照阅读器（archive）同位置开篇头约 120~137px、
 * 页脚约 1.5em 字号 —— 前者把"头和尾太宽"（用户在需求阶段即明确要求**不要**复制该缺点）放大到极致。
 *
 * 判据 = 真机 re-measure（`l2_verify_template_page_frame.py --source sweep`）已验的收敛值必须被**源码钉住**，
 * 且不得回退到旧的大尺寸字面量（只写文档不写断言 ⇒ 下次改模板会静默复发）。
 */
class ReaderBuiltinTemplateChromeBudgetTest {

    private val assetsRoot = File("src/main/assets")

    private val reader = ReaderBuiltinTemplateCatalog.AssetReader { path ->
        val file = File(assetsRoot, path)
        if (file.isFile) file.readText() else null
    }

    private val loaded by lazy { ReaderBuiltinTemplateCatalog.load(reader) }

    private fun cssOf(id: String): String =
        loaded.templates.first { it.id == id }.template.css

    @Test
    fun `开篇页眉装饰带收敛到预算内`() {
        val cc = cssOf("builtin.cyber-city")
        assertTrue(".cc-sky 开篇头下留白须 ≤7vh", cc.contains("padding:.7em 1.05em 7vh"))
        assertTrue(".cc-sky::after 天际线带高须 ≤7vh", cc.contains("bottom:0;height:7vh"))
        assertTrue(".cc-city 书名须收敛到 1.6em", cc.contains("display:block;font-size:1.6em"))

        val ik = cssOf("builtin.ink")
        assertTrue(
            ".ik-title 开篇题签带高须 ≤7vh",
            ik.contains(".ik-title{position:relative;height:7vh;overflow:hidden;}")
        )

        val sc = cssOf("builtin.star-chart")
        assertTrue(".sc-band 基规则带高须 ≤7vh", sc.contains(".sc-band{position:relative;height:7vh;"))
        assertTrue(".sc-band 美术段覆盖规则同样须 ≤7vh", sc.contains(".sc-band{height:7vh;}"))

        val rn = cssOf("builtin.neon-night")
        assertTrue(".rn-art 开篇图高须 ≤3.2vh", rn.contains("height:3.2vh;color:var(--rn-accent);}"))
    }

    @Test
    fun `页脚装饰带与内边距收敛到预算内`() {
        val rn = cssOf("builtin.neon-night")
        assertTrue(
            ".rn-footmark 波形页脚须 ≤1.4vh",
            rn.contains(".rn-footmark{display:block;width:100%;height:1.4vh;color:var(--rn-accent);}")
        )
        assertTrue(
            ".rn-edge 边缘装饰须 ≤1.2vh",
            rn.contains(".rn-edge{display:block;width:100%;height:1.2vh;color:var(--rn-accent);}")
        )
        assertTrue(".rn-foot 上下内边距须收紧", rn.contains("padding:.4em 1.1em .5em;"))

        val ik = cssOf("builtin.ink")
        assertTrue(
            ".ik-footmark 边缘装饰须 ≤2vh",
            ik.contains(".ik-footmark{display:block;width:100%;height:2vh;color:var(--ik-line);}")
        )
        assertTrue(
            ".ik-edge 边缘装饰须 ≤1.6vh",
            ik.contains(".ik-edge{display:block;width:100%;height:1.6vh;color:var(--ik-line);}")
        )
        assertTrue(".ik-foot 上下内边距须收紧", ik.contains("padding:.45em 1.2em .6em"))

        val sc = cssOf("builtin.star-chart")
        assertTrue(
            ".sc-footmark 边缘装饰须 ≤2vh",
            sc.contains(".sc-footmark{display:block;width:100%;height:2vh;color:var(--sc-gold);}")
        )
        assertTrue(
            ".sc-edge 边缘装饰须 ≤1.6vh",
            sc.contains(".sc-edge{display:block;width:100%;height:1.6vh;color:var(--sc-gold);}")
        )
        assertTrue(".sc-foot 上下内边距须收紧", sc.contains("padding:.4em 1.2em .55em"))
    }

    @Test
    fun `左右正文内边距不得超过 1_2em`() {
        listOf("builtin.ink", "builtin.star-chart").forEach { id ->
            val css = cssOf(id)
            assertFalse(
                "$id 不得残留 1.5em/1.4em 级左右正文内边距（用户实测："左右留白偏大"）",
                css.contains("1.5em 0") || css.contains("1.4em 0")
            )
        }
        assertTrue(cssOf("builtin.ink").contains("padding:.8em 1.2em 0;"))
        assertTrue(cssOf("builtin.star-chart").contains("padding:.85em 1.2em 0;"))
    }

    @Test
    fun `不得回退到旧的大尺寸字面量`() {
        assertFalse(
            "builtin.cyber-city 不得回退 12vh 开篇天际线带",
            cssOf("builtin.cyber-city").contains("padding:1.2em 1.05em 12vh")
        )
        assertFalse("builtin.ink 不得回退 10vh 开篇题签", cssOf("builtin.ink").contains("height:10vh"))
        assertFalse(
            "builtin.star-chart 不得回退 10vh 美术段题带",
            cssOf("builtin.star-chart").contains(".sc-band{height:10vh;}")
        )
        assertFalse(
            "builtin.neon-night 不得回退 4.2vh 开篇图",
            cssOf("builtin.neon-night").contains("height:4.2vh")
        )
        assertFalse(
            "builtin.neon-night 不得回退 2vh 波形页脚",
            cssOf("builtin.neon-night").contains("height:2vh;color:var(--rn-accent);}")
        )
        assertFalse("builtin.ink 不得回退 3.2vh 页脚装饰", cssOf("builtin.ink").contains("height:3.2vh"))
        assertFalse(
            "builtin.star-chart 不得回退 3.2vh 页脚装饰",
            cssOf("builtin.star-chart").contains("height:3.2vh")
        )
    }
}
