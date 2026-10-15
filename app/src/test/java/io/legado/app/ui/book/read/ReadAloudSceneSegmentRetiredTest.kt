package io.legado.app.ui.book.read

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B24：`ReadAloudPlayerPanel.buildSceneSegments` 被取代分支退役守护。
 *
 * 证据：同文件 `SceneSegmentUi(` 另有 4 处**活构造点**（Scene 段渲染走这些路径）⇒
 * 零调用的 `buildSceneSegments` 属冗余生产变体（被取代），退役。
 */
class ReadAloudSceneSegmentRetiredTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `被取代的场景段生产者已退役且活构造点仍在`() {
        val src = code("src/main/java/io/legado/app/ui/book/read/ReadAloudPlayerPanel.kt")
        assertEquals("被取代的场景段生产者应退役", false, src.contains("fun buildSceneSegments("))
        assertEquals("SceneSegmentUi 活构造点仍须存在（Scene 渲染链）", true,
            src.contains("SceneSegmentUi("))
    }
}
