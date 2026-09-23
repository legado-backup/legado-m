package io.legado.app.ui.book.read.config

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B3 · R13「版面设置弹窗合并」不变量。
 *
 * 需求（spec R13-1/R13-2）：从阅读样式弹窗点「版面设置」后，**单个弹窗内**即可改边距与页眉页脚
 * （无需二次进入）；且**配置项键完全不变**（结果与原两条独立路径等价、旧配置零迁移）。
 *
 * 实现要点（固化以防回退）：
 * - 合并落在 `PaddingConfigDialog`（现即「版面设置」）：顶部分段 + 两段分别复用既有实现；
 * - 页眉页脚段复用 `TipConfigContent`（**不允许复制一份渲染**）；
 * - 原 `TipConfigDialog` 独立弹窗已无调用方 ⇒ 类删除，仅保留内容体与宿主回传 id。
 */
class LayoutConfigMergeTest {

    private fun code(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readLines()
            .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
            .joinToString("\n")
    }

    /** R13-1：阅读样式弹窗只留一个「版面设置」入口，不再分头打开两个弹窗。 */
    @Test
    fun readStyleDialog_hasSingleLayoutEntry() {
        val dialog = code("ui/book/read/config/ReadStyleDialog.kt")
        assertTrue("必须有「版面设置」入口", dialog.contains("R.string.layout_config"))
        assertTrue("必须走版面设置打开路径", dialog.contains("showPaddingConfig()"))
        assertFalse("不得再单独打开页眉页脚弹窗", dialog.contains("TipConfigDialog("))
    }

    /** R13-1/2：单弹窗内两段切换，且两段都复用既有实现（零复制）。 */
    @Test
    fun layoutDialog_hostsBothSectionsByReuse() {
        val dialog = code("ui/book/read/config/PaddingConfigDialog.kt")
        assertTrue("必须有分段切换", dialog.contains("LayoutSectionSwitch("))
        assertTrue("页眉页脚段必须复用 TipConfigContent", dialog.contains("TipConfigContent("))
        assertTrue(
            "边距段必须仍是原有三段实现",
            dialog.contains("HeaderSection(") &&
                dialog.contains("BodySection(") &&
                dialog.contains("FooterSection(")
        )
    }

    /** R13-2：配置项键不变（边距与标题/页脚仍写 `ReadBookConfig` 的同名字段）。 */
    @Test
    fun configKeysUnchanged() {
        val dialog = code("ui/book/read/config/PaddingConfigDialog.kt")
        listOf(
            "ReadBookConfig.headerPaddingTop",
            "ReadBookConfig.paddingTop",
            "ReadBookConfig.footerPaddingTop",
            "ReadBookConfig.showHeaderLine",
            "ReadBookConfig.showFooterLine"
        ).forEach { key ->
            assertTrue("配置字段 $key 不得改名（旧配置零迁移）", dialog.contains(key))
        }
        // 页眉页脚段仍经 TipConfigContent → ReadTipConfig（→ ReadBookConfig.config 同名字段）
        assertFalse(
            "不得在版面设置里另起一套页眉页脚字段",
            dialog.contains("ReadTipConfig.tipHeaderLeft =")
        )
    }

    /** 死代码清理：合并后 `TipConfigDialog` 类已无调用方 ⇒ 类删除，仅保留内容体与回传 id。 */
    @Test
    fun tipConfigDialogClassRemovedButIdsKept() {
        val tip = code("ui/book/read/config/TipConfigDialog.kt")
        assertFalse("独立的页眉页脚弹窗类必须已删除", tip.contains("class TipConfigDialog"))
        assertTrue("内容体必须保留（供版面设置复用）", tip.contains("internal fun TipConfigContent("))
        assertTrue("配色回传 id 必须保留为文件级常量", tip.contains("internal const val TIP_COLOR"))
        assertTrue(tip.contains("internal const val TIP_DIVIDER_COLOR"))
    }
}