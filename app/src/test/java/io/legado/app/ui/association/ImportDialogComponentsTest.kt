package io.legado.app.ui.association

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 导入弹窗「旧公共行组件」整族退役守护。
 *
 * 缺陷背景：`ImportDialogComponents.kt` 的 `ImportSourceItemRow` KDoc 自称
 * 「Common source item row used by all import dialogs」，但实际**全仓零消费者** ——
 * 8 个导入弹窗（书源/RSS/主题/净化规则/HttpTTS/TXT目录规则/替换规则/红主题）**全部**改用
 * `ui/widget/components/ImportSourceSheet`（含 `ImportItem` 数据类）作为**活的单一数据源**
 * ⇒ 该行组件是「早期抽取尝试」的**被取代残留**（KDoc 口径已过时）。
 *
 * 本类守护：①退役组件不得回流；②活单源 `ImportSourceSheet` 必须保留且仍被导入弹窗成规模消费。
 */
class ImportDialogComponentsTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val main = "src/main/java/io/legado/app/ui/association/"

    private fun dirText(): String {
        val dir = listOf(File(main), File("../app/$main"), File("app/$main")).first { it.isDirectory }
        return dir.listFiles { f -> f.extension == "kt" }!!.joinToString("\n") { it.readText() }
    }

    @Test
    fun `旧公共行组件已退役`() {
        assertEquals("退役组件不得回流", false, dirText().contains("fun ImportSourceItemRow("))
    }

    @Test
    fun `活单源 ImportSourceSheet 必须保留`() {
        val sheet = code("src/main/java/io/legado/app/ui/widget/components/ImportSourceSheet.kt")
        assertEquals("活单源组件必须保留", true, sheet.contains("fun ImportSourceSheet("))
        assertEquals("活单源数据类必须保留", true, sheet.contains("data class ImportItem("))
    }

    @Test
    fun `导入弹窗成规模消费活单源`() {
        val count = Regex("import io\\.legado\\.app\\.ui\\.widget\\.components\\.ImportSourceSheet")
            .findAll(dirText()).count()
        assertEquals("至少 6 个导入弹窗须消费活单源（防退回各自内联）", true, count >= 6)
    }
}
