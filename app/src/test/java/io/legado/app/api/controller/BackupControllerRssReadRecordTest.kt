package io.legado.app.api.controller

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-17：Web 备份（④ 处）与备份概览须包含订阅已读记录。
 *
 * 为什么单独测：`executeWebBackup` **硬编码全集、不走选择器**（AD-20）⇒ 选择器加了条目它不会自动跟上；
 * 概览（`generateBackupOverview`）若漏项，用户在选择备份内容时看不到该类别的体量。
 */
class BackupControllerRssReadRecordTest {

    private val controller by lazy {
        // 一期 §2.3.3：备份业务已下沉到内核 ⇒ 断言须同时覆盖两处源码
        listOf(
            File("src/main/java/io/legado/app/api/controller/BackupController.kt"),
            File("../app/src/main/java/io/legado/app/api/controller/BackupController.kt"),
            File("app/src/main/java/io/legado/app/api/controller/BackupController.kt")
        ).first { it.isFile }.readText() +
            "\n" + listOf(
            File("src/main/java/io/legado/app/service/kernel/BackupKernel.kt"),
            File("../app/src/main/java/io/legado/app/service/kernel/BackupKernel.kt"),
            File("app/src/main/java/io/legado/app/service/kernel/BackupKernel.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun webBackupWritesRssReadRecordJson() {
        assertTrue(
            "Web 备份须写出 rssReadRecord.json（④ 处）",
            controller.contains("""writeListToJson(appDb.rssReadRecordDao.getRecords(), "rssReadRecord.json", webBackupPath)""")
        )
    }

    @Test
    fun backupOverviewListsRssReadRecord() {
        assertTrue(
            "概览须登记 rssReadRecord.json（否则用户看不到该类别体量）",
            controller.contains("""BackupItemDef("rssReadRecord.json"""")
        )
    }
}