package io.legado.app.api

import com.google.gson.JsonParser
import io.legado.app.utils.GSON
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ReturnData 信封单测（一期 · 3.1 / REQ-1-301 / REQ-1-302）。
 *
 * 守两条红线：
 * 1. `isSuccess` / `errorMsg` / `data` 三字段语义**完全不变**（老 vue 页只看这三个）；
 * 2. 新增 `code` **默认 200** ⇒ 未显式设置时行为与改造前一致（HTTP 200），且能被 Gson 序列化出去。
 */
class ReturnDataTest {

    @Test
    fun defaults_successFalse_code200() {
        val data = ReturnData()
        assertFalse("默认非成功", data.isSuccess)
        assertEquals("默认 code 须为 200（保持改造前行为）", 200, data.code)
    }

    @Test
    fun setData_marksSuccessAndClearsErrorMsg_keepsCode() {
        val data = ReturnData()
        data.setErrorMsg("先失败")
        data.setData("ok")
        assertTrue(data.isSuccess)
        assertEquals("", data.errorMsg)
        assertEquals("ok", data.data)
        assertEquals("setData 不得隐式改 code", 200, data.code)
    }

    @Test
    fun setErrorMsg_marksFailureAndKeepsDataNull() {
        val data = ReturnData()
        data.setErrorMsg("格式不对")
        assertFalse(data.isSuccess)
        assertEquals("格式不对", data.errorMsg)
        assertEquals(null, data.data)
    }

    @Test
    fun setCode_isChainable_andIndependentOfThreeFields() {
        val data = ReturnData()
        val chained = data.setErrorMsg("unauthorized").setCode(401)
        assertTrue("setCode 须可链式", chained === data)
        assertEquals(401, data.code)
        assertEquals("unauthorized", data.errorMsg)
        assertFalse(data.isSuccess)
    }

    @Test
    fun gson_serializesCode_andKeepsLegacyFieldNames() {
        // 注意：本仓 `GSON` 开了 setPrettyPrinting（带换行与空格）⇒
        // 断言必须**格式无关**，用 JsonParser 取值，禁止 contains("\"code\":403") 这类写法（首次实现即踩此坑）。
        val denied = JsonParser.parseString(GSON.toJson(ReturnData().setErrorMsg("denied").setCode(403)))
            .asJsonObject
        assertTrue("旧字段名须保持（老页依赖）：isSuccess", denied.has("isSuccess"))
        assertTrue("旧字段名须保持：errorMsg", denied.has("errorMsg"))
        assertFalse("失败分支 isSuccess 须为 false", denied.get("isSuccess").asBoolean)
        assertEquals("errorMsg 须原样带出", "denied", denied.get("errorMsg").asString)
        assertEquals("新增字段 code 须与设置值一致", 403, denied.get("code").asInt)

        // 成功分支
        val ok = JsonParser.parseString(GSON.toJson(ReturnData().setData("payload"))).asJsonObject
        assertTrue("成功分支 isSuccess 须为 true", ok.get("isSuccess").asBoolean)
        assertEquals("data 须带出", "payload", ok.get("data").asString)
        assertEquals("未设置 code 时应为默认 200", 200, ok.get("code").asInt)
    }
}
