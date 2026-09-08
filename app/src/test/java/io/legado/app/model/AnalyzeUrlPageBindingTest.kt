package io.legado.app.model

import com.script.ScriptBindings
import com.script.buildScriptBindings
import com.script.rhino.RhinoScriptEngine
import org.junit.Assert
import org.junit.Test
import java.io.File

/**
 * 复现 {{page}} 分页失效问题：模拟 AnalyzeUrl.evalJS 的完整作用域结构
 * （bindings + cryptoScope 共享原型，模拟 47b3b8276 引入的 getShareScope 兜底）。
 */
class AnalyzeUrlPageBindingTest {

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

    /** 场景A：无共享作用域（原版无 jsLib 源的行为） */
    @Test
    fun pageBindingWithoutSharedScope() {
        val bindings = buildScriptBindings { bindings ->
            bindings["page"] = 2
            bindings["key"] = "test"
        }
        val scope = RhinoScriptEngine.getRuntimeScope(bindings)
        val result = RhinoScriptEngine.eval("page", scope)
        Assert.assertEquals("page 应解析为 2", 2, (result as Number).toInt())
    }

    /** 场景B：cryptoScope 作为共享原型（当前 fork 对全部无 jsLib 源的行为） */
    @Test
    fun pageBindingWithCryptoScopePrototype() {
        val shared = cryptoScope()
        val bindings = buildScriptBindings { bindings ->
            bindings["page"] = 2
            bindings["key"] = "test"
        }
        val scope = bindings.apply { prototype = shared }
        val result = RhinoScriptEngine.eval("page", scope)
        Assert.assertEquals("page 应解析为 2", 2, (result as Number).toInt())
    }

    /** 场景C：cryptoScope 冻结后作为原型 + page 算术表达式（常见写法 {{page-1}}） */
    @Test
    fun pageArithmeticWithFrozenCryptoScopePrototype() {
        val shared = cryptoScope()
        if (shared is org.mozilla.javascript.ScriptableObject) {
            shared.preventExtensions()
        }
        val bindings = buildScriptBindings { bindings ->
            bindings["page"] = 3
        }
        val scope = bindings.apply { prototype = shared }
        val result = RhinoScriptEngine.eval("page-1", scope)
        Assert.assertEquals("page-1 应解析为 2", 2, (result as Number).toInt())
    }
}
