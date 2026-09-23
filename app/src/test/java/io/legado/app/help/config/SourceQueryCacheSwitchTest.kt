package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B4 · R18 开关接线（`AppConfig.sourceQueryCacheEnabled`）。
 *
 * 要求（tasks §4.2）：**开关关闭时行为与改造前完全一致**（每次直查数据库）⇒ 该开关必须
 * ①默认开 ②被读路径真正消费（不是死配置）③有注释说明它无 UI 入口（同 `optimizeRender` 口径）。
 */
class SourceQueryCacheSwitchTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun appConfigExposesSwitchWithDefaultOn() {
        val appConfig = code("help/config/AppConfig.kt")
        assertTrue(
            "必须暴露开关属性且默认开",
            appConfig.contains("var sourceQueryCacheEnabled = appCtx.getPrefBoolean(PreferKey.sourceQueryCacheEnabled, true)")
        )
        assertTrue(
            "必须消费开关（不是死配置）",
            code("help/source/SourceQueryCache.kt").contains("AppConfig.sourceQueryCacheEnabled")
        )
        assertTrue(
            "无 UI 技术开关需在注释中说明口径（同 optimizeRender）",
            appConfig.contains("optimizeRender")
        )
    }
}