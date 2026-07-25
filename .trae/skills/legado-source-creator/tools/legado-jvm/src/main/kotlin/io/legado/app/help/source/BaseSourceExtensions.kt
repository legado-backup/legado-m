package io.legado.app.help.source

import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.model.SharedJsScope
import org.mozilla.javascript.Scriptable

// 源码参照: app/src/main/java/io/legado/app/help/source/BaseSourceExtensions.kt#L11-L13
// 修复内容: 调用 SharedJsScope.getScope 实现 JS 共享作用域
// 简化说明: SharedJsScope 简化版，不支持 jsLib URL 下载 | 已知上限: jsLib 中的 URL 会被跳过 | 升级路径: 接入 OkHttp 同步下载

fun BaseSourceInterface.getShareScope(coroutineContext: kotlin.coroutines.CoroutineContext? = null): Scriptable? {
    return SharedJsScope.getScope(jsLib, coroutineContext)
}
