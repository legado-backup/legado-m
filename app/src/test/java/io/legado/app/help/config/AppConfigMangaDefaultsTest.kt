package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.1 / 6.3（REQ-20 / REQ-22）：漫画相关**全局默认值**不变量。
 *
 * 为什么值得测（实证根因）：6.1 是把默认值由 `true` 翻成 `false` 的一行改动 —— 极易在后续
 * 重构中被改回；6.3 新增的开关必须默认「开」以保持既有行为（默认值写反 = 静默行为回归）。
 */
class AppConfigMangaDefaultsTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val appConfig by lazy {
        read("src/main/java/io/legado/app/help/config/AppConfig.kt")
    }

    @Test
    fun disableMangaScaleDefaultsToFalse() {
        assertTrue(
            "漫画缩放默认须为关（false ⇒ 缩放可用）",
            appConfig.contains("getPrefBoolean(PreferKey.disableMangaScale, false)")
        )
    }

    @Test
    fun volumeKeyPageDefaultsToTrue() {
        assertTrue(
            "音量键翻页默认须为开（保持既有行为）",
            appConfig.contains("getPrefBoolean(PreferKey.mangaVolumeKeyPage, true)")
        )
        assertTrue(
            "须有对应的写入器（否则设置页开关无法落盘）",
            appConfig.contains("putPrefBoolean(PreferKey.mangaVolumeKeyPage, value)")
        )
    }

    @Test
    fun bookLevelOverrideChainUntouched() {
        // 6.1 只允许改「全局默认值」：书籍级覆盖语义必须保持 `book?.config?.mangaDisableScale ?: 全局`
        val readManga by lazy { read("src/main/java/io/legado/app/ui/book/manga/ReadMangaActivity.kt") }
        assertTrue(
            "书籍级覆盖链不得改动",
            readManga.contains("ReadManga.book?.config?.mangaDisableScale ?: AppConfig.disableMangaScale")
        )
    }
}