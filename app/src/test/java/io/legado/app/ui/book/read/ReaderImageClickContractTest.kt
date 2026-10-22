package io.legado.app.ui.book.read

import io.legado.app.data.entities.BookSource
import io.legado.app.model.jsSource.MAIN_JS_IMAGE_CLICK_DEFERRED
import io.legado.app.model.jsSource.shouldDeferImageClick
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 阅读页图片点击的 JS 源桥接契约（ng-js-source-port）。
 *
 * 声明式 `click` 脚本作用域看不到 `mainJs`，故用稳定哨兵值转交 `onImageClick`。
 * 哨兵值属于跨端协议（书源作者也要写它），改动必须同时改测试 —— 用断言锁死字面量。
 */
class ReaderImageClickContractTest {

    @Test
    fun sentinelValue_isStableProtocolConstant() {
        assertEquals("__legado_main_js_image_click_deferred__", MAIN_JS_IMAGE_CLICK_DEFERRED)
    }

    @Test
    fun deferDecision_requiresExactSentinelAndJsSource() {
        val js = BookSource(bookSourceUrl = "u", mainJs = "var config={};")
        assertTrue(js.shouldDeferImageClick(MAIN_JS_IMAGE_CLICK_DEFERRED))
        assertFalse(js.shouldDeferImageClick(MAIN_JS_IMAGE_CLICK_DEFERRED + " "))
        assertFalse(js.shouldDeferImageClick(null))
        assertFalse(BookSource(bookSourceUrl = "u").shouldDeferImageClick(MAIN_JS_IMAGE_CLICK_DEFERRED))
    }
}
