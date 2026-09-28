package io.legado.app.help.storage

import com.google.gson.Gson
import io.legado.app.data.entities.SceneBookmark
import io.legado.app.help.book.SceneBookmarkHelper
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.5 / REQ-33：名场面书签的**备份四处同名同文件**与**往返保真**。
 *
 * 背景：本仓「备份 ↔ 恢复」有四处必须同名同文件（`BackupSelectorConfig.allItems` / `Backup` 写出分支 /
 * `Restore` 还原分支 / `BackupController.executeWebBackup`），且 **Web 备份是硬编码全集、不走选择器** ⇒
 * 只加选择器条目不会自动跟上（既有先例：曾有 5 类在 Web 备份路径静默缺失）。`BackupRestoreParityTest`
 * 只覆盖前三处，第 ④ 处由本文件守着。
 *
 * 另锁「恢复后 AI 描述保留」：`desc` / `tags` 是行内字段，Gson 往返必须完整（含 `@Keep` 防 R8 剥离签名）。
 */
class SceneBookmarkBackupRoundTripTest {

    private fun read(rel: String): String =
        listOf(java.io.File(rel), java.io.File("../app/$rel"), java.io.File("app/$rel"))
            .first { it.isFile }
            .readText()

    private val fileName = "sceneBookmarks.json"

    @Test
    fun allFourPlacesUseTheSameFileName() {
        val selector = read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt")
        val backup = read("src/main/java/io/legado/app/help/storage/Backup.kt")
        val restore = read("src/main/java/io/legado/app/help/storage/Restore.kt")
        val webBackup = read("src/main/java/io/legado/app/api/controller/BackupController.kt")

        assertTrue("① 选择器缺条目", selector.contains("BackupItem(\"sceneBookmark\", \"$fileName\""))
        assertTrue("② 备份侧未写出", backup.contains("if (selectedFiles.contains(\"$fileName\"))"))
        assertTrue("③ 恢复侧未读回", restore.contains("\"$fileName\""))
        assertTrue(
            "④ Web 备份（硬编码全集、不走选择器）未登记 —— 会在换机后静默丢数据",
            webBackup.contains("writeListToJson(appDb.sceneBookmarkDao.all, \"$fileName\"")
        )
    }

    @Test
    fun selectorRowIsVisibleInBackupPicker() {
        val selector = read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt")
        val row = selector.substringAfter("BackupItem(\"sceneBookmark\"")
        assertTrue(
            "选择器条目须带可读名（否则勾选页显示为空/键名）",
            row.take(80).contains("名场面书签")
        )
    }

    @Test
    fun gsonRoundTripKeepsDescTagsAndAnchor() {
        val gson = Gson()
        val source = SceneBookmark(
            id = 7,
            time = 1_700_000_000_000,
            bookUrl = "https://example.invalid/book",
            bookName = "书",
            bookAuthor = "作者",
            chapterIndex = 3,
            chapterName = "第三章",
            contentKind = SceneBookmarkHelper.KIND_IMAGE,
            anchor = SceneBookmarkHelper.imageAnchor("https://example.invalid/a.jpg", "https://example.invalid/p/1"),
            text = "原文片段",
            desc = "AI 生成的一句话描述",
            tags = SceneBookmarkHelper.tagsToJson(listOf("燃", "转折")),
            style = ""
        )
        val json = gson.toJson(listOf(source))
        val back = gson.fromJson(json, Array<SceneBookmark>::class.java).toList()

        assertEquals("行数须保持", 1, back.size)
        val restored = back.first()
        assertEquals("AI 描述必须随备份保留", "AI 生成的一句话描述", restored.desc)
        assertEquals("标签必须随备份保留", listOf("燃", "转折"), SceneBookmarkHelper.tagsFromJson(restored.tags))
        assertEquals("自增主键须保留（REPLACE 幂等的依据）", 7L, restored.id)
        assertEquals("图片路径路线依据须保留", SceneBookmarkHelper.KIND_IMAGE, restored.contentKind)
        assertEquals(
            "图片锚点须完整（含跳回所需的 articleLink）",
            "https://example.invalid/p/1",
            SceneBookmarkHelper.articleLinkOf(restored.anchor)
        )
    }

    @Test
    fun entityKeepsR8AnnotationForBackupChain() {
        val entity = SourceFileProbe.sourceText("data/entities/SceneBookmark.kt")
        assertTrue(
            "备份链路经 Gson ⇒ 实体必须 @Keep（否则 R8 剥离成员致恢复为空）",
            entity.contains("@Keep")
        )
    }
}
