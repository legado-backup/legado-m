package io.legado.app.lib.theme

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-89：`ShapeSelector`「已显式设置」标记的**赶工型缺陷**修复守护。
 *
 * 缺陷（此前未发现，源码级铁证）：
 * ① `hasSetFocusedBgColor` 被声明为 **`val`**（其余 4 个兄弟标记 `hasSetDisabledBgColor` /
 *    `hasSetPressedBgColor` / `hasSetSelectedBgColor` / `hasSetCheckedBgColor` 均为 `var`）⇒ **恒 false**；
 * ② `setFocusedBgColor` 体内误置 `hasSetPressedBgColor`（复制粘贴）⇒ 聚焦态标记**永不可能为真**；
 * 二者叠加使 `setDefaultBgColor` 的「已显式设置则不覆盖」保护**对聚焦态失效**（并令 `build()` 中
 * `if (hasSetFocusedBgColor || …)` 恒只取决于 stroke 标记）。
 *
 * 运行时影响：**本轮为零**（`setFocusedBgColor` 全仓零调用点）⇒ 属结构性正确性修复，非行为变更。
 * 本用例锁定修复结果（`var` + 置正确标记），防止复制粘贴再次回流。
 */
class SelectorFlagCorrectnessTest {

    private val src by lazy { SourceFileProbe.sourceText("lib/theme/Selector.kt") }

    /** `setFocusedBgColor` 的函数体（从签名到该函数收尾括号）。 */
    private val focusedBody: String by lazy {
        Regex("fun setFocusedBgColor\\([\\s\\S]*?\\n        }").find(src)?.value.orEmpty()
    }

    @Test
    fun `聚焦态已设置标记必须是可变 var`() {
        assertEquals(
            "hasSetFocusedBgColor 须声明为 var（否则恒 false）", true,
            src.contains("private var hasSetFocusedBgColor = false")
        )
        assertEquals(
            "不得残留 val 声明", false,
            src.contains("private val hasSetFocusedBgColor")
        )
    }

    @Test
    fun `setFocusedBgColor 必须置正确标记`() {
        assertEquals("须能取到函数体", true, focusedBody.isNotEmpty())
        assertEquals(
            "须置 hasSetFocusedBgColor", true,
            focusedBody.contains("hasSetFocusedBgColor = true")
        )
        assertEquals(
            "不得误置兄弟标记 hasSetPressedBgColor", false,
            focusedBody.contains("hasSetPressedBgColor = true")
        )
    }
}
