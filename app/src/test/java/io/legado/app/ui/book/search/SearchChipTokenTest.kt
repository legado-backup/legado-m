package io.legado.app.ui.book.search

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 搜索页 chip 底口径不变量回归测试（B7 R28/D1，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 D1）：同语义「筛选 chip 未选中底」曾有三套口径 ——
 * Compose 侧 `AppFilterChip`、本页 View 侧程序化 chip（弱化底）、规范（chip 面 token）
 * ⇒ 换主题色后两栈分量不同。B7 R28 统一取 chip 面 token `tabBackgroundColor`。
 *
 * CE 5.2（2026-09-24）本页换装：**View 侧程序化 chip（原 `createSourceGroupChip`）随页删除**
 * ⇒ 该语义只剩共享 `AppFilterChip` **唯一实现**。本测试守护点随之从「两栈同 token」
 * 收敛为「**单源实现内含 chip 面 token** + 本页不得再自建第二套 chip」。
 *
 * 探针走单源 [SourceFileProbe]（CC-1：禁止再复制私有的读源码 + 剥注释实现）。
 */
class SearchChipTokenTest {

    private val page = "ui/book/search/SearchActivity.kt"
    private val chipComponent = "ui/widget/components/AppFilterChip.kt"

    /** 未选中 chip 底必须取 chip 面 token（唯一实现口径）。 */
    @Test
    fun groupChip_idleBackgroundUsesChipFaceToken() {
        val chipCode = SourceFileProbe.sourceText(chipComponent)
        assertTrue(
            "chip 底应取 chip 面 token tabBackgroundColor",
            chipCode.contains("themeUi.tabBackgroundColor")
        )
        assertFalse(
            "chip 底不得再用 mutedColor（面 token 越界）",
            chipCode.contains("themeMutedColorOrDefault()")
        )
    }

    /** 搜索页不得再自建第二套 chip（同语义单一实现）。 */
    @Test
    fun searchPage_doesNotOwnASecondChipImplementation() {
        val pageCode = SourceFileProbe.sourceText(page)
        assertFalse(
            "本页 View 侧程序化 chip 应已随 CE 5.2 删除（不得遗留第二套口径）",
            pageCode.contains("createSourceGroupChip")
        )
        assertFalse(
            "本页不得再直接写 chip 面 token（应由 AppFilterChip 唯一承载）",
            pageCode.contains("themeTabBackgroundColorOrDefault()")
        )
        assertTrue("本页分组 chips 必须走共享 AppFilterChip", pageCode.contains("AppFilterChip("))
    }
}