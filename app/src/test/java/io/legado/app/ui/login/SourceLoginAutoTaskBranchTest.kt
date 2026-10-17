package io.legado.app.ui.login

import io.legado.app.model.AutoTask
import io.legado.app.model.AutoTaskRule
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 自动任务「登录」链接线护栏（2026-10-17 修复）。
 *
 * 背景（真缺陷）：`AutoTaskEditActivity.openLogin()` 传 `type="autoTask"` / `key=rule.id`，
 * 而 `SourceLoginViewModel.initData` 的 `when(type)` **只有 bookSource/rssSource/httpTts 三支**
 * ⇒ `else -> null` ⇒ source 恒空 ⇒ `onSuccess` 走 `未找到书源` toast：**登录页永远打不开**。
 *
 * 修复＝补 `"autoTask"` 分支：按 id 取 `AutoTaskRule` 并经 `AutoTask.buildSource` 合成 BaseSource。
 * 该修复**成立的前提**＝合成 key 必须与 `AutoTaskService` 执行期构造的 key **同源**
 * （`"auto_task:{id}"`）——否则登录写入的 Cookie 落不到任务请求读取的槽位、登录「成功但无效」。
 * 故本用例以**行为断言**锁定该 key/字段契约，并以结构断言锁定分支已接线。
 */
class SourceLoginAutoTaskBranchTest {

    private val rule = AutoTaskRule(
        id = "rid-1",
        name = "任务名",
        header = """{"A":"B"}""",
        jsLib = "lib",
        concurrentRate = "1/1000",
        enabledCookieJar = false,
        loginUrl = "http://127.0.0.1:18091/login",
        loginUi = "ui-json",
        loginCheckJs = "check-js",
    )

    @Test
    fun `合成源 key 与执行期同源且字段透传`() {
        val src = AutoTask.buildSource(rule)
        // key 契约：必须与 AutoTaskService 执行期 `AutoTask.buildSource(task)` 逐字一致，
        // 否则登录 Cookie 槽位与任务请求槽位错位 ⇒ 登录无效。
        assertEquals("autoTask 合成源 key 必须为 auto_task:{id}", "auto_task:rid-1", src.getKey())
        assertEquals("显示名透传", "任务名", src.getTag())
        assertEquals("jsLib 透传", "lib", src.jsLib)
        assertEquals("header 透传", """{"A":"B"}""", src.header)
        assertEquals("并发率透传", "1/1000", src.concurrentRate)
        assertEquals("CookieJar 开关透传", false, src.enabledCookieJar)
        assertEquals("loginUrl 透传（登录页据此载入）", "http://127.0.0.1:18091/login", src.loginUrl)
        assertEquals("loginUi 透传", "ui-json", src.loginUi)
        assertEquals("loginCheckJs 透传", "check-js", src.loginCheckJs)
    }

    @Test
    fun `SourceLoginViewModel 已接线 autoTask 分支`() {
        val src = SourceFileProbe.sourceText("ui/login/SourceLoginViewModel.kt")
        assertEquals(
            "autoTask 分支必须在位（否则登录页恒显示未找到书源）",
            true,
            src.contains("\"autoTask\" -> appDb.autoTaskRuleDao.getById(sourceKey)?.let {")
        )
        assertEquals("分支必须调用 buildSource 合成 BaseSource", true, src.contains("AutoTask.buildSource(it)"))
        // 顺序守卫：若 `autoTask` 支落到 `else -> null` 之后（或缺失），when 永不命中该支 ⇒ 登录仍失效。
        val iAuto = src.indexOf("\"autoTask\" ->")
        val iElse = src.indexOf("else -> null", iAuto.coerceAtLeast(0))
        assertEquals("autoTask 分支必须在 else 兜底之前命中", true, iAuto >= 0 && iElse > iAuto)
    }
}
