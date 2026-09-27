package io.legado.app.constant

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.3 / REQ-22：新增偏好键的**四处同名**一致性（键名、AppConfig 读写、设置页两栈）。
 *
 * 为什么值得测（实证根因）：设置项是「XML（供设置搜索收录）+ Compose spec 列表（实际渲染）」
 * 双栈 —— 只改一处会出现「搜索得到但页面没有」或「页面有但开关不落盘」的静默缺陷。
 */
class PreferKeyMangaKeysTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val preferKey by lazy { read("src/main/java/io/legado/app/constant/PreferKey.kt") }
    private val appConfig by lazy {
        read("src/main/java/io/legado/app/help/config/AppConfig.kt")
    }
    private val prefXml by lazy { read("src/main/res/xml/pref_config_other.xml") }
    private val otherSpec by lazy {
        read("src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt")
    }

    @Test
    fun volumeKeyConstantDeclaredWithSameLiteral() {
        assertTrue(
            "常量须声明",
            preferKey.contains("const val mangaVolumeKeyPage = \"mangaVolumeKeyPage\"")
        )
        assertTrue(
            "键面值须在 AppConfig 一致使用",
            appConfig.contains("PreferKey.mangaVolumeKeyPage")
        )
    }

    @Test
    fun bothSettingStacksRegisterTheKey() {
        assertTrue("XML 栈须有条目（设置搜索收录）", prefXml.contains("android:key=\"mangaVolumeKeyPage\""))
        assertTrue("Compose spec 栈须有条目（实际渲染）", otherSpec.contains("PreferKey.mangaVolumeKeyPage"))
    }

    @Test
    fun defaultValueIsConsistentAcrossStacks() {
        // XML 条目里 `android:defaultValue` 写在 `android:key` 之前 ⇒ 取包含该 key 的整个 <SwitchPreference .../> 块
        val xmlBlock = Regex(
            "<io\\.legado\\.app\\.lib\\.prefs\\.SwitchPreference[\\s\\S]{0,240}?android:key=\"mangaVolumeKeyPage\"[\\s\\S]{0,240}?/>"
        ).find(prefXml)?.value.orEmpty()
        assertTrue("XML 条目须声明默认值 true", xmlBlock.contains("android:defaultValue=\"true\""))
        val specHasTrue = Regex("PreferKey\\.mangaVolumeKeyPage[\\s\\S]{0,200}?defaultValue = true")
            .containsMatchIn(otherSpec)
        assertTrue("Compose spec 默认值须为 true（两栈一致）", specHasTrue)
    }
}