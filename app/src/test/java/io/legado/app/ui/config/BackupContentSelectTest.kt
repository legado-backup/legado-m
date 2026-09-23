package io.legado.app.ui.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R17「备份选择器按内容分选」不变量。
 *
 * 说明：`BackupSelectorConfig` / `BackupConfig` 均为 `object` 且初始化时触碰 `appCtx`，
 * 在无 Robolectric 的 JVM 单测里**不可实例化**（会崩）⇒ 本测试按**源码结构不变量**固化，
 * 覆盖 spec R17 的四条场景中的可静态判定部分（R17-2 阻止提交 / R17-3 与恢复忽略解耦 /
 * R17-4 回退分支不破坏 / 类别模型含 R8 条目）。
 */
class BackupContentSelectTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** R17-1/2：设置页有分选入口，且 `backup()` 前置「全不勾选阻止提交」。 */
    @Test
    fun fragment_exposesSelectorAndBlocksEmptySelection() {
        val fragment = code("ui/config/BackupConfigFragment.kt")
        assertTrue("必须有分选入口键", fragment.contains("KEY_BACKUP_CONTENT_SELECT"))
        assertTrue("必须渲染分选入口文案", fragment.contains("R.string.backup_content_select"))
        assertTrue("必须有分选弹窗方法", fragment.contains("private fun backupContentSelect("))
        assertTrue(
            "backup() 必须前置「全不勾选阻止提交」",
            fragment.contains("BackupSelectorConfig.isNoneSelected()")
        )
    }

    /**
     * R17-4：阻断判定必须**先于**云存储容量回退分支，否则会出现
     * 「S3 满 → 回退 WebDAV 弹窗」先弹、再发现无可备份内容的错序交互。
     */
    @Test
    fun emptySelectionGuard_runsBeforeS3FallbackBranch() {
        val fragment = code("ui/config/BackupConfigFragment.kt")
        val start = fragment.indexOf("fun backup(ignoreS3FullPrompt: Boolean = false)")
        assertTrue("未定位到 public backup()", start >= 0)
        val body = fragment.substring(start, start + 600)
        val guardAt = body.indexOf("isNoneSelected()")
        val fallbackAt = body.indexOf("shouldShowS3FullWebDavFallback()")
        assertTrue("未在 backup() 内定位到阻断判定", guardAt >= 0)
        assertTrue(
            "阻断判定必须先于 S3 满回退分支（实测顺序 guard=$guardAt fallback=$fallbackAt）",
            fallbackAt < 0 || guardAt < fallbackAt
        )
    }

    /** R17-3：分选与「恢复忽略」是两套独立机制（不得互相顶替）。 */
    @Test
    fun contentSelectAndRestoreIgnore_areIndependent() {
        val fragment = code("ui/config/BackupConfigFragment.kt")
        val ignoreFn = fragment.indexOf("private fun backupIgnore(")
        assertTrue("未定位到恢复忽略方法", ignoreFn >= 0)
        val ignoreBody = fragment.substring(ignoreFn, ignoreFn + 700)
        assertTrue(
            "恢复忽略必须仍走 BackupConfig.ignoreConfig（与分选解耦）",
            ignoreBody.contains("BackupConfig.ignoreConfig") &&
                !ignoreBody.contains("BackupSelectorConfig.setSelected")
        )
    }

    /** 类别模型：分选清单被 `Backup.backup()` 消费（本地/云端共用），且含 R8 的 autoTask 条目。 */
    @Test
    fun categoryModel_isConsumedByBackup_andContainsAutoTaskEntry() {
        val backup = code("help/storage/Backup.kt")
        assertTrue(
            "备份实现必须按分选清单裁剪内容",
            backup.contains("BackupSelectorConfig.getSelectedFileNames()")
        )
        val selector = code("help/storage/BackupSelectorConfig.kt")
        assertTrue(
            "R8 的 autoTask.json 必须在类别模型中有归属（防孤儿条目）",
            selector.contains("\"autoTask\"") && selector.contains("\"autoTask.json\"")
        )
        assertTrue("类别模型必须有非空判定（供阻断提交使用）", selector.contains("fun isNoneSelected()"))
    }
}