package io.legado.app.ui.book.source.edit

import io.legado.app.data.entities.BookSource
import io.legado.app.model.jsSource.isJsSource
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源编辑页路由判定（ng-js-source-port）。
 *
 * 规则页对 JS 源无意义（规则字段被剥离），必须改道脚本编辑器，
 * 否则用户会在空规则页误保存、且看不到真正的脚本。这里锁定该判定。
 */
class JsSourceEditRoutingTest {

    @Test
    fun jsSource_mustNotOpenRuleEditor() {
        assertTrue(BookSource(bookSourceUrl = "u", mainJs = "var config={};").isJsSource())
    }

    @Test
    fun declarativeSource_keepsRuleEditor() {
        assertFalse(BookSource(bookSourceUrl = "u", searchUrl = "https://x/{{key}}").isJsSource())
    }
}
