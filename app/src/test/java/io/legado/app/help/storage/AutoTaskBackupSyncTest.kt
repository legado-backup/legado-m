package io.legado.app.help.storage

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B2 · R8「自动任务规则纳入备份/恢复」的**三处同步**不变量。
 *
 * 为什么值得测（设计文档明确警示）：备份文件名在**三处独立书写**——
 * ①`BackupSelectorConfig` 条目表 ②`Backup.backupFileNames` 清单 ③`Backup` 导出分支
 * （外加 ④`Restore` 恢复分支）。任一处漏改都会造成**静默失灵**：
 * 选择器勾了但导出不写 / 清单有但恢复不导 —— 且编译期完全无感。
 *
 * 另锁两条语义：恢复分支必须 ①按 REPLACE 幂等导入 ②**导入后立即重排**（否则「恢复了却不跑」）。
 */
class AutoTaskBackupSyncTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val selector by lazy { read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt") }
    private val backup by lazy { read("src/main/java/io/legado/app/help/storage/Backup.kt") }
    private val restore by lazy { read("src/main/java/io/legado/app/help/storage/Restore.kt") }

    @Test
    fun selectorDeclaresAutoTaskItemWithDatabaseCategory() {
        assertTrue(
            "选择器须登记 autoTask 条目（类别=数据库，名称=自动任务）",
            selector.contains("""BackupItem("autoTask", "autoTask.json", "自动任务", "数据库")""")
        )
    }

    @Test
    fun backupListAndExportBranchBothCoverAutoTask() {
        assertTrue("清单 backupFileNames 须含 autoTask.json", backup.contains("\"autoTask.json\""))
        assertTrue("导出分支须按勾选写出 autoTask.json", backup.contains("selectedFiles.contains(\"autoTask.json\")"))
        assertTrue("导出内容须来自规则表", backup.contains("autoTaskRuleDao.all()"))
    }

    @Test
    fun restoreBranchImportsIdempotentlyAndReschedules() {
        assertTrue("恢复分支须读取 autoTask.json", restore.contains("fileToListT<io.legado.app.model.AutoTaskRule>(path, \"autoTask.json\")"))
        assertTrue("导入须走 REPLACE 语义的 insert（幂等）", restore.contains("appDb.autoTaskRuleDao.insert("))
        val insertAt = restore.indexOf("appDb.autoTaskRuleDao.insert(")
        val refreshAt = restore.indexOf("AutoTask.refreshSchedule()", insertAt)
        assertTrue("导入后必须立即重排（否则规则在库但闹钟未建立）", refreshAt > insertAt)
        assertTrue("旧备份缺该文件必须静默跳过（?.let 空安全）", restore.contains("autoTask.json\")?.let"))
    }

    @Test
    fun backupFileNamesListIsStillConsistentForHighlightsPrecedent() {
        // 同语义既有条目不得因本次改动被破坏（防误删/错位）
        assertTrue(selector.contains("""BackupItem("highlight", "highlights.json", "划线批注", "数据库")"""))
        assertTrue(backup.contains("\"highlights.json\""))
        assertTrue(restore.contains("fileToListT<BookHighlight>(path, \"highlights.json\")"))
    }
}