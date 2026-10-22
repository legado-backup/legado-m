package io.legado.app.model

import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import org.junit.Assert
import org.junit.Test
import java.io.File

class SharedJsScopeTest {

    private fun cryptoScope(): org.mozilla.javascript.Scriptable {
        val f = File("src/main/assets/scripts/cryptojs.min.js")
        Assert.assertTrue("asset 不存在: ${f.absolutePath}", f.exists())
        val text = f.readText()
        return RhinoScriptEngine.run {
            val scope = getRuntimeScope(ScriptBindings())
            eval(text, scope)
            scope
        }
    }

    @Test
    fun cryptoJsMd5FixedVector() {
        val scope = cryptoScope()
        val md5 = RhinoScriptEngine.eval("CryptoJS.MD5('legado').toString()", scope)
        Assert.assertEquals("bbd6a62a8a291b19a802e4ad64547fff", md5)
    }

    @Test
    fun cryptoJsSha256FixedVector() {
        val scope = cryptoScope()
        val sha256 = RhinoScriptEngine.eval("CryptoJS.SHA256('legado').toString()", scope)
        Assert.assertEquals(
            "c848c83a14853821592f9ec571c3ee23caa985a2ebe93b8d3185be3e9d650051",
            sha256
        )
    }

    @Test
    fun cryptoJsAesRoundTrip() {
        val scope = cryptoScope()
        val keyIv = "1234567890abcdef"
        val encrypted = RhinoScriptEngine.eval(
            "CryptoJS.AES.encrypt('hello', CryptoJS.enc.Utf8.parse('$keyIv'), {iv: CryptoJS.enc.Utf8.parse('$keyIv')}).toString()",
            scope
        )
        Assert.assertTrue("加密结果为空", encrypted != null && encrypted.toString().isNotBlank())
        val decrypted = RhinoScriptEngine.eval(
            "CryptoJS.AES.decrypt('$encrypted', CryptoJS.enc.Utf8.parse('$keyIv'), {iv: CryptoJS.enc.Utf8.parse('$keyIv')}).toString(CryptoJS.enc.Utf8)",
            scope
        )
        Assert.assertEquals("hello", decrypted)
    }

    /**
     * JS 书源在 Rhino 下调用 `CryptoJS.lib.WordArray.random` 会因缺少宿主
     * `crypto.getRandomValues` 而抛 "Native crypto module could not be used to get secure random"。
     * 修复：注入 Java SecureRandom 替换该入口；补丁后必须产出 32 位 hex 且两次不同。
     */
    @Test
    fun cryptoJsWordArrayRandomUsesHostSecureRandom() {
        val scope = cryptoScope()
        // 缺陷复现：未打补丁时无法取得安全随机数
        var patchedNeeded = false
        try {
            RhinoScriptEngine.eval("CryptoJS.lib.WordArray.random(16).toString()", scope)
            patchedNeeded = false
        } catch (e: Throwable) {
            patchedNeeded = true
            Assert.assertTrue(
                "异常应指向缺失的 crypto 宿主能力，实际: ${e.message}",
                e.message?.contains("crypto", ignoreCase = true) == true
            )
        }
        Assert.assertTrue("JVM 环境应能复现 crypto 缺失（否则本用例失去意义）", patchedNeeded)

        SharedJsScope.CryptoRandomPatch.install(scope, null)
        val first = RhinoScriptEngine.eval(
            "CryptoJS.lib.WordArray.random(16).toString()", scope
        ).toString()
        val second = RhinoScriptEngine.eval(
            "CryptoJS.lib.WordArray.random(16).toString()", scope
        ).toString()
        Assert.assertEquals("16 字节应为 32 位 hex", 32, first.length)
        Assert.assertTrue("随机值应为十六进制字符串", first.matches(Regex("^[0-9a-f]{32}$")))
        Assert.assertNotEquals("两次随机值不应相同", first, second)
        Assert.assertEquals(
            "临时绑定必须被清理（脚本侧不可见）",
            "undefined",
            RhinoScriptEngine.eval("typeof __legadoSecureRandomInt", scope).toString()
        )
    }
}
