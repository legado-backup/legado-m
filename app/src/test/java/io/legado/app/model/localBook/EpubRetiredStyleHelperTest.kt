package io.legado.app.model.localBook

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B17：EPUB 旧计算样式助手退役守护。
 *
 * 缺陷背景：`EpubBoxBuilder.extractBackgroundRepeat/extractBackgroundSize` 与
 * `EpubLayoutEngine.inlinePadding/inlineBackgroundRadius` 经 `audit_dead_private_fun.py`
 * 判定为 `private` 作用域内零调用（不可达），人工核实为「被新实现取代」的旧助手：
 * - `inlinePadding` 仅转调仍存活的 `boxPadding`（重命名残留）；
 * - `inlineBackgroundRadius` 被 `EpubBorderRadius` 富实现取代；
 * - 两个背景简写助手被现行背景解析取代。
 * 本类固化退役结果，并守护活实现不被误删。
 */
class EpubRetiredStyleHelperTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `旧计算样式助手退役且活实现仍在`() {
        val box = code("src/main/java/io/legado/app/model/localBook/EpubBoxBuilder.kt")
        assertEquals("旧背景简写助手应退役", emptyList<String>(),
            listOf("extractBackgroundRepeat", "extractBackgroundSize")
                .filter { box.contains("fun $it(") })

        val layout = code("src/main/java/io/legado/app/model/localBook/EpubLayoutEngine.kt")
        assertEquals("旧内联样式助手应退役", emptyList<String>(),
            listOf("inlinePadding", "inlineBackgroundRadius")
                .filter { layout.contains("fun $it(") })
        assertEquals("活实现 boxPadding 必须保留", true,
            layout.contains("fun EpubComputedStyle.boxPadding("))
    }
}
