package io.legado.app.help.image

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.4 / REQ-23：图片**真分享**接线不变量。
 *
 * 为什么值得测（实证根因）：原实现是 `sendToClip(imageUrl)`（复制链接），
 * 名为分享实为复制 ⇒ 必须锁定「FileProvider 授权 + ACTION_SEND + 读权限 + 图片 MIME」四要素，
 * 且分享文件必须落在 `file_paths.xml` 已声明的目录内（否则 `getUriForFile` 直接抛
 * `IllegalArgumentException`）。
 */
class ImageShareHelperTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val helper by lazy {
        read("src/main/java/io/legado/app/help/image/ImageShareHelper.kt")
    }
    private val filePaths by lazy { read("src/main/res/xml/file_paths.xml") }

    @Test
    fun usesFileProviderWithSingleSourceAuthority() {
        assertTrue("须经 FileProvider 授权", helper.contains("FileProvider.getUriForFile("))
        assertTrue("授权串须走 AppConst.authority 单源", helper.contains("AppConst.authority"))
    }

    @Test
    fun sendsImageFileWithReadPermission() {
        assertTrue("须用 ACTION_SEND", helper.contains("Intent.ACTION_SEND"))
        assertTrue("须携带 EXTRA_STREAM", helper.contains("Intent.EXTRA_STREAM"))
        assertTrue(
            "须授读权限（否则接收方打不开）",
            helper.contains("Intent.FLAG_GRANT_READ_URI_PERMISSION")
        )
        assertTrue("MIME 须为图片", helper.contains("\"image/*\""))
    }

    @Test
    fun shareFileKeepsExtensionUnderCacheDir() {
        assertTrue("须落 cacheDir（file_paths 的 cache-path 覆盖）", helper.contains("activity.cacheDir"))
        assertTrue("须保留扩展名（Glide 缓存文件名无扩展名 ⇒ MIME 推断会失败）", helper.contains("File(dir, displayName)"))
        assertTrue("须声明分享目录常量", helper.contains("share_image"))
    }

    @Test
    fun reusesExistingImageLoaderAndReportsFailure() {
        assertTrue("取图须复用 ImageLoader（不新增下载通道）", helper.contains("ImageLoader.loadFile("))
        assertTrue(
            "须注入 sourceOrigin（CDN 防盗链）",
            helper.contains("OkHttpModelLoader.sourceOriginOption")
        )
        assertTrue("失败须可定位（日志 + 非静默提示）", helper.contains("AppLog.put("))
        assertTrue("失败须有文案", helper.contains("R.string.image_share_failed"))
    }

    @Test
    fun shareDirectoryIsCoveredByFilePathsXml() {
        assertTrue(
            "cacheDir 根须已在 file_paths.xml 声明（cache-path path=\".\"）",
            filePaths.contains("<cache-path") && filePaths.contains("path=\".\"")
        )
    }
}