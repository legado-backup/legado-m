package io.legado.app.ui.download

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 宿主刷新钩子覆盖不变量回归测试（B7 R29/C1，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 C1）：「一处补了、一处漏了」——`ReadRecordFragment` 的 AndroidView
 * 宿主调了 `applyTopBarStyle(force = true)`，而 `DownloadManageScreen` 的 `AndroidView.update`
 * 只 `submitItems`、从不刷新 ⇒ 主题切换后该页标签栏不跟随。
 *
 * `AndroidView.update` 需真实 Compose 环境，本项目单测无 Robolectric，故按源码结构不变量固化：
 * ①该宿主必须出现刷新调用；②宿主登记清单必须登记它（门禁 17 的判定输入）。
 */
class DownloadHostRefreshHookTest {

    private fun read(relFromRepoRoot: String): String {
        val candidates = listOf(
            File(relFromRepoRoot),
            File("../$relFromRepoRoot"),
            File("../../$relFromRepoRoot")
        )
        return candidates.firstOrNull { it.isFile }?.readText()
            ?: throw AssertionError("未找到文件（工作目录=${File(".").absolutePath}）：$relFromRepoRoot")
    }

    @Test
    fun downloadManageScreen_callsTopBarRefreshHook() {
        val text = read("src/main/java/io/legado/app/ui/download/DownloadManageScreen.kt")
        assertTrue("宿主应调用 applyTopBarStyle 刷新标签栏", text.contains("applyTopBarStyle"))
    }

    @Test
    fun hostRefreshRegistry_listsDownloadManageScreen() {
        val registry = read("ai_tests/config/host_refresh_registry.json")
        assertTrue(
            "宿主登记清单应包含 DownloadManageScreen（门禁 17 的判定输入）",
            registry.contains("DownloadManageScreen.kt")
        )
    }
}