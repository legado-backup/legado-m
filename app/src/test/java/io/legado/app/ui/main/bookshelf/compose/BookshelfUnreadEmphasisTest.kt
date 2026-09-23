package io.legado.app.ui.main.bookshelf.compose

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R16「书架未读颜色强调」单测（覆盖 spec R16-1 / R16-2 / R16-3）。
 *
 * 口径：开关开启且**未读** ⇒ 标题用主题强调色；已读不变；开关**默认关** ⇒ 渲染与现状一致。
 * 强调色取自主题（`accentColor`），其与页面底的对比度由主题成对提供（夜间/E-Ink 由主题保证可读）。
 */
class BookshelfUnreadEmphasisTest {

    private val accent = 0xFF7B1FA2.toInt()
    private val primaryText = 0xFF212121.toInt()

    // ---- R16-1：开启后未读用强调色 ----
    @Test
    fun r16_1_enabledAndUnread_usesAccent() {
        assertEquals(
            accent,
            BookshelfUnreadEmphasis.titleColor(
                enabled = true, unreadCount = 3, accent = accent, primaryText = primaryText
            )
        )
    }

    // ---- R16-2：默认关 / 已读 ⇒ 与现状一致 ----
    @Test
    fun r16_2_disabledOrRead_keepsPrimaryText() {
        assertEquals(
            "开关关闭时（默认）未读也必须用主文字色",
            primaryText,
            BookshelfUnreadEmphasis.titleColor(
                enabled = false, unreadCount = 5, accent = accent, primaryText = primaryText
            )
        )
        assertEquals(
            "开启但已读完 ⇒ 不得强调",
            primaryText,
            BookshelfUnreadEmphasis.titleColor(
                enabled = true, unreadCount = 0, accent = accent, primaryText = primaryText
            )
        )
        assertEquals(
            "未读数异常为负 ⇒ 不得强调",
            primaryText,
            BookshelfUnreadEmphasis.titleColor(
                enabled = true, unreadCount = -1, accent = accent, primaryText = primaryText
            )
        )
    }

    /**
     * 接线不变量：**所有真实书架渲染路径**必须共用同一决策函数（口径分裂 ⇒ 同开关下表现不一致），
     * 且配置默认值必须为 **false**（新装/升级渲染零变化）。
     *
     * ⚠ 实测教训（2026-09-24）：`compose/BookshelfComposeItems.BookshelfGridItem` 在 App 内**零调用**
     * （设备实际渲染的是 `BookshelfScreen.kt` 的 `BookGridItem` / 列表行）——只改前者会得到
     * 「代码改了、真机无变化」的假通过。故此处把**真实路径**（`BookshelfScreen.kt`）钉为必检项。
     */
    @Test
    fun r16_wiring_allLivePathsShareSingleDecision_andDefaultOff() {
        val live = code("ui/main/bookshelf/BookshelfScreen.kt")
        assertEquals(
            "真实渲染路径 BookshelfScreen 必须有两处（网格卡 + 列表行）调用统一决策函数",
            2,
            Regex("BookshelfUnreadEmphasis\\.titleColor\\(").findAll(live).count()
        )

        val grid = code("ui/main/bookshelf/compose/BookshelfComposeItems.kt")
        val list = code("ui/main/bookshelf/compose/BookshelfComposeList.kt")
        assertTrue("网格布局文件亦应调用统一决策函数", grid.contains("BookshelfUnreadEmphasis.titleColor("))
        assertTrue("列表布局文件亦应调用统一决策函数", list.contains("BookshelfUnreadEmphasis.titleColor("))

        val appConfig = code("help/config/AppConfig.kt")
        assertTrue(
            "配置默认值必须为 false（默认关）",
            appConfig.contains("getPrefBoolean(PreferKey.bookshelfUnreadEmphasis, false)")
        )
    }

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }
}