package io.legado.app.help.storage

import android.app.Application
import android.content.Context
import androidx.test.core.app.ApplicationProvider
import io.legado.app.data.repository.CoverGalleryRepository
import io.legado.app.help.DirectLinkUpload
import io.legado.app.help.config.ReadBookConfig
import io.legado.app.help.config.ThemeConfig
import io.legado.app.model.BookCover
import io.legado.app.ui.book.read.config.HighlightRuleStore
import io.legado.app.utils.GSON
import io.legado.app.utils.fromJsonObject
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import splitties.init.injectAsAppCtx

/**
 * B3 · R17「备份按内容分选」的**行为级**验证（2026-09-24 补齐，原为登记待补的 L3 项）。
 *
 * 为什么需要它：原 `BackupContentSelectTest` 只能做**源码不变量**断言（当时无 Robolectric，
 * `BackupSelectorConfig` 是触碰 `appCtx` 的 `object`，JVM 里不可实例化）⇒
 * 「只勾选部分类别 ⇒ 备份产物只含所选」这条**核心语义**始终停在人工待补。
 * 本测试用 B5 引入的 Robolectric 底座把该语义**真正跑起来**：
 *  ① 选择 → `getSelectedFileNames()` 精确集合（不多不少）
 *  ② 全不勾选 → 空清单（配合 `BackupConfigFragment` 的阻止提交即「不产出空包」）
 *  ③ `save()` 落盘 JSON 往返一致（防「选了没存」静默失效）
 *  ④ **类别模型 ↔ 备份实现「同名同文件」一致性**（AD-08 明确担忧的「孤儿条目 / 读到不存在文件」）：
 *     类别项若与真实产出的文件名不一致，用户勾选它**不会产生任何效果**（静默误导）。
 *     本用例正是靠它查出并修掉了两处真实缺陷：`bookChapter.json`（死条目，已删）与
 *     `readShareConfig.json`（与实际 `shareReadConfig.json` 写反，已改常量引用）。
 */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class)
class BackupSelectorBehaviorTest {

