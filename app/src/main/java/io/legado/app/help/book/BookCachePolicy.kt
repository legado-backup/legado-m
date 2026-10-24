package io.legado.app.help.book

import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.exoplayer.ExoPlayerHelper

/**
 * 详情页缓存卡的**内容类型分派口径**（book-info-unified-cache AD-02）。
 *
 * 纯函数：便于 JVM 单测锁定「哪些类型应显示缓存卡」，避免在 Composable 内散落 if-else。
 * `isVideo` 由调用方按**复合身份**（`book.isVideo` 位 或 书源 `isVideoSource`）算好后传入。
 */
enum class CacheBarKind {
    VIDEO,
    AUDIO,
    IMAGE,
    /** 文本 / 文件（`isWebFile`）—— 同走章节缓存底座 */
    TEXT,
    UNSUPPORTED;

    companion object {
        fun of(
            isVideo: Boolean,
            isAudio: Boolean,
            isImage: Boolean,
            isLocal: Boolean,
            hasToc: Boolean,
        ): CacheBarKind = when {
            // 本地书没有可缓存的远端内容；无目录则无从统计/缓存
            isLocal || !hasToc -> UNSUPPORTED
            isVideo -> VIDEO
            isAudio -> AUDIO
            isImage -> IMAGE
            else -> TEXT
        }
    }
}

/**
 * 「某章是否已缓存」的**单一判定入口**（book-info-unified-cache AD-04）。
 *
 * 收敛此前三套口径分歧：
 * - `TocComposeScreen.isChapterCached`：无视频分支，视频走 `BookHelp.hasContent`（`.nb` 口径）⇒ 恒 false
 * - `CacheManageActivityViewModel.isChapterCached`（private）：视频走 `BookVideoCache`、音频走 `isMediaCached`
 * - `LocalMediaResolver.hasLocal`：全部触盘（图片还解码）
 *
 * 本入口保留目录页既有语义（本地书 / 卷行 → 已缓存），并按类型分派：
 * 视频 → `.mp4` 双名比对（不触盘）；音频 → ExoPlayer 缓存查询；图片 → 默认文件名比对
 * （`validateImageContent=true` 时才校验图片内容）；文本/文件 → 章节缓存文件名比对。
 */
object CachedChapterResolver {

    fun isCached(
        book: Book?,
        chapter: BookChapter,
        cacheFileNames: Set<String>,
        sourceIsVideo: Boolean = false,
        validateImageContent: Boolean = false,
    ): Boolean {
        if (book == null) return false
        // 与目录页既有行为一致：本地书（内容在本地）与卷行（线路名不是一章）不参与统计
        if (book.isLocal || chapter.isVolume) return true
        return when {
            book.isVideo || sourceIsVideo -> BookVideoCache.isCachedIn(cacheFileNames, chapter)
            book.isAudio -> ExoPlayerHelper.isMediaCached(chapter.resourceUrl)
            book.isImage -> cacheFileNames.contains(chapter.getFileName()) ||
                (validateImageContent && BookHelp.hasImageContent(book, chapter))
            else -> BookHelp.getChapterCacheFileNames(book, chapter).any(cacheFileNames::contains)
        }
    }

    /**
     * 已缓存集的**全集下标**集合（选集勾选用）。
     *
     * 返回的是 `chapters` 列表下标（与 `VideoPlay.episodes` / `ChoiceEpisodeDialog` 回传的集号同语义），
     * 因此倒序展示时角标仍对应真实集号，而非格子位置。
     */
    fun cachedIndexes(
        book: Book?,
        chapters: List<BookChapter>,
        cacheFileNames: Set<String>,
        sourceIsVideo: Boolean = false,
    ): Set<Int> {
        if (book == null || chapters.isEmpty()) return emptySet()
        val result = LinkedHashSet<Int>()
        chapters.forEachIndexed { index, chapter ->
            if (isCached(book, chapter, cacheFileNames, sourceIsVideo)) result.add(index)
        }
        return result
    }
}
