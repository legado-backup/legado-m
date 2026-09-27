package io.legado.app.help.storage

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W4 / REQ-17（AD-08 / AD-20）：`rssReadRecord.json` 的**四处同名同文件**铁律。
 *
 * 实证背景：选择器（`BackupSelectorConfig.allItems`）只决定**裁剪文件名集合**；
 * 真正写出/还原分别在 `Backup`/`Restore`，而 Web 备份**硬编码全集、不走选择器**
 * ⇒ 四处任一漏改即出现「勾了却没备份 / 备份了却不还原 / Web 备份缺项」三种静默失效。
 */
class BackupRssReadRecordParityTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val backup by lazy { read("src/main/java/io/legado/app/help/storage/Backup.kt") }
    private val restore by lazy { read("src/main/java/io/legado/app/help/storage/Restore.kt") }
    private val selector by lazy { read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt") }

    @Test
    fun fourSitesUseIdenticalFileName() {
        assertTrue(
            "① Backup 写出分支缺 rssReadRecord.json",
            backup.contains("""selectedFiles.contains("rssReadRecord.json")""") &&
                backup.contains("""appDb.rssReadRecordDao.getRecords(), "rssReadRecord.json"""")
        )
        assertTrue(
            "② Restore 还原分支缺 rssReadRecord.json",
            restore.contains("""fileToListT<RssReadRecord>(path, "rssReadRecord.json")""")
        )
        assertTrue(
            "③ 选择器缺该条目（用户根本看不到这个类别）",
            selector.contains("""BackupItem("rssReadRecord", "rssReadRecord.json"""")
        )
    }

    @Test
    fun restoreUsesIgnoreInsertSemantics() {
        assertTrue(
            "还原语义须保持 insertRecord（@Insert IGNORE ⇒ 不推翻本机进度）",
            restore.contains("appDb.rssReadRecordDao.insertRecord(*it.toTypedArray())")
        )
    }
}