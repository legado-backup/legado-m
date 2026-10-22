package io.legado.app.service.kernel

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * 保存书源时 `mainJs` 的取值契约（ng-js-source-port · 2026-10-22）。
 *
 * 背景：Web 列表接口已剥离 `mainJs`（防响应膨胀），前端「列表对象回填保存」与
 * 老 JSON 编辑流程都可能把不含脚本的整源写回。若直接写库会**清空真实脚本**（数据丢失）。
 * 契约：`null`（字段未携带）= 保持库中值；`""`（显式空串）= 清除；其余 = 覆盖。
 */
class BookSourceScriptPreserveTest {

    @Test
    fun missingFieldKeepsExistingScript() {
        assertEquals("function search(){}", BookSourceKernel.resolveScriptForSave(null, "function search(){}"))
        assertNull("库中也没有脚本时仍为 null", BookSourceKernel.resolveScriptForSave(null, null))
    }

    @Test
    fun explicitEmptyStringClearsScript() {
        assertEquals("", BookSourceKernel.resolveScriptForSave("", "function search(){}"))
    }

    @Test
    fun providedScriptOverridesExisting() {
        assertEquals("new", BookSourceKernel.resolveScriptForSave("new", "old"))
    }
}
