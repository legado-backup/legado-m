package io.legado.app.api.controller

import io.legado.app.help.storage.BackupSelectorConfig
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `BackupController` 的**契约不变量**（REQ-05 / REQ-07 / REQ-08）。
 *
 * 为何用源码不变量：`BackupController` 依赖 `appCtx` + NanoHTTPD 运行时，纯 JVM 无法驱动其
 * 落库路径；而这三条契约（Web 备份覆盖全集 / 纳共享锁 / 失败消息非空）**编译期完全无感**，
 * 漏改即静默失灵 —— 正是「备份选择器加了类别但 Web 备份不跟上」这类缺陷的成因。
 * 运行时往返（Web 备份产物含全部类别）由 §12.3 D3-III 真机档覆盖。
 */
class BackupControllerContractTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val controller by lazy {
        read("src/main/java/io/legado/app/api/controller/BackupController.kt")
    }
    private val selector by lazy {
        read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt")
    }

    /** Web 备份**硬编码全集、不走选择器** ⇒ 选择器每加一条都可能漏写，必须逐条登记在此。 */
    @Test
    fun webBackupWritesEveryCategoryFile() {
        listOf(
            "bookshelf.json", "bookmark.json", "bookGroup.json", "bookSource.json",
            "rssSources.json", "rssStar.json", "replaceRule.json", "readRecord.json",
            "readRecordDetail.json", "searchHistory.json", "sourceSub.json",
            "txtTocRule.json", "httpTTS.json", "keyboardAssists.json", "dictRule.json",
            "servers.json", "config.xml", "videoConfig.xml",
            // 2026-09-27 补全的 5 类（此前漏写）
            "highlights.json", "autoTask.json", "ttsCastingTemplates.json",
            "stageCoverGallery", "stageRuntimeSourceCaches",
            // 既有的目录类
            "stageBackgroundImageFiles", "stageBookCache", "stageBookChapterForCache",
            "stageHighlightRuleBackgroundFiles"
        ).forEach { token ->
            assertTrue("Web 备份未写出：$token", controller.contains(token))
        }
    }

    @Test
    fun selectorCategoriesAreConsistentWithWebBackupExpectations() {
        // 选择器条目数下界：防止「误删条目」让上面的清单悄悄失真
        val count = Regex("""BackupItem\(\s*"[^"]+",""").findAll(
            selector.lines().filterNot { it.trimStart().startsWith("//") }.joinToString("\n")
        ).count()
        assertTrue("选择器条目数异常（期望 ≥ 31，实得 $count）", count >= 31)
    }

    @Test
    fun webBackupIsWrappedBySharedStorageLock() {
        assertTrue(
            "Web 备份对外入口须经 BackupRestoreLock 包裹（REQ-07）",
            controller.contains("BackupRestoreLock.withStorageLock { executeWebBackupUnlocked() }")
        )
        assertTrue(
            "未加锁实现必须私有（防绕过锁直调）",
            controller.contains("private suspend fun executeWebBackupUnlocked()")
        )
    }

    @Test
    fun backupFailureMessageIsNeverNull() {
        assertTrue(
            "失败回执须非空兜底（REQ-08），否则响应体出现 \"备份失败: null\"",
            controller.contains("""error.message?.takeIf { it.isNotBlank() } ?: "未知错误"""")
        )
        assertFalse(
            "旧的裸插值写法必须已移除",
            controller.contains("""备份失败: ${'$'}{error.message}""")
        )
    }

    @Test
    fun selectorItemKeysAreResolvableForParityAudit() {
        // 供跨包对等性审计使用的 key 采样（BackupItem 第一个参数）
        val keys = Regex("""BackupItem\("([^"]+)",""")
            .findAll(selector.lines().filterNot { it.trimStart().startsWith("//") }.joinToString("\n"))
            .map { it.groupValues[1] }
            .toList()
        assertEquals("关键类别 key 必须存在", true, keys.containsAll(listOf("highlight", "autoTask", "coverGallery")))
    }
}