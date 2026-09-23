package io.legado.app.ui.book.search

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 搜索页 chip 底口径不变量回归测试（B7 R28/D1，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 D1）：同语义「筛选 chip 未选中底」曾有三套口径 ——
 * Compose 侧 `AppFilterChip`（settings 行态）、本 View 侧（弱化底）、规范（chip 面 token）
 * ⇒ 换主题色后两栈分量不同。收敛后统一取 chip 面 token `tabBackgroundColor`。
 */
class SearchChipTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/search/SearchActivity.kt"
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        val f = candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return f.readLines()
            .filterNot {
                val t = it.trimStart()
                t.startsWith("*") || t.startsWith("//") || t.startsWith("/*")
            }
            .joinToString("\n")
    }

    /** 未选中 chip 底必须取 chip 面 token（与 Compose 侧同语义实现同 token）。 */
    @Test
    fun groupChip_idleBackgroundUsesChipFaceToken() {
        val text = code()
        assertTrue("chip 底应取 tabBackgroundColor", text.contains("themeTabBackgroundColorOrDefault()"))
        assertFalse("chip 底不得再用 mutedColor（面 token 越界）", text.contains("themeMutedColorOrDefault()"))
    }
}