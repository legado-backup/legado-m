package io.legado.app.lib.theme

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「套件自动套用一次性标记」的**存量回填**不变量（2026-09-24 主题设置体系失守修复配套）。
 *
 * 修复把「每次启动都套用套件」改为「一次性」后，已配置过的存量用户若不回填标记，
 * 会在升级后首启**再被套件覆盖一次**（主题 / 主页布局 / 顶栏包被改回）——本测试固化该回填。
 */
class ThemeRuntimeKeysAutoApplyMigrationTest {

    private fun source(rel: String): String {
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    @Test
    fun themeRuntimeKeys_providesIdempotentBackfill() {
        val code = source("src/main/java/io/legado/app/lib/theme/ThemeRuntimeKeys.kt")
        assertTrue(
            "必须提供 migrateAppearanceKitAutoApplyFlag（幂等回填）",
            code.contains("fun migrateAppearanceKitAutoApplyFlag(")
        )
        assertTrue(
            "回填必须写入一次性标记 appearanceKitAutoApplyDone",
            code.contains("PreferKey.appearanceKitAutoApplyDone")
        )
        assertTrue(
            "回填必须有哨兵键防重复执行",
            code.contains("appearanceKitAutoApplyMigratedKey")
        )
    }

    @Test
    fun appAttachBaseContext_invokesBackfill() {
        val code = source("src/main/java/io/legado/app/App.kt")
        assertTrue(
            "App.attachBaseContext 必须调用回填（否则存量用户升级后首启被覆盖一次）",
            code.contains("migrateAppearanceKitAutoApplyFlag(")
        )
    }
}