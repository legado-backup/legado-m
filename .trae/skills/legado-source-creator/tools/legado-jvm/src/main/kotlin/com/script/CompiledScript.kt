package com.script

import org.mozilla.javascript.Scriptable
import kotlin.coroutines.CoroutineContext

// 简化说明: 从 modules/rhino 抽取 CompiledScript 抽象类，移除 ScriptEngine/ScriptContext 依赖 | 已知上限: 无 Bindings/ScriptContext 支持 | 升级路径: 引入 modules/rhino 模块
abstract class CompiledScript {
    abstract fun eval(scope: Scriptable, coroutineContext: CoroutineContext?): Any?

    fun eval(scope: Scriptable): Any? {
        return eval(scope, null)
    }
}
