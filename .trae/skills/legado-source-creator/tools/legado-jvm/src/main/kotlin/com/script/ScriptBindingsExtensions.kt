package com.script

import org.mozilla.javascript.Context

// 源码参照: modules/rhino/src/main/java/com/script/ScriptBindingsExtensions.kt

inline fun buildScriptBindings(block: (bindings: ScriptBindings) -> Unit): ScriptBindings {
    val bindings = ScriptBindings()
    Context.enter()
    try {
        block(bindings)
    } finally {
        Context.exit()
    }
    return bindings
}
