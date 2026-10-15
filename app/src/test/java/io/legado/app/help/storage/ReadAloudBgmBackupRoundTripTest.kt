package io.legado.app.help.storage

import com.google.gson.Gson
import io.legado.app.data.entities.ReadAloudBgmGroup
import io.legado.app.data.entities.ReadAloudBgmTrack
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-51：朗读配乐 / 音效（分组 + 曲目 + 音频文件）的「备份四处同名同文件」与 Gson 往返保真。
 *
 * 缺陷背景（用户可感）：`read_aloud_bgm_groups` / `read_aloud_bgm_tracks` 两张表此前在
 * `help/storage/` 下**零引用** ⇒ 换机 / 重装 / 清数据 / 恢复备份后，用户导入的分组与音频全丢；
 * 且音频来自**用户本地文件**（非可下载产物）→ **无法重建**，与同类数据（划线 `highlights.json`、
 * 名场面书签 `sceneBookmarks.json`、背景图 `bg` 目录）均已入备份的既有口径不一致 ⇒ 属遗漏而非取舍。
 *
 * 四处同名同文件铁律：①`BackupSelectorConfig.allItems` ②`Backup.kt` 写出分支
 * ③`Restore.kt` 还原分支 ④**Web 备份硬编码全集**（`service/kernel/BackupKernel.buildBackupZip`，
 * **不走选择器** ⇒ 最易漏，历史上有 5 类曾在此静默缺失）。
 *
 * 与 NEW-50 的差异点（本类额外守住的）：本条目是**目录项**（同 `bg`），除元数据 JSON 外还承载
 * **音频文件本体**，故必须同守「音频先落盘 → 再落库」「filePath 按落盘名重算」
 * 「目录名与存储侧单源」三条，否则恢复出来是「有曲目、点开即文件缺失」的空壳。
 */
class ReadAloudBgmBackupRoundTripTest {

    private fun read(rel: String): String {
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
        if (f == null) throw AssertionError("找不到源文件 $rel（工作目录 ${File(".").absolutePath}）")
        return f.readText().replace("\r\n", "\n")
    }

    private val groupsFile = "readAloudBgmGroups.json"
    private val tracksFile = "readAloudBgmTracks.json"
    private val audioDir = "readAloudAudio"

    private val selector by lazy { read("src/main/java/io/legado/app/help/storage/BackupSelectorConfig.kt") }
    private val backup by lazy { read("src/main/java/io/legado/app/help/storage/Backup.kt") }
    private val restore by lazy { read("src/main/java/io/legado/app/help/storage/Restore.kt") }
    private val webBackup by lazy { read("src/main/java/io/legado/app/service/kernel/BackupKernel.kt") }
    private val manageActivity by lazy {
        read("src/main/java/io/legado/app/ui/book/read/config/ReadAloudBgmManageActivity.kt")
    }

    @Test
    fun allFourPlacesUseTheSameFileNames() {
        assertTrue("① 选择器缺朗读配乐条目", selector.contains("BackupItem(\"readAloudBgm\", \"$audioDir\""))
        assertTrue(
            "② 备份侧未写出分组元数据",
            backup.contains("writeListToJson(appDb.readAloudBgmDao.groups(), \"$groupsFile\"")
        )
        assertTrue("② 备份侧未写出曲目元数据", backup.contains("\"$tracksFile\""))
        assertTrue(
            "② 备份侧未接音频落盘分支（条目键即目录名，与 bg 同口径）",
            backup.contains("if (selectedFiles.contains(READ_ALOUD_AUDIO_DIR))")
        )
        assertTrue("③ 恢复侧未读回分组", restore.contains("\"$groupsFile\""))
        assertTrue("③ 恢复侧未读回曲目", restore.contains("\"$tracksFile\""))
        assertTrue("③ 恢复侧未接入总流程（否则备份了也不还原）", restore.contains("restoreReadAloudBgm(path)"))
        assertTrue(
            "④ Web 备份（硬编码全集、不走选择器）未登记 —— 会在换机后静默丢数据",
            webBackup.contains("Backup.stageReadAloudBgm(webBackupPath)")
        )
    }

