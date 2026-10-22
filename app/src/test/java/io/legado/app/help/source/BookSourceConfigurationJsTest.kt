package io.legado.app.help.source

import io.legado.app.data.entities.BookSource
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 导入期「空壳源」判定与 JS 源（ng-js-source-port）。
 *
 * JS 源规则字段为空是正常的（脚本自带抓取逻辑），不能被当成空壳源剔除；
 * 老源判定必须保持原口径（无搜索无发现且无规则 ⇒ 仍判空壳）。
 */
class BookSourceConfigurationJsTest {

    @Test
    fun jsOnlySource_isNotEmptyConfiguration() {
        val js = BookSource(
            bookSourceUrl = "https://a",
            bookSourceName = "js",
            mainJs = "var config={};",
        )
        assertFalse(js.isEmptyConfiguration())
    }

    @Test
    fun trulyEmptySource_isEmptyConfiguration() {
        assertTrue(BookSource(bookSourceUrl = "https://a", bookSourceName = "empty").isEmptyConfiguration())
    }

    @Test
    fun declarativeSearchSource_isNotEmptyConfiguration() {
        val source = BookSource(
            bookSourceUrl = "https://a",
            bookSourceName = "decl",
            searchUrl = "https://a/search?q={{key}}",
        )
        assertFalse(source.isEmptyConfiguration())
    }
}
