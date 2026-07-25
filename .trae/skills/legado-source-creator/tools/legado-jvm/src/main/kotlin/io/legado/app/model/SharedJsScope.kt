package io.legado.app.model

import com.google.gson.reflect.TypeToken
import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import io.legado.app.utils.GSON
import io.legado.app.utils.isJsonObject
import org.mozilla.javascript.Scriptable
import org.mozilla.javascript.ScriptableObject
import java.util.concurrent.ConcurrentHashMap
import kotlin.coroutines.CoroutineContext

// 源码参照: app/src/main/java/io/legado/app/model/SharedJsScope.kt
// 修复内容: 实现 SharedJsScope 共享 JS 作用域，支持 jsLib 内联 JS 和 JSON 对象格式
// 简化说明: 用 ConcurrentHashMap 替代 LruCache+WeakReference，不支持 jsLib URL 下载（需 OkHttp+ACache） | 已知上限: jsLib 中的 URL 会被跳过 | 升级路径: 接入 OkHttp 同步下载 + 文件缓存

object SharedJsScope {

    private val scopeMap = ConcurrentHashMap<String, Scriptable>()

    fun getScope(jsLib: String?, coroutineContext: CoroutineContext? = null): Scriptable? {
        if (jsLib.isNullOrBlank()) {
            return null
        }
        val key = jsLib.hashCode().toString()
        var scope = scopeMap[key]
        if (scope == null) {
            scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
            if (jsLib.isJsonObject()) {
                // jsLib 是 JSON 对象格式: {"name1": "jsCode1", "name2": "url2"}
                val jsMap: Map<String, String> = GSON.fromJson(
                    jsLib,
                    TypeToken.getParameterized(
                        Map::class.java,
                        String::class.java,
                        String::class.java
                    ).type
                )
                jsMap.values.forEach { value ->
                    if (isAbsUrl(value)) {
                        // 简化说明: 不支持 jsLib URL 下载，跳过 | 升级路径: 接入 OkHttp 同步下载
                        println("[SharedJsScope] 跳过 jsLib URL 下载: $value")
                    } else {
                        RhinoScriptEngine.eval(value, scope, coroutineContext)
                    }
                }
            } else {
                // jsLib 是 JS 代码
                RhinoScriptEngine.eval(jsLib, scope, coroutineContext)
            }
            if (scope is ScriptableObject) {
                // 阻止新全局增加（即函数内未用var的隐性全局变量创建）
                scope.preventExtensions()
            }
            scopeMap[key] = scope
        }
        return scope
    }

    fun remove(jsLib: String?) {
        if (jsLib.isNullOrBlank()) {
            return
        }
        val key = jsLib.hashCode().toString()
        scopeMap.remove(key)
    }

    private fun isAbsUrl(str: String): Boolean =
        str.startsWith("http://", true) || str.startsWith("https://", true)

}
