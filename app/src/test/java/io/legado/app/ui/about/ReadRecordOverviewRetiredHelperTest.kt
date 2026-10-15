package io.legado.app.ui.about

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/** B21：`ReadRecordOverviewCard.composeReadRecordPanelRadius` 零调用 @Composable 助手退役守护。 */
class ReadRecordOverviewRetiredHelperTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `零调用圆角助手已连注解一并退役`() {
        val src = code("src/main/java/io/legado/app/ui/about/ReadRecordOverviewCard.kt")
        assertEquals("零调用 Composable 助手应退役", false, src.contains("composeReadRecordPanelRadius"))
        assertEquals("活 Composable ReadRecordDivider 必须保留", true,
            src.contains("fun ReadRecordDivider("))
    }
}
