package io.legado.app.ui.main.bookshelf

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

/**
 * 2026-10-17 · **书架配置弹窗存量超限拆分**的结构不变量（G-38 登记项的落地）。
 *
 * 背景：`BookshelfConfigDialog.kt` 曾 **1121 行**（阈值 800；allowlist 上限 1150），把「宿主 Fragment +
 * 取值模型 + 内容/面板骨架 + 选项族 + 展示族」全聚在一处。现按**形态**拆为 3 个**同包**文件
 * （同包 ⇒ 跨文件引用无需 import ⇒ **零调用点改动**）；被跨文件引用的原 `private` 顶层声明
 * （含 `private data class`）自动提为 `internal`。
 *
 * 本用例锁死：①各文件职责归属；②**不得双份定义**（防拆完又抄回去）；③各文件 ≤800 行。
 */
class BookshelfConfigDialogSplitTest {

    private val files = listOf(
        "ui/main/bookshelf/BookshelfConfigDialog.kt",
        "ui/main/bookshelf/BookshelfConfigChoiceParts.kt",
        "ui/main/bookshelf/BookshelfConfigDisplayParts.kt",
    )

    /** 文件 → 必须包含的声明（按观察到的可见性前缀断言，防止可见性被改回 private 导致编译面收窄）。 */
    private val expects = mapOf(
        "ui/main/bookshelf/BookshelfConfigDialog.kt" to listOf(
            "class BookshelfConfigDialog : ComposeDialogFragment()",
            "data class BookshelfConfigValues(",
            "internal data class BookshelfSelectItem(",
            "internal data class BookshelfSwitchItem(",
            "private fun BookshelfConfigContent(",
            "private fun BookshelfConfigPanel(",
        ),
        "ui/main/bookshelf/BookshelfConfigChoiceParts.kt" to listOf(
            "internal fun BookshelfOptionGrid(",
            "private fun BookshelfSelectTile(",
            "private fun BookshelfChoicePopupPanel(",
            "private fun BookshelfChoiceChip(",
        ),
        "ui/main/bookshelf/BookshelfConfigDisplayParts.kt" to listOf(
            "internal fun BookshelfDisplaySummaryCard(",
            "private fun BookshelfSummaryChip(",
            "private fun BookshelfDisplayPopupPanel(",
            "private fun BookshelfDisplaySwitchRow(",
            "internal fun BookshelfSliderRow(",
            "internal fun BookshelfFooterActions(",
        ),
    )

    /** 全部顶层声明（应各自唯一归属一个文件）。 */
    private val declNames = listOf(
        "BookshelfConfigValues", "BookshelfConfigOption", "BookshelfConfigOptions", "BookshelfConfigTexts",
        "BookshelfPremiumSpec", "BookshelfSelectItem", "BookshelfSwitchItem", "BookshelfConfigDialog",
        "BookshelfConfigContent", "BookshelfConfigPanel", "ConfigSection",
        "BookshelfOptionGrid", "BookshelfSelectTile", "BookshelfChoicePopupPanel", "BookshelfChoiceChip",
        "BookshelfDisplaySummaryCard", "BookshelfSummaryChip", "BookshelfDisplayPopupPanel",
        "BookshelfDisplaySwitchRow", "BookshelfSliderRow", "BookshelfFooterActions",
    )

    @Test
    fun `职责归属正确`() {
        expects.forEach { (rel, wants) ->
            val src = SourceFileProbe.sourceText(rel)
            wants.forEach { w -> assertEquals("$rel 应含 $w", true, src.contains(w)) }
        }
    }

    @Test
    fun `顶层声明不得双份定义`() {
        val owners = mutableMapOf<String, MutableList<String>>()
        files.forEach { rel ->
            val src = SourceFileProbe.sourceText(rel)
            declNames.forEach { name ->
                if (Regex("""\b(class|object|interface) $name\b""").containsMatchIn(src) ||
                    Regex("""\bfun $name\(""").containsMatchIn(src)
                ) {
                    owners.getOrPut(name) { mutableListOf() }.add(rel)
                }
            }
        }
        val dup = owners.filterValues { it.size > 1 }
        assertEquals("同一顶层声明只允许一个文件持有：$dup", emptyMap<String, List<String>>(), dup)
        assertEquals("声明必须全部有归属（漏拆/漏登记）：${declNames - owners.keys}", declNames.size, owners.size)
    }

    @Test
    fun `拆分后各文件不超过800行`() {
        val root = SourceFileProbe.mainJavaRoot()
        val oversized = files.mapNotNull { rel ->
            val n = File(root, "io/legado/app/$rel").readLines().size
            if (n > 800) "$rel=$n" else null
        }
        assertEquals("拆分后仍超 800 行的文件：$oversized", emptyList<String>(), oversized)
    }
}