    @Test
    fun selectorRowIsVisibleInBackupPicker() {
        assertTrue("条目须带可读名（否则勾选页显示为空/键名）", selector.contains("\"朗读配乐与音效\""))
    }

    @Test
    fun audioDirMatchesStorageSideAndIsSingleSourced() {
        assertTrue(
            "备份侧须定义音频目录常量（单源，防三处硬编码漂移）",
            backup.contains("internal const val READ_ALOUD_AUDIO_DIR = \"$audioDir\"")
        )
        assertTrue(
            "存储侧（管理页）实际落盘目录名须与备份常量一致（漂移即备份拿不到音频）",
            manageActivity.contains("readAloudAudio/$" + "currentAssetType")
        )
        assertTrue("恢复侧须复用同一常量（不得硬编码目录名）", restore.contains("Backup.READ_ALOUD_AUDIO_DIR"))
    }

    @Test
    fun restoreWritesAudioBeforeDbAndInsertsGroupsBeforeTracks() {
        val groupAt = restore.indexOf("insertGroup(it)")
        val trackAt = restore.indexOf("insertTrack(")
        assertTrue("恢复侧须插入分组", groupAt > 0)
        assertTrue("恢复侧须插入曲目", trackAt > 0)
        assertTrue("分组须先于曲目（曲目行引用 groupId，倒序会落进错误分组）", groupAt < trackAt)
        assertTrue(
            "音频须先落盘再落库（否则插入时 filePath 指向不存在的文件 ⇒ 预览一律「文件缺失」）",
            restore.indexOf("copyRecursively") in 1 until trackAt
        )
        assertTrue(
            "filePath 须按落盘文件名重算（备份记录的是原设备绝对路径，换机/多用户下 filesDir 会变）",
            restore.contains("track.copy(filePath = existing.absolutePath)")
        )
        assertTrue(
            "音频目录不存在时须静默跳过（旧包 / 未勾选该条目时不得抛错中断整包恢复）",
            restore.contains("if (audioSrc.isDirectory)")
        )
    }

    @Test
    fun gsonRoundTripKeepsPrimaryAndForeignKeys() {
        val gson = Gson()
        val group = ReadAloudBgmGroup(id = 7, name = "片头乐", assetType = ReadAloudBgmTrack.TYPE_SFX, sortOrder = 3)
        val track = ReadAloudBgmTrack(
            id = 19,
            groupId = 7,
            assetType = ReadAloudBgmTrack.TYPE_SFX,
            name = "雨声",
            fileName = "rain.mp3",
            filePath = "/data/user/0/pkg/files/$audioDir/sfx/1_rain.mp3",
            tags = "自然",
            checksum = "abc",
            durationMs = 12345L,
            defaultVolume = 0.8f,
            enabled = false,
            sortOrder = 2
        )
        val groups = gson.fromJson(gson.toJson(listOf(group)), Array<ReadAloudBgmGroup>::class.java).toList()
        val tracks = gson.fromJson(gson.toJson(listOf(track)), Array<ReadAloudBgmTrack>::class.java).toList()

        assertEquals("分组行数须保持", 1, groups.size)
        assertEquals("曲目行数须保持", 1, tracks.size)
        assertEquals("分组自增主键须保留（REPLACE 幂等的依据）", 7L, groups[0].id)
        assertEquals("曲目自增主键须保留", 19L, tracks[0].id)
        assertEquals("曲目外键 groupId 须保留（否则恢复后落进错误分组）", 7L, tracks[0].groupId)
        assertEquals("资产类型须保留（bgm/sfx 分流）", ReadAloudBgmTrack.TYPE_SFX, tracks[0].assetType)
        assertEquals(
            "落盘文件名须保留（恢复侧正是靠它重算 filePath）",
            "1_rain.mp3",
            File(tracks[0].filePath).name
        )
        assertEquals("默认音量须保留", 0.8f, tracks[0].defaultVolume, 0.0001f)
        assertEquals("启用状态须保留（停用项也要进备份，否则恢复后丢配置）", false, tracks[0].enabled)
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
