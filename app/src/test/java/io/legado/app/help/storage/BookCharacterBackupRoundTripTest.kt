package io.legado.app.help.storage

import com.google.gson.Gson
import io.legado.app.data.entities.BookCharacter
import io.legado.app.data.entities.BookCharacterRelation
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-50：书角角色 / 角色关系的「备份四处同名同文件」与 Gson 往返保真。
 *
 * 缺陷背景（用户可感）：`help/storage/` 目录下（Backup / Restore / ImportOldData）原本对角色表**零引用** ⇒
 * 换机 / 重装 / 清数据 / 恢复备份后，用户已建的角色与关系**全部丢失**；而同类数据
 * （划线 `highlights.json`、名场面书签 `sceneBookmarks.json`、订阅已读 `rssReadRecord.json`）
 * 均有备份 + 专项往返测试 ⇒ 属**遗漏**而非设计取舍。
 *
 * 四处同名同文件铁律：①`BackupSelectorConfig.allItems` ②`Backup.kt` 写出分支
 * ③`Restore.kt` 还原分支 ④**Web 备份硬编码全集**（`service/kernel/BackupKernel.buildBackupZip`，
 * **不走选择器** ⇒ 最易漏，历史上有 5 类曾在此静默缺失）⇒ 第 ④ 处由本文件专守。
 */
class BookCharacterBackupRoundTripTest {

    private fun read(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
        if (f == null) throw AssertionError("找不到源文件 $rel（工作目录 ${File(".").absolutePath}）")
        return f.readText().replace("\r\n", "\n")
    }

    private val charsFile = "bookCharacters.json"
    private val relsFile = "bookCharacterRelations.json"

    private val selector by lazy { read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt") }
    private val backup by lazy { read("src/main/java/io/legado/app/help/storage/Backup.kt") }
    private val restore by lazy { read("src/main/java/io/legado/app/help/storage/Restore.kt") }
    private val webBackup by lazy { read("src/main/java/io/legado/app/service/kernel/BackupKernel.kt") }

    @Test
    fun allFourPlacesUseTheSameFileNames() {
        assertTrue("① 选择器缺角色条目", selector.contains("BackupItem(\"bookCharacter\", \"$charsFile\""))
        assertTrue("① 选择器缺关系条目", selector.contains("BackupItem(\"bookCharacterRelation\", \"$relsFile\""))
        assertTrue("② 备份侧未写出角色", backup.contains("if (selectedFiles.contains(\"$charsFile\"))"))
        assertTrue("② 备份侧未写出关系", backup.contains("if (selectedFiles.contains(\"$relsFile\"))"))
        assertTrue("③ 恢复侧未读回角色", restore.contains("\"$charsFile\""))
        assertTrue("③ 恢复侧未读回关系", restore.contains("\"$relsFile\""))
        assertTrue(
            "④ Web 备份（硬编码全集、不走选择器）未登记 —— 会在换机后静默丢数据",
            webBackup.contains("writeListToJson(appDb.bookCharacterDao.allCharacters(), \"$charsFile\"")
        )
        assertTrue(
            "④ Web 备份未登记关系",
            webBackup.contains("writeListToJson(appDb.bookCharacterDao.allRelations(), \"$relsFile\"")
        )
    }

    @Test
    fun selectorRowsAreVisibleInBackupPicker() {
        assertTrue("角色条目须带可读名（否则勾选页显示为空/键名）", selector.contains("\"书角角色\""))
        assertTrue("关系条目须带可读名", selector.contains("\"角色关系\""))
    }

    @Test
    fun restoreInsertsCharactersBeforeRelationsAndFiltersOrphans() {
        val charAt = restore.indexOf("insertCharacter(it)")
        val relAt = restore.indexOf("insertRelation(it)")
        assertTrue("恢复侧须插入角色", charAt > 0)
        assertTrue("恢复侧须插入关系", relAt > 0)
        assertTrue(
            "顺序不可颠倒：先角色后关系（关系对角色有 FK+CASCADE，倒序会抛 SQLiteConstraintException）",
            charAt < relAt
        )
        assertTrue(
            "关系须按库内现存角色 id 过滤（防「只勾选关系」/旧包缺角色时插入悬空外键）",
            restore.contains("list.filter { it.fromCharacterId in aliveIds && it.toCharacterId in aliveIds }")
        )
    }

    @Test
    fun gsonRoundTripKeepsPrimaryAndForeignKeys() {
        val gson = Gson()
        val c1 = BookCharacter(id = 11, bookUrl = "https://example.invalid/b", name = "甲")
        val c2 = BookCharacter(id = 12, bookUrl = "https://example.invalid/b", name = "乙")
        val rel = BookCharacterRelation(
            id = 21,
            bookUrl = "https://example.invalid/b",
            fromCharacterId = 11,
            toCharacterId = 12,
            relationName = "师徒"
        )
        val chars = gson.fromJson(
            gson.toJson(listOf(c1, c2)), Array<BookCharacter>::class.java
        ).toList()
        val rels = gson.fromJson(
            gson.toJson(listOf(rel)), Array<BookCharacterRelation>::class.java
        ).toList()

        assertEquals("角色行数须保持", 2, chars.size)
        assertEquals("关系行数须保持", 1, rels.size)
        assertEquals("角色自增主键须保留（REPLACE 幂等的依据）", 11L, chars[0].id)
        assertEquals("角色归属书址须保留", "https://example.invalid/b", chars[0].bookUrl)
        // 关系的外键必须完整 —— 否则恢复后关系指向不存在的角色（FK 失败或图中断链）
        assertEquals("fromCharacterId 须保留", 11L, rels[0].fromCharacterId)
        assertEquals("toCharacterId 须保留", 12L, rels[0].toCharacterId)
        assertEquals("关系名须保留", "师徒", rels[0].relationName)
    }

    @Test
    fun backupChainIsR8Protected() {
        // 备份链路经 Gson ⇒ 实体成员被 R8 剥离会导致恢复为空；两类实体均在 data.entities 包，
        // 由 `-keep class **.data.entities.**{*;}` 统一保护（proguard-rules.pro）
        val proguard = read("proguard-rules.pro")
        assertTrue(
            "data.entities 包须保持 R8 keep 规则（否则恢复出来是空对象）",
            proguard.contains("-keep class **.data.entities.**{*;}")
        )
    }
}
