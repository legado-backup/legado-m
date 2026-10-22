package io.legado.app.model.login

import io.legado.app.data.entities.BaseSource
import io.legado.app.data.entities.BookSource
import io.legado.app.exception.NoStackTraceException
import io.legado.app.model.jsSource.JsSourceEngine
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject

fun BaseSource.isLoginUiV2(): Boolean = LoginUiV2.isV2(loginUi)

fun BaseSource.evalLoginUiV2(stateJson: String): String? {
    singleFileJsEngine()?.let { engine ->
        return engine.callFunction(
            "loginUi",
            listOf("state" to parseLoginObject(stateJson)),
        )
    }
    val script = getLoginJs()
        ?: throw NoStackTraceException("登录 UI v2 缺少 loginUi/loginAction 脚本")
    val result = evalJS(
        "$script\nloginUi(JSON.parse(String(__loginState)))"
    ) {
        put("__loginState", stateJson)
    }
    return JsSourceEngine.normalizeJsResult(result)
}

fun BaseSource.evalLoginActionV2(
    action: String,
    stateJson: String,
    formJson: String,
): String? {
    singleFileJsEngine()?.let { engine ->
        return engine.callFunction(
            "loginAction",
            listOf(
                "action" to action,
                "state" to parseLoginObject(stateJson),
                "form" to parseLoginObject(formJson),
            ),
        )
    }
    val script = getLoginJs()
        ?: throw NoStackTraceException("登录 UI v2 缺少 loginUi/loginAction 脚本")
    val result = evalJS(
        "$script\n" +
            "loginAction(String(__loginAction), JSON.parse(String(__loginState)), " +
            "JSON.parse(String(__loginForm)))"
    ) {
        put("__loginAction", action)
        put("__loginState", stateJson)
        put("__loginForm", formJson)
    }
    return JsSourceEngine.normalizeJsResult(result)
}

private fun BaseSource.singleFileJsEngine(): JsSourceEngine? {
    val bookSource = this as? BookSource ?: return null
    if (bookSource.mainJs.isNullOrBlank()) return null
    return JsSourceEngine(bookSource)
}

private fun parseLoginObject(value: String): Map<String, Any?> {
    return GSON.fromJsonObject<Map<String, Any?>>(value).getOrThrow()
}
