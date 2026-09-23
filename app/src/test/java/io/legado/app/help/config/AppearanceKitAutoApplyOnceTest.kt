package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 首装「自动套用暗夜紫外观套件」必须**一次性**（2026-09-24 主题设置体系失守修复）。
 *
 * 缺陷：`App.kt` 原判据只有 `firstInstallDarkPurple`（读 `theme_first_install_done`），
 * 而该键语义是「**本机为全新安装**」——迁移后**长期为 true** ⇒ 每次启动都 `apply(kit)`，
 * 把用户此后选择的主题 / 外观套件 / 主页布局 preset / 顶栏包**静默还原**
 * （真机实测：注入的面 token 重启后变回套件值、`mainLayoutPreset` 与 `defaultTopBarStyle` 被改回 regular）。
 */
class AppearanceKitAutoApplyOnceTest {

    @Test
    fun shouldApply_onlyOnFreshInstallWithoutPriorAutoApply() {
        assertTrue(
            "全新安装 + 从未自动套用 ⇒ 应套用",
            AppearanceKitManager.shouldAutoApplyDarkPurpleKitOnce(
                isFreshInstall = true, alreadyAutoApplied = false
            )
        )
        assertFalse(
            "已自动套用过 ⇒ 不得再套用（否则用户改的主题会被还原）",
            AppearanceKitManager.shouldAutoApplyDarkPurpleKitOnce(
                isFreshInstall = true, alreadyAutoApplied = true
            )
        )
        assertFalse(
            "非全新安装（存量用户）⇒ 不得套用",
            AppearanceKitManager.shouldAutoApplyDarkPurpleKitOnce(
                isFreshInstall = false, alreadyAutoApplied = false
            )
        )
        assertFalse(
            AppearanceKitManager.shouldAutoApplyDarkPurpleKitOnce(
                isFreshInstall = false, alreadyAutoApplied = true
            )
        )
    }

    /** 接线不变量：`App.kt` 的套件自动套用必须由判据函数 + 一次性标记共同把关。 */
    @Test
    fun appStartup_mustGuardKitApplyWithOneShotFlag() {
        val rel = "src/main/java/io/legado/app/App.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        val code = file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")

        assertTrue(
            "App 启动必须用 shouldAutoApplyDarkPurpleKitOnce 判据（不得只判 firstInstallDarkPurple）",
            code.contains("shouldAutoApplyDarkPurpleKitOnce(")
        )
        assertTrue(
            "必须读写一次性标记 appearanceKitAutoApplyDone",
            code.contains("PreferKey.appearanceKitAutoApplyDone")
        )
        assertFalse(
            "不得再出现「仅以 firstInstallDarkPurple 直接 apply(kit)」的写法",
            Regex("if\\s*\\(\\s*firstInstallDarkPurple\\s*\\)\\s*\\{\\s*AppearanceKitManager\\.apply")
                .containsMatchIn(code.replace("\n", " "))
        )
    }
}