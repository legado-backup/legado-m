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
}
