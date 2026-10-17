package io.legado.app.constant

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 首屏加载模板 **prefs 键**契约单测（reader-theme-family 3.12 配对 · `constant` 目录）。
 *
 * 为什么值得一个测试：prefs 键是"定义↔消费"链最脆的一环 —— 键名写错或**同名重复**都会让功能
 * 静默失效（存了却读不到 / 两处各存一份）。这里把三件事钉住：
 * ①两个新键的**字面值**（改值必须同时改测试，防"改键名不迁移数据"）；
 * ②两键在 `PreferKey.kt` 内**各只出现一次**（防重复声明造成同名冲突）；
 * ③键确实被门面 `AppConfig` 读写、且 Manager 只经门面访问（防"绕过门面直读 prefs"回潮）。
 *
 * 注：本测试读源码文本（`:test` 目录无法构造 appCtx ⇒ `AppConfig` 取值不可 JVM 行为化），
 * 但每条都带**期望值断言**（不是"只断言存在"的弱形态）。
 */
class LoadingTemplatePreferKeysTest {

    private fun source(path: String) = File("src/main/java/$path").readText()

    @Test
    fun `两个新键的字面值与唯一性`() {
        val preferKey = source("io/legado/app/constant/PreferKey.kt")
        assertEquals("epubLoadingTemplate", PreferKey.epubLoadingTemplate)
        assertEquals("epubLoadingTemplates", PreferKey.epubLoadingTemplates)
        listOf(PreferKey.epubLoadingTemplate, PreferKey.epubLoadingTemplates).forEach { key ->
            val occurrences = Regex("""const val \w+ = "$key"""").findAll(preferKey).count()
            assertEquals("键 $key 在 PreferKey.kt 内必须只声明一次（重复会造成同名冲突）", 1, occurrences)
        }
    }

    @Test
    fun `键经 AppConfig 门面读写且 Manager 不绕过门面`() {
        val appConfig = source("io/legado/app/help/config/AppConfig.kt")
        assertTrue("AppConfig 必须读选择键", appConfig.contains("PreferKey.epubLoadingTemplate,"))
        assertTrue("AppConfig 必须写选择键", appConfig.contains("putPrefString(PreferKey.epubLoadingTemplate"))
        assertTrue("AppConfig 必须读库键", appConfig.contains("PreferKey.epubLoadingTemplates"))
        assertTrue("AppConfig 必须写库键", appConfig.contains("putPrefString(PreferKey.epubLoadingTemplates"))

        val manager = source("io/legado/app/help/config/EpubLoadingTemplateManager.kt")
        assertTrue("Manager 必须经 AppConfig 读选择键", manager.contains("AppConfig.epubLoadingTemplate"))
        assertTrue("Manager 必须经 AppConfig 写选择键", manager.contains("AppConfig.epubLoadingTemplate ="))
        assertTrue("Manager 必须经 AppConfig 读库键", manager.contains("AppConfig.epubLoadingTemplates)"))
        assertTrue("Manager 必须经 AppConfig 写库键", manager.contains("AppConfig.epubLoadingTemplates ="))
        assertTrue(
            "Manager 不得绕过门面直读 defaultSharedPreferences",
            !manager.contains("getDefaultSharedPreferences")
        )
    }

    @Test
    fun `默认值哨兵单源在 ReaderFeatureDefaults`() {
        val defaults = source("io/legado/app/help/config/ReaderFeatureDefaults.kt")
        assertTrue("默认值常量必须存在于 ReaderFeatureDefaults", defaults.contains("const val LOADING_TEMPLATE_ID"))
        // 哨兵语义：空串 ⇒ 走 EpubLoadingTemplate.DEFAULT（默认是哪一套由模型单源决定）
        assertTrue("哨兵须为空串（模型侧 BUILT_IN.first 决定默认款）", defaults.contains("LOADING_TEMPLATE_ID = \"\""))
    }
}
