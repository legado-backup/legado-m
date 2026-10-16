package io.legado.app.lib.theme

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * `UiCorner` 死 drawable 构造器退役守护。
 *
 * `panelRoundedStroke` 全仓零引用；其依赖的活体构造器 `roundedStroke` / `strokeOnly` /
 * `panelImageDrawable` / `applyPanelBorderAlpha` 仍在活路径（`panelRounded`、`panelInsetStrokeDrawable`
 * 与多处 Compose 宿主使用）。本类守护「死构造器不得回流」与「活体不得被误删」。
 */
class UiCornerTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    private val src by lazy { code("src/main/java/io/legado/app/lib/theme/UiCorner.kt") }

    @Test
    fun `panelRoundedStroke 已退役`() {
        assertEquals(
            "死 drawable 构造器 panelRoundedStroke 应退役",
            false,
            src.contains("fun panelRoundedStroke(")
        )
    }

    @Test
    fun `活体构造器必须保留`() {
        listOf(
            "fun panelInsetStrokeDrawable(",
            "fun panelRounded(",
            "fun roundedStroke(",
            "fun strokeOnly("
        ).forEach { sig ->
            assertEquals("活体 $sig 必须保留", true, src.contains(sig))
        }
    }
}
