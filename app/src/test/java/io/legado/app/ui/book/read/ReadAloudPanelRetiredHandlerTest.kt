package io.legado.app.ui.book.read

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B19：`ReadAloudPlayerPanel` 内零调用处理函数退役守护。
 *
 * 缺陷背景（三档分诊结论）：
 * - `setSpeechRate` / `setFollowSystemSpeechRate`：`AppConfig.ttsSpeechRate`/`ttsFlowSys` 存在**活写入方**
 *   （`TtsKernel.kt:132-133`、`ReadAloudDialog.kt:166/363`、`ReadAloudConfigDialog` 滑杆）⇒ **被取代**；
 * - `closeFromAction`：与相邻内联块语义等价（`dismissedForCurrentRun = isRun`）⇒ **重构残留**；
 * - `nearbyCueParagraphs`：与活兄弟 `[TextParagraph].nearbyParagraphs` 逐字同构 ⇒ **旧变体残留**。
 * 本类固化退役结果，并守护活兄弟不被误删。
 */
class ReadAloudPanelRetiredHandlerTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `面板内被取代或重复的处理函数已退役且活兄弟仍在`() {
        val src = code("src/main/java/io/legado/app/ui/book/read/ReadAloudPlayerPanel.kt")
        assertEquals("被取代/重复残留应退役", emptyList<String>(),
            listOf("closeFromAction", "setSpeechRate", "setFollowSystemSpeechRate", "nearbyCueParagraphs")
                .filter { src.contains("fun $it(") })
        assertEquals("活兄弟 nearbyParagraphs 必须保留", true,
            src.contains("fun List<TextParagraph>.nearbyParagraphs("))
        assertEquals("Compose 宿主入口必须上提 LegadoTheme 根作用域（G-37 / K1 / AD-01）", true,
            src.contains("LegadoTheme {"))
    }
}
