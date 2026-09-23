package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B7 R30 共享 tab_bar 取色不变量（源码文本断言；依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷：本页的共享宿主 `activity_theme_manage.xml` 双段切换条段底原依赖 **XML 静态**
 * `@drawable/bg_bookshelf_tag_item`（`@color/background_card`，仅日夜两态）⇒ 换自定义主题色/
 * 主题包时选中段底不跟随；本页当时只把「轨道」底色改成主题派生、**漏了段底**（同族一处补一处漏）。
 */
class ReadAloudBgmTagBarTokenTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/ui/book/read/config/ReadAloudBgmManageActivity.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun tabBarSegmentsUseThemeDerivedSelector() {
        val t = code()
        assertTrue("轨道应走主题派生 opaqueRounded", t.contains("opaqueRounded"))
        assertTrue("段底应走主题派生 actionSelector（镜像同语义既有实现）", t.contains("actionSelector"))
        assertTrue("段底应取主题卡片色", t.contains("themeCardColorOrDefault()"))
        assertFalse("不得再引用已删除的静态 drawable", t.contains("bg_bookshelf_tag_item"))
        assertFalse("不得再引用已删除的静态 drawable", t.contains("bg_bookshelf_tag_track"))
    }
}