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

    @Test
    fun `NEW-86 零引用被取代判据退役且活实现仍在`() {
        // 分诊结论（audit_zero_ref_fun + 全仓 grep 交叉）：两条「零引用 + 有活替代」判据 ⇒ 已删。
        // ⚠️ 本断言守护的是「死判据不得回流」，同时守住活实现不被误删。
        val compat =
            code("src/main/java/io/legado/app/model/localBook/epubcore/style/EpubCssCompat.kt")
        assertEquals(
            "被取代的 isRenderable 应退役（活替代 = resolvePropertyName 归一+判定一步到位）",
            false,
            compat.contains("fun isRenderable(")
        )
        assertEquals("活实现 resolvePropertyName 必须保留", true, compat.contains("fun resolvePropertyName("))

        val dom = code("src/main/java/io/legado/app/model/localBook/EpubDom.kt")
        assertEquals(
            "被取代的 withoutInheritedTextIndent 应退役（活替代 = inheritedOnly）",
            false,
            dom.contains("fun withoutInheritedTextIndent(")
        )
        assertEquals("活实现 inheritedOnly 必须保留", true, dom.contains("fun inheritedOnly("))
    }
}
