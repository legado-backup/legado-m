package io.legado.app.ui.book.source.manage

import io.legado.app.data.entities.BookSourcePart
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源管理页的 JS 源入口判定（ng-js-source-port）与制作链路入口（js-source-parity-and-crash-fix）。
 *
 * `hasJs` 来自 `book_sources_part` 视图；它决定列表标识与「编辑脚本」入口，
 * 默认必须为 false（老库升级后不应把所有源误标成 JS 源）。
 */
class BookSourceJsEntryTest {

    @Test
    fun hasJs_defaultsFalseForLegacyRows() {
        assertFalse(BookSourcePart(bookSourceUrl = "u").hasJs)
        assertFalse(BookSourcePart(bookSourceUrl = "u", hasSearchUrl = true).hasJs)
    }

    @Test
    fun hasJs_survivesCopyForLocalUiRefresh() {
        val js = BookSourcePart(bookSourceUrl = "u", hasJs = true).copy(enabledExplore = false)
        assertTrue(js.hasJs)
    }

    @Test
    fun hasJs_doesNotChangeSearchCapabilityFlag() {
        val js = BookSourcePart(bookSourceUrl = "u", hasJs = true, hasSearchUrl = true)
        assertEquals(true, js.hasSearchUrl)
    }

    /**
     * 2026-10-23 制作链路入口契约（修复「管理页没有新建 JS 书源入口」「编辑走 Binder 传正文」）：
     * - 「添加书源」必须是**下拉二选一**（规则源 / JS 源），对齐 NG `book_source_add_rules|javascript`；
     * - 编辑 JS 源必须交给 `JsSourceEditActivity` 编排页，且脚本正文走会话通道（零 Binder）。
     */
    @Test
    fun addSourceMenuOffersRulesAndJs() {
        val source = SourceFileProbe.sourceText("ui/book/source/manage/BookSourceActivity.kt")
        assertTrue(
            "「添加书源」必须改为下拉菜单（menuActions != null 时 scaffold 走下拉、忽略 onClick）",
            source.contains("menuActions = ::addSourceMenuActions")
        )
        assertTrue("下拉必须有「新建规则书源」", source.contains("R.string.book_source_add_rules"))
        assertTrue("下拉必须有「新建 JS 书源」", source.contains("R.string.book_source_add_javascript"))
        assertFalse(
            "不得再把整段脚本塞进 Intent（Binder 超限 ⇒ 编辑页卡死/闪退）",
            source.contains("putExtra(\"text\", script)")
        )
        assertTrue(
            "JS 源编辑必须走编排页",
            source.contains("StartActivityContract(JsSourceEditActivity::class.java)")
        )
    }

    /** 所有入口的 JS 源编辑都必须被重定向到编排页（此前是 toast + finish 的死路）。 */
    @Test
    fun declarativeEditorRedirectsJsSource() {
        val edit = SourceFileProbe.sourceText("ui/book/source/edit/BookSourceEditActivity.kt")
        assertTrue(
            "必须按 sourceUrl 查 hasJsSource 决定重定向",
            edit.contains("hasJsSource(sourceUrl)")
        )
        assertTrue(
            "重定向目标必须是 JS 编排页",
            edit.contains("startActivity<JsSourceEditActivity>")
        )
        assertFalse(
            "不得残留「toast 后 finish」的死路写法",
            edit.contains("R.string.js_source_use_script_editor")
        )
    }
}
