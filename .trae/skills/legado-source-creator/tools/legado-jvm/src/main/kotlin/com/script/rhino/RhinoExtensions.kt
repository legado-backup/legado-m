package com.script.rhino

import org.mozilla.javascript.Context
import kotlin.coroutines.CoroutineContext

// 源码参照: modules/rhino/src/main/java/com/script/rhino/RhinoExtensions.kt#L42-L53
// 简化说明: runScriptWithContext 简化为直接执行 block，不绑定 CoroutineContext 到 RhinoContext | 已知上限: JS 无法感知协程上下文 | 升级路径: 引入 modules/rhino 模块

inline fun <T> runScriptWithContext(context: CoroutineContext, block: () -> T): T {
    Context.enter()
    try {
        return block()
    } finally {
        Context.exit()
    }
}
