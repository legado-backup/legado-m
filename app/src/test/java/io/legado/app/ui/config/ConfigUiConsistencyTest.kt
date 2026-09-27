package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 配置页面的**一致性不变量**（REQ-08 非空兜底 + 2026-09-27 底栏搜索开关退役）。
 *
 * 覆盖：
 * ① 备份失败 toast 的非空兜底（`BackupConfigFragment` 的**两个** catch 分支）；
 * ② 已删开关在设置页与底栏包管理页**不得残留**（残留会出现「点了没反应」的死开关）。
 */
class ConfigUiConsistencyTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val backupFragment by lazy {
        read("src/main/java/io/legado/app/ui/config/BackupConfigFragment.kt")
    }
    private val otherConfig by lazy { read("src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt") }
    private val navBarManage by lazy {
        read("src/main/java/io/legado/app/ui/config/NavigationBarManageActivity.kt")
    }

    /**
     * W7 8.2 / REQ-30：文章级离线预取开关须在「其他设置」页接线（与 W5 音量键开关同族同形）。
     */
    @Test
    fun imageArticlePrefetchSwitchIsWiredInOtherConfig() {
        assertTrue(
            "OtherConfigFragment 须登记 `imageArticlePrefetch` 开关（否则设置项根本不存在）",
            otherConfig.contains("key = PreferKey.imageArticlePrefetch")
        )
    }

    @Test
    fun bothBackupFailureBranchesHaveNonNullFallback() {
        val pattern = """e.localizedMessage?.takeIf { it.isNotBlank() } ?: "未知错误""""
        val count = Regex(Regex.escape(pattern)).findAll(backupFragment).count()
        assertEquals(
            "两处 catch（S3CapacityFullException / Throwable）均须非空兜底",
            2,
            count
        )
    }

    @Test
    fun removedBottomSearchSwitchIsGoneFromSettings() {
        assertFalse(
            "设置页仍残留已删开关的声明",
            otherConfig.contains("key = PreferKey.floatingBottomBarHideSearch")
        )
        assertFalse(
            "底栏包管理页仍残留已删配置行（断言赋值而非词面：注释里会提到它为何被删）",
            navBarManage.contains("config.hideSearchInFloatingStyle =")
        )
    }

    @Test
    fun stagedStringsRemovalKeepsCommentedTombstone() {
        // 双 strings 的删除以注释墓碑记录，便于后续追溯「这条文案为何消失」
        val values = read("src/main/res/values/strings.xml")
        val valuesZh = read("src/main/res/values-zh/strings.xml")
        assertFalse("英文文案仍在使用（应为已删墓碑）", values.contains("""name="bottom_bar_hide_search""""))
        assertFalse("中文文案仍在使用（应为已删墓碑）", valuesZh.contains("""name="bottom_bar_hide_search""""))
        assertTrue("英文侧应留删除墓碑", values.contains("bottom_bar_hide_search"))
        assertTrue("中文侧应留删除墓碑", valuesZh.contains("bottom_bar_hide_search"))
    }
}