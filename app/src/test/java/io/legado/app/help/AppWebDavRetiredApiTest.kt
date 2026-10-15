package io.legado.app.help

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B17：`AppWebDav.backUpWebDav` 零调用 API 退役守护。
 *
 * 缺陷背景：该函数为 `public suspend fun`，却在全主源码内**零调用**——
 * 活路径是 `AppCloudStorage.backupToWebDav`（带 `ensureNetwork()`/`webDavBackend.upConfig()`），
 * 该函数为赶工期的重复实现残留；且它会「网络不可用/未配置时静默 return」，
 * 属典型的设计不合理死代码。本类固化其退役，并守护活路径不被误删。
 */
class AppWebDavRetiredApiTest {

    private fun code(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText().replace("\r\n", "\n")

    @Test
    fun `零调用 webDav 备份 API 退役且活路径仍在`() {
        val webdav = code("src/main/java/io/legado/app/help/AppWebDav.kt")
        assertEquals("零调用 API backUpWebDav 应退役", false,
            webdav.contains("fun backUpWebDav("))
        val cloud = code("src/main/java/io/legado/app/help/AppCloudStorage.kt")
        assertEquals("活路径 backupToWebDav 必须保留", true,
            cloud.contains("fun backupToWebDav("))
    }
}
