package io.legado.app.api.controller

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源 Web 门面的 JS 脚本端点（ng-js-source-port）。
 *
 * 缺参必须给结构化错误而不是抛异常（老 Vue 页按 `errorMsg` 提示）；
 * `saveScript` 的入参解析同理，避免前端拿到 500。
 */
class BookSourceControllerScriptTest {

    @Test
    fun getScript_withoutUrl_returnsError() {
        val result = BookSourceController.getScript(emptyMap())
        assertEquals("参数url不能为空，请指定源地址", result.errorMsg)
    }

    @Test
    fun saveScript_blankBody_returnsError() {
        assertTrue(BookSourceController.saveScript(null).errorMsg!!.isNotEmpty())
        assertTrue(BookSourceController.saveScript("  ").errorMsg!!.isNotEmpty())
    }

    @Test
    fun saveScript_missingScriptField_returnsError() {
        val result = BookSourceController.saveScript("""{"openedSourceUrl":"u"}""")
        assertEquals("缺少 script", result.errorMsg)
    }

    @Test
    fun saveScript_invalidJson_returnsError() {
        assertTrue(BookSourceController.saveScript("not-json").errorMsg!!.isNotEmpty())
    }

    /**
     * 契约锁定（2026-10-22 真机 889KB 源）：Web 编辑器读脚本必须拿全文。
     * 若有人把上限改回 20000，前端保存截断文本会覆盖真实脚本 ⇒ 数据丢失。
     */
    @Test
    fun scriptExportLimitIsUnlimitedForEditor() {
        assertEquals(Int.MAX_VALUE, BookSourceController.SCRIPT_EXPORT_LIMIT)
    }
}
