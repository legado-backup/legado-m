package io.legado.app.model.localBook.epubcore.template

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `ReaderTemplateHostDocument` 死诊断脚本退役守护。
 *
 * `sandboxProbeScript`（沙箱就绪探针）全仓零引用；活体 `skeletonScript` / `containerSizeScript`
 * 在 [io.legado.app.ui.book.read.textweb.TemplateRenderBackend] 活路径。本类用**行为断言**
 * （直接调用活体脚本工厂并校验其输出）守护活体不被误删，同时守护死诊断脚本不得回流。
 */
class ReaderTemplateHostDocumentTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `sandboxProbeScript 已退役`() {
        val src = code("src/main/java/io/legado/app/model/localBook/epubcore/template/ReaderTemplateHostDocument.kt")
        assertEquals(
            "死诊断脚本 sandboxProbeScript 应退役",
            false,
            src.contains("fun sandboxProbeScript(")
        )
    }

    @Test
    fun `活体容器脚本行为不变`() {
        assertTrue("容器定尺寸脚本须回发 sized 自证", ReaderTemplateHostDocument.containerSizeScript().contains("sized|"))
        assertTrue("骨架隐藏脚本须输出 display='none'", ReaderTemplateHostDocument.skeletonScript(false).contains("display='none'"))
        assertTrue("骨架显示脚本须输出 display='block'", ReaderTemplateHostDocument.skeletonScript(true).contains("display='block'"))
    }
}
