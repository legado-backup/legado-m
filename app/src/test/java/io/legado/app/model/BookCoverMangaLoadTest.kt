package io.legado.app.model

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W5 6.2 / REQ-21：漫画图片加载的**内存缓存 + 解码高收敛**接线不变量。
 *
 * 为什么值得测（实证根因）：
 * - 原 `loadManga()` 带 `.skipMemoryCache(true)` ⇒ 每次翻回都重新解码/重下（流量与白屏）；
 * - 且 `.override(widthPixels, SIZE_ORIGINAL)` ⇒ 条漫（数万像素高）**按原图全量解码**（OOM 风险）。
 * 两个改动都不会让编译失败，只能靠断言锁定，否则极易被「顺手改回」。
 */
class BookCoverMangaLoadTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            .replace("\r\n", "\n")

    private val bookCover by lazy { read("src/main/java/io/legado/app/model/BookCover.kt") }

    /** 只截取 `loadManga` 函数体，避免同文件其它 `load*` 函数造成误判。 */
    private val loadMangaRaw by lazy {
        val start = bookCover.indexOf("fun loadManga(")
        val end = bookCover.indexOf("fun preloadManga(", start)
        if (start > 0 && end > start) bookCover.substring(start, end) else bookCover
    }

    /** 去掉注释行后再断言：说明文字里会引用被移除的旧写法（如 `skipMemoryCache(true)`）。 */
    private val loadManga by lazy {
        loadMangaRaw.lines().filterNot { it.trimStart().startsWith("//") }.joinToString("\n")
    }

    @Test
    fun memoryCacheIsEnabledForManga() {
        assertFalse(
            "不得再跳过内存缓存（否则翻回必重新解码）",
            loadManga.contains("skipMemoryCache(true)")
        )
    }

    @Test
    fun decodeHeightIsCappedBySharedSingleSource() {
        assertTrue(
            "解码高上限须取自 ImagePyramidLoader 的同口径常量",
            loadManga.contains("ImagePyramidLoader.NORMAL_MAX_HEIGHT_SCREEN_MULTIPLIER")
        )
        assertTrue(
            "须按屏宽 × 上限高做 override（不再用 SIZE_ORIGINAL）",
            loadManga.contains(".override(metrics.widthPixels, maxDecodeHeight)")
        )
        assertFalse("不得再按原图高全量解码", loadManga.contains("SIZE_ORIGINAL"))
    }

    @Test
    fun fitCenterDownsampleBoundsDecodeByTheBox() {
        assertTrue(
            "须显式 FIT_CENTER：默认 CENTER_OUTSIDE 只保证「覆盖」目标盒，" +
                "长图解码高仍会超出上限（实测口径）",
            loadManga.contains(".downsample(DownsampleStrategy.FIT_CENTER)")
        )
    }

    @Test
    fun diskCacheStrategyAndTransformBranchPreserved() {
        assertTrue("磁盘缓存策略须保持 ALL", loadManga.contains("DiskCacheStrategy.ALL"))
        assertTrue("transformation 分支须保持", loadManga.contains(".transform(transformation)"))
    }
}