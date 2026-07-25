package io.legado.ruleengine

import io.legado.app.exception.NoStackTraceException

/**
 * 用户介入需求异常
 *
 * 当 startBrowserAwait / getVerificationCode 等方法需要用户手动操作时抛出。
 * debug() 捕获后返回 DebugResult(needsUserIntervention=true)。
 *
 * @param stage 触发阶段（如 "login", "verification"）
 */
class UserInterventionException(
    val stage: String,
    message: String
) : NoStackTraceException(message)
