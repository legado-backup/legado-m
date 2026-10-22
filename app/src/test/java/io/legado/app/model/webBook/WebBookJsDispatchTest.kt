package io.legado.app.model.webBook

import io.legado.app.data.entities.BookSource
import io.legado.app.model.jsSource.isJsSource
import io.legado.app.model.jsSource.shouldDeferImageClick
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * WebBook 五条链路的前置分流判据（ng-js-source-port）。
 *
 * 老源零回归的根：`mainJs` 为空（含空白）时必须走声明式路径。
 * 这里锁定该布尔判据与图片点击延迟哨兵的「仅 JS 源生效」语义。
 */
class WebBookJsDispatchTest {

    @Test
    fun nullOrBlankMainJs_isNotJsSource() {
        assertFalse(BookSource(bookSourceUrl = "https://a").isJsSource())
        assertFalse(BookSource(bookSourceUrl = "https://a", mainJs = "").isJsSource())
        assertFalse(BookSource(bookSourceUrl = "https://a", mainJs = "   \n").isJsSource())
    }

    @Test
    fun nonBlankMainJs_isJsSource() {
        assertTrue(BookSource(bookSourceUrl = "https://a", mainJs = "function search(){}").isJsSource())
    }

    @Test
    fun imageClickSentinel_onlyDefersForJsSource() {
        val payload = """{"click":"__legado_main_js_image_click_deferred__"}"""
        val jsSource = BookSource(bookSourceUrl = "https://a", mainJs = "var config={};")
        val oldSource = BookSource(bookSourceUrl = "https://b")
        assertTrue(jsSource.shouldDeferImageClick("__legado_main_js_image_click_deferred__"))
        // 返回内容不是哨兵值 ⇒ 永不转交
        assertFalse(jsSource.shouldDeferImageClick(payload))
        // 老源即使是哨兵值也保持原行为（不转交）
        assertFalse(oldSource.shouldDeferImageClick("__legado_main_js_image_click_deferred__"))
    }
}
