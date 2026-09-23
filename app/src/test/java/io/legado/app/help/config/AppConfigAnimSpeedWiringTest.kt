package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B1·R5 配置接线不变量：`AppConfig.pageTurnAnimSpeedTier` 必须
 * ①读写 `PreferKey.pageTurnAnimSpeed` 同一键 ②读侧带 `coerceIn` 兜底 ③毫秒映射只走 `PageTurnAnimSpeed` 单源。
 *
 * 为什么用源码不变量：`AppConfig` 是 object 且类初始化即读 `appCtx` 的 prefs（依赖 ContentProvider），
 * 本项目单测无 Robolectric ⇒ 无法实例化断言；档位→毫秒的**纯逻辑**已由 `PageTurnAnimSpeedTest` 覆盖。
 */
class AppConfigAnimSpeedWiringTest {

    private fun code(): String {
        val rel = "src/main/java/io/legado/app/help/config/AppConfig.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        return f.readLines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun r5TierPropertyWiresToSingleSourceWithClamp() {
        val t = code()
        val start = t.indexOf("var pageTurnAnimSpeedTier")
        assertTrue("未找到 pageTurnAnimSpeedTier 属性", start >= 0)
        val body = t.substring(start, t.indexOf("get() =", start).let { if (it < 0) start + 400 else it + 400 })

        assertTrue("读侧必须用 PreferKey.pageTurnAnimSpeed", body.contains("PreferKey.pageTurnAnimSpeed"))
        assertTrue("读侧必须 coerceIn 兜底非法档位", body.contains("coerceIn("))
        assertTrue("毫秒映射必须走 PageTurnAnimSpeed 单源", body.contains("PageTurnAnimSpeed"))
        assertTrue("写侧必须落同一键", body.contains("putPrefInt(PreferKey.pageTurnAnimSpeed"))
    }
}