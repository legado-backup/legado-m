package com.script

import org.mozilla.javascript.Context
import org.mozilla.javascript.NativeObject

// 源码参照: modules/rhino/src/main/java/com/script/ScriptBindings.kt
// 简化说明: 从 modules/rhino 模块抽取 ScriptBindings，使用 org.mozilla.javascript 原生 API | 已知上限: 无 SharedJsScope 支持 | 升级路径: 引入 modules/rhino 模块

class ScriptBindings : NativeObject() {

    companion object {
        private val topLevelScope: org.mozilla.javascript.ScriptableObject by lazy {
            val cx = Context.enter()
            try {
                cx.initStandardObjects()
            } finally {
                Context.exit()
            }
        }
    }

    init {
        prototype = topLevelScope
    }

    operator fun set(key: String, value: Any?) {
        Context.enter()
        try {
            put(key, this, Context.javaToJS(value, this))
        } finally {
            Context.exit()
        }
    }

    operator fun set(index: Int, value: Any?) {
        Context.enter()
        try {
            put(index, this, Context.javaToJS(value, this))
        } finally {
            Context.exit()
        }
    }

    fun put(key: String, value: Any?) {
        set(key, value)
    }
}
