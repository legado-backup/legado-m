package io.legado.app.ui.widget.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

/**
 * 2026-10-17 · **Compose 弹层族存量超限拆分**的结构不变量（G-38 登记的独立重构项落地）。
 *
 * 背景：`AppComposeDialogs.kt` 曾 **2462 行**（阈值 800 的 3 倍，allowlist 上限 2500），聚合了
 * 框架 + 样式 + 共享字段助手 + 全部弹层内容体。现按「弹层形态」拆为 7 个**同包**文件
 * （同包 ⇒ 跨文件引用无需 import ⇒ **零调用点改动**）。
 *
 * 本用例锁死三件事（防「拆完又被合回去」或「复制粘贴双份」）：
 *  ①框架/样式/共享字段助手**必须留在** `AppComposeDialogs.kt`（对外 API 面不动）；
 *  ②六个弹层体**必须各自在新家**，且**不得**同时残留在聚合文件里（防双份定义）；
 *  ③各文件行数 ≤800（G-38 阈值口径；拆分后仍超额即白拆）。
 */
class AppComposeDialogsSplitTest {

    /** keep 文件（框架 + 样式 + 共享助手）与各自应含的弹层类。 */
    private val layout = mapOf(
        "ui/widget/compose/AppComposeDialogs.kt" to listOf(
            "fun AppDialogFrame(", "fun rememberAppDialogStyle(", "data class AppDialogStyle(",
            "internal fun DismissWhenCallbackMissing(", "internal fun AppDialogTextField(",
        ),
        "ui/widget/compose/AppComposeTextDialogs.kt" to listOf(
            "class ComposeTextInputDialog", "class ComposeSuggestionTextInputDialog",
            "class ComposeTextFormDialog",
        ),
        "ui/widget/compose/AppComposeTemplateDialogs.kt" to listOf("class ComposeTipTemplateDialog"),
        "ui/widget/compose/AppComposePickerDialogs.kt" to listOf("class ComposeNumberPickerDialog"),
        "ui/widget/compose/AppComposeChoiceDialogs.kt" to listOf(
            "class ComposeMultiChoiceDialog", "class ComposeSingleChoiceDialog",
            "class ComposeActionListDialog",
        ),
        "ui/widget/compose/AppComposeConfirmDialogs.kt" to listOf(
            "class ComposeConfirmDialog", "class ComposeFetchedModelDialog",
        ),
        "ui/widget/compose/AppComposeDialogRows.kt" to listOf("fun AppDialogSwitchRow("),
    )

    /** 全部弹层类（应各自唯一归属一个文件）。 */
    private val dialogClasses = listOf(
        "ComposeTextInputDialog", "ComposeSuggestionTextInputDialog", "ComposeTextFormDialog",
        "ComposeTipTemplateDialog", "ComposeNumberPickerDialog", "ComposeMultiChoiceDialog",
        "ComposeSingleChoiceDialog", "ComposeActionListDialog", "ComposeConfirmDialog",
        "ComposeFetchedModelDialog",
    )

    @Test
    fun `框架与共享助手留在原文件且弹层体各自在新家`() {
        layout.forEach { (rel, expects) ->
            val src = SourceFileProbe.sourceText(rel)
            expects.forEach { e ->
                assertEquals("$rel 应含 $e", true, src.contains(e))
            }
        }
    }

    @Test
    fun `弹层类不得双份定义（防拆完又抄回去）`() {
        val owners = mutableMapOf<String, MutableList<String>>()
        layout.keys.forEach { rel ->
            val src = SourceFileProbe.sourceText(rel)
            dialogClasses.forEach { cls ->
                if (src.contains("class $cls")) owners.getOrPut(cls) { mutableListOf() }.add(rel)
            }
        }
        val dup = owners.filterValues { it.size > 1 }
        assertEquals("同一弹层类只允许一个文件声明：$dup", emptyMap<String, List<String>>(), dup)
        assertEquals("弹层类必须全部有归属（漏拆/漏登记）：${dialogClasses - owners.keys}", dialogClasses.size, owners.size)
    }

    @Test
    fun `拆分后各文件不超过800行`() {
        val root = SourceFileProbe.mainJavaRoot()
        val oversized = layout.keys.mapNotNull { rel ->
            val f = File(root, "io/legado/app/$rel")
            val n = f.readLines().size
            if (n > 800) "$rel=$n" else null
        }
        assertEquals("拆分后仍超 800 行的文件：$oversized", emptyList<String>(), oversized)
    }
}
