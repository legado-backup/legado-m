package io.legado.app.api.controller

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.5 / REQ-33：Web 备份（④ 处）与备份概览须包含名场面书签。
 *
 * 为什么单独测：`executeWebBackup` **硬编码全集、不走选择器**（AD-20）⇒ 选择器加了条目它不会自动跟上；
 * 概览（`generateBackupOverview`）若漏项，用户在选择备份内容时看不到该类别的体量。
 * 本仓已有先例（订阅已读记录曾漏写）。
 */
class BackupControllerSceneBookmarkTest {

    private val controller by lazy {
        listOf(
            File("src/main/java/io/legado/app/api/controller/BackupController.kt"),
            File("../app/src/main/java/io/legado/app/api/controller/BackupController.kt"),
            File("app/src/main/java/io/legado/app/api/controller/BackupController.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun webBackupWritesSceneBookmarksJson() {
        assertTrue(
            "Web 备份须写出 sceneBookmarks.json（④ 处）",
            controller.contains(
                """writeListToJson(appDb.sceneBookmarkDao.all, "sceneBookmarks.json", webBackupPath)"""
            )
        )
    }

    @Test
    fun backupOverviewListsSceneBookmarks() {
        assertTrue(
            "概览须登记 sceneBookmarks.json（否则用户看不到该类别体量）",
            controller.contains("""BackupItemDef("sceneBookmarks.json"""")
        )
    }
}