    private lateinit var context: Context

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        // BackupSelectorConfig 在类初始化即读 appCtx.filesDir；本测试刻意不加载 io.legado.app.App
        context.injectAsAppCtx()
        // 静态 object 跨用例存活（Robolectric 同一沙箱）：这里先强制初始化，
        // 并把「初始化时生效的 filesDir」记下来 —— `configPath` 绑定的是那一刻的 Context。
        if (boundFilesDir == null) {
            boundFilesDir = context.filesDir
            BackupSelectorConfig.isSelected("__init_probe__")
        }
        // 每个用例复位为「全选」，保证用例独立
        BackupSelectorConfig.selectAll()
    }

    private fun mainJava(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }

    /** ① 只勾选两项 ⇒ 备份清单**精确等于**这两项（不多不少）。 */
    @Test
    fun partialSelection_yieldsExactlySelectedFileNames() {
        BackupSelectorConfig.deselectAll()
        BackupSelectorConfig.setSelected("bookSource", true)
        BackupSelectorConfig.setSelected("autoTask", true)

        assertEquals(
            "只勾选 书源 + 自动任务 ⇒ 清单必须精确为这两项",
            listOf("bookSource.json", "autoTask.json"),
            BackupSelectorConfig.getSelectedFileNames()
        )
        assertFalse("部分勾选不得被判为「全选」", BackupSelectorConfig.isAllSelected())
        assertFalse("部分勾选不得被判为「全不选」", BackupSelectorConfig.isNoneSelected())
    }

    /** ② 全不勾选 ⇒ 空清单（宿主据此阻止提交，故不会产出空包）。 */
    @Test
    fun noneSelected_yieldsEmptyList() {
        BackupSelectorConfig.deselectAll()
        assertTrue("全不勾选必须被识别", BackupSelectorConfig.isNoneSelected())
        assertTrue("全不勾选清单必须为空", BackupSelectorConfig.getSelectedFileNames().isEmpty())
    }

    /** ③ `save()` 落盘后读回一致（防「选了没存」的静默失效）。 */
    @Test
    fun save_roundTripsThroughDisk() {
        BackupSelectorConfig.deselectAll()
        BackupSelectorConfig.setSelected("bookSource", true)
        BackupSelectorConfig.save()

        val dir = boundFilesDir ?: throw AssertionError("未捕获 filesDir")
        val configFile = File(dir, "backupSelector.json")
        assertTrue("分选配置必须落盘（路径=${configFile.absolutePath}）", configFile.isFile)
        val parsed = GSON.fromJsonObject<Map<String, Boolean>>(configFile.readText()).getOrNull()
        assertNotNull("分选配置必须可解析", parsed)
        assertEquals("bookSource 必须为 true", true, parsed!!["bookSource"])
        assertEquals("未勾选项必须为 false", false, parsed["autoTask"])
        // 全表都要被持久化（缺键会回落默认 true ⇒ 静默全选，等于用户的选择被吞）
        assertEquals(
            "所有类别键都必须被写入配置（缺键会回落默认 true）",
            BackupSelectorConfig.allItems.size,
            parsed.size
        )
    }

    /** 默认口径：未出现的键回落选中（升级用户不被静默裁剪）。 */
    @Test
    fun unknownKey_defaultsToSelected() {
        assertTrue(
            "未配置的键必须默认选中（否则升级用户备份被静默裁剪）",
            BackupSelectorConfig.isSelected("__not_configured__")
        )
    }

    /**
     * ④ 类别模型 ↔ `Backup.kt` 的「同名同文件」一致性（AD-08 的孤儿条目风险）。
     *
     * 判定：每个 `BackupItem.fileName` 必须能在 `Backup.kt` 源码里找到对它的引用 ——
     * 要么是**字符串字面量**，要么是**被引用的常量表达式**（常量值由本测试在 Kotlin 侧解析，
     * 避免"用常量就查不到"的假阴性）。
     */
    @Test
    fun everyCategoryNameExistsInBackupImplementation() {
        val backup = mainJava("help/storage/Backup.kt")
        assertTrue(
            "Backup.kt 必须按分选清单裁剪（否则分选形同虚设）",
            backup.contains("BackupSelectorConfig.getSelectedFileNames()")
        )

        // 常量名（Backup.kt 里出现的引用表达式）→ 实际值（Kotlin 侧求值，防常量改写后测试失真）
        val constants = mapOf(
            "CoverGalleryRepository.backupDirName" to CoverGalleryRepository.backupDirName,
            "HighlightRuleStore.backupFileName" to HighlightRuleStore.backupFileName,
            "DirectLinkUpload.ruleFileName" to DirectLinkUpload.ruleFileName,
            "ReadBookConfig.configFileName" to ReadBookConfig.configFileName,
            "ReadBookConfig.shareConfigFileName" to ReadBookConfig.shareConfigFileName,
            "ThemeConfig.configFileName" to ThemeConfig.configFileName,
            "BookCover.configFileName" to BookCover.configFileName,
        ).filterValues { it.isNotBlank() }

        val items = BackupSelectorConfig.allItems
        assertTrue("类别模型条目数异常（应 ≥30）", items.size >= 30)

        val unresolved = items.filter { item ->
            val byLiteral = backup.contains("\"${item.fileName}\"")
            // 常量引用命中：Backup.kt 出现了该常量表达式，且其值与条目名一致
            val byConstant = constants.any { (expr, value) ->
                value == item.fileName && backup.contains(expr)
            }
            // 条目自身就用常量引用（如 coverGallery / readShareConfig）时，按值比对即可
            val selfByConstant = constants.any { (_, value) -> value == item.fileName } &&
                backup.contains(constants.entries.first { it.value == item.fileName }.key)
            !byLiteral && !byConstant && !selfByConstant
        }

        assertTrue(
            "以下类别在备份实现里找不到同名文件引用 ⇒ 勾选后无任何效果（孤儿条目）：" +
                unresolved.joinToString { "${it.key}->${it.fileName}" },
            unresolved.isEmpty()
        )
    }

    companion object {
        /** 录制 `BackupSelectorConfig` 初始化时生效的 filesDir（`configPath` 绑定它）。 */
        private var boundFilesDir: File? = null
    }
}