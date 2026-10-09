package io.legado.app.ui.main

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * unify-changelog-and-release 接线配对测试（`MainActivity.upVersion()`）。
 *
 * `upVersion()` 依赖 `Activity` / `assets`，无法在 JVM 直接执行 ⇒ 按本仓既有惯例以**源码契约**固化：
 * 「更新版本后」弹窗必须走 `UpdateLogDigest` 区间视图（去日期 + 分节合并），
 * 且**不得**再整份展示 `updateLog.md` 全文；同时必须持久化上一版本名。
 */
class UpgradeChangelogWiringTest {

    private fun mainActivity(): String = SourceFileProbe.sourceText("ui/main/MainActivity.kt")

    @Test
    fun dialogUsesDigestInsteadOfRawLog() {
        val src = mainActivity()
        assertTrue(
            "弹窗内容须经 UpdateLogDigest 区间裁剪",
            src.contains("UpdateLogDigest.digest(log, preVersionName, appInfo.versionName)")
        )
        assertFalse(
            "不得再把 updateLog.md 全文直接交给弹窗",
            src.contains(", log, TextDialog.Mode.MD)")
        )
    }

    @Test
    fun persistsPreviousVersionNameAcrossUpgrade() {
        val src = mainActivity()
        assertTrue(
            "升级时须先读取上一版本名（此刻仍是旧值）",
            src.contains("val preVersionName = LocalConfig.appVersionName")
        )
        assertTrue(
            "升级时须写回当前版本名，供下次升级确定区间起点",
            src.contains("LocalConfig.appVersionName = appInfo.versionName")
        )
    }

    @Test
    fun emptyDigestSkipsDialogWithoutBlocking() {
        val src = mainActivity()
        assertTrue(
            "无可展示内容时必须直接 resume，不弹空弹窗",
            src.contains("if (digest == null)") && src.contains("block.resume(null)")
        )
    }
}