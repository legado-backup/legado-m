package com.script.rhino

import com.script.CompiledScript
import com.script.ScriptBindings
import org.mozilla.javascript.Context
import org.mozilla.javascript.ContextFactory
import org.mozilla.javascript.Scriptable
import java.io.StringReader
import kotlin.coroutines.CoroutineContext

// 简化说明: 从 modules/rhino 抽取 RhinoScriptEngine，使用 org.mozilla.javascript 原生 API | 已知上限: 无 RhinoTopLevel/编译缓存 | 升级路径: 引入 modules/rhino 模块

/**
 * 修复 GAP-70a: RhinoContext 子类（对齐真机 RhinoContext.kt）
 * 简化说明: 仅包含构造函数，移除协程取消/递归检查（仿真端用时间阈值替代） | 已知上限: 无协程取消响应、无递归深度检查 | 升级路径: 引入完整 RhinoContext
 */
private class RhinoContext(factory: ContextFactory) : Context(factory)

object RhinoScriptEngine {

    // 修复 GAP-70b: JS执行超时控制（对齐真机 RhinoContext.ensureActive 机制）
    // 简化说明: 真机通过 RhinoContext.ensureActive() 检查协程取消，仿真端用时间阈值替代 | 已知上限: 无法响应协程取消 | 升级路径: 引入 RhinoContext
    private val jsStartTime = ThreadLocal<Long>()
    private const val JS_TIMEOUT_MS = 30000L  // 30秒超时

    init {
        // 修复 GAP-70a: 移植 WrapFactory + instructionObserverThreshold（对齐真机 RhinoScriptEngine.kt 第319-330行）
        // 简化说明: 使用默认 WrapFactory，仅设置 instructionObserverThreshold 和 maximumInterpreterStackDepth | 已知上限: 无 RhinoClassShutter 安全控制 | 升级路径: 引入 RhinoClassShutter
        try {
            ContextFactory.initGlobal(object : ContextFactory() {
                override fun makeContext(): Context {
                    val cx = RhinoContext(this)
                    cx.languageVersion = Context.VERSION_ES6
                    cx.setInterpretedMode(true)
                    cx.instructionObserverThreshold = 10000
                    cx.maximumInterpreterStackDepth = 1000
                    return cx
                }

                // 修复 GAP-70b: 指令计数观察器，检测JS执行超时（对齐真机 observeInstructionCount 第340-344行）
                // 真机模式: cx.ensureActive() 检查协程是否已取消
                // 仿真模式: 检查JS执行是否超过30秒阈值
                override fun observeInstructionCount(cx: Context, instructionCount: Int) {
                    val startTime = jsStartTime.get()
                    if (startTime != null && System.currentTimeMillis() - startTime > JS_TIMEOUT_MS) {
                        // 简化说明: 真机用 RhinoInterruptError，仿真端用 RuntimeException 替代 | 已知上限: 无 | 升级路径: 引入 RhinoInterruptError
                        throw RuntimeException("JS执行超时(${JS_TIMEOUT_MS}ms)，可能存在死循环")
                    }
                }
            })
        } catch (_: IllegalStateException) {
            // ContextFactory.initGlobal 只能调用一次，如果已被调用则忽略
        }
    }

    fun getRuntimeScope(bindings: ScriptBindings): Scriptable {
        val cx = Context.enter()
        try {
            bindings.prototype = cx.initStandardObjects()
        } finally {
            Context.exit()
        }
        return bindings
    }

    fun eval(js: String, scope: Scriptable, coroutineContext: CoroutineContext? = null): Any? {
        // 修复 GAP-70b: 记录JS执行开始时间，用于 observeInstructionCount 超时检测
        jsStartTime.set(System.currentTimeMillis())
        val cx = Context.enter()
        try {
            cx.languageVersion = Context.VERSION_ES6
            return cx.evaluateReader(scope, StringReader(js), "<eval>", 1, null)
        } finally {
            Context.exit()
            jsStartTime.remove()
        }
    }

    fun eval(js: String, bindingsConfig: ScriptBindings.() -> Unit = {}): Any? {
        val bindings = ScriptBindings()
        Context.enter()
        try {
            bindings.apply(bindingsConfig)
        } finally {
            Context.exit()
        }
        return eval(js, getRuntimeScope(bindings))
    }

    fun compile(js: String): CompiledScript {
        val cx = Context.enter()
        try {
            cx.languageVersion = Context.VERSION_ES6
            val compiled = cx.compileReader(StringReader(js), "<eval>", 1, null)
            return object : CompiledScript() {
                override fun eval(scope: Scriptable, coroutineContext: CoroutineContext?): Any? {
                    // 修复 GAP-70b: 记录JS执行开始时间，用于 observeInstructionCount 超时检测
                    jsStartTime.set(System.currentTimeMillis())
                    val cx2 = Context.enter()
                    try {
                        cx2.languageVersion = Context.VERSION_ES6
                        return compiled.exec(cx2, scope)
                    } finally {
                        Context.exit()
                        jsStartTime.remove()
                    }
                }
            }
        } finally {
            Context.exit()
        }
    }
}
