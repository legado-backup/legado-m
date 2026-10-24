package io.legado.app.service

import android.content.Intent
import androidx.core.app.NotificationCompat
import io.legado.app.R
import io.legado.app.base.BaseService
import io.legado.app.constant.AppConst
import io.legado.app.constant.AppLog
import io.legado.app.constant.IntentAction
import io.legado.app.constant.NotificationId
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.data.entities.BookSource
import io.legado.app.help.book.BookVideoCache
import io.legado.app.help.book.getBookSource
import io.legado.app.help.coroutine.Coroutine
import io.legado.app.help.download.HlsDownloader
import io.legado.app.help.download.HlsResult
import io.legado.app.help.http.addHeaders
import io.legado.app.help.http.newCallResponse
import io.legado.app.help.http.okHttpClient
import io.legado.app.help.video.VideoUrlExtractor
import io.legado.app.model.analyzeRule.AnalyzeUrl
import io.legado.app.model.webBook.WebBook
import io.legado.app.service.kernel.VideoCacheKernel
import io.legado.app.ui.book.cache.CacheActivity
import io.legado.app.utils.activityPendingIntent
import io.legado.app.utils.servicePendingIntent
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import splitties.systemservices.notificationManager
import java.io.File
import java.io.IOException
import kotlin.math.min

/**
 * 书源视频缓存服务（video-cache-and-multiep V1）。
 *
 * 与 [CacheBookService]（文本/音频/漫画章节缓存）并列：本服务只处理 `bookSourceType=4`
 * 的视频书源，按集解析真实流地址并落盘为 `book_cache/{folder}/c-{md5}.mp4`。
 *
 * 关键约束（见 design AD-01/AD-13/AD-15）：
 * - 复用 `BookHelp` 缓存目录与 `.mp4` 后缀，不新增表/目录；
 * - 逐集串行（避免站点限流），单集失败不阻塞后续集；
 * - 已缓存集跳过，天然断点续传；
 * - 前台服务类型 dataSync，通知复用下载渠道。
 */
class VideoCacheService : BaseService() {

    companion object {
        private const val TAG_VIDEO_CACHE = "VideoCacheDiag"

        /** 目录未落库时的轮询次数与间隔（合计 20s，覆盖详情页入架→目录加载窗口） */
        internal const val EPISODE_WAIT_POLLS = 40
        internal const val EPISODE_WAIT_STEP_MS = 500L
    }

    private var cacheJob: Coroutine<*>? = null
    private var cacheRunning = false
    private var notificationContent = ""

    private val notificationBuilder by lazy {
        NotificationCompat.Builder(this, AppConst.channelIdDownload)
            .setSmallIcon(R.drawable.ic_download)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentTitle(getString(R.string.offline_cache))
            .setContentIntent(activityPendingIntent<CacheActivity>("cacheActivity"))
            .apply {
                addAction(
                    R.drawable.ic_stop_black_24dp,
                    getString(R.string.cancel),
                    servicePendingIntent<VideoCacheService>(IntentAction.stop)
                )
                setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            }
    }

    override fun startForegroundNotification() {
        notificationBuilder.setContentText(notificationContent)
        startForeground(NotificationId.VideoCacheService, notificationBuilder.build())
    }

    private fun upNotification() {
        notificationBuilder.setContentText(notificationContent)
        notificationManager.notify(NotificationId.VideoCacheService, notificationBuilder.build())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.action?.let { action ->
            when (action) {
                IntentAction.start -> startCache(
                    intent.getStringExtra("bookUrl"),
                    intent.getIntExtra("start", 0),
                    intent.getIntExtra("end", -1),
                )

                IntentAction.stop -> intent.getStringExtra("bookUrl")?.let(::stopCache)
            }
        }
        return super.onStartCommand(intent, flags, startId)
    }

    private fun startCache(bookUrl: String?, from: Int, to: Int) {
        if (bookUrl.isNullOrBlank()) return
        if (cacheRunning) return
        cacheRunning = true
        cacheJob = execute {
            try {
                val book = appDb.bookDao.getBook(bookUrl)
                val source = book?.getBookSource() as? BookSource
                if (book == null || source == null) {
                    AppLog.put("$TAG_VIDEO_CACHE 启动失败：书籍或书源不存在")
                    VideoCacheKernel.onStopped(bookUrl)
                    return@execute
                }
                val chapters = appDb.bookChapterDao.getChapterList(bookUrl)
                var episodes = VideoCacheKernel.episodesOf(chapters)
                if (episodes.isEmpty()) {
                    // 详情页「点击缓存自动入架」场景：书籍入库与目录落库有先后，
                    // 立刻起缓存会因「目录为空」fail-fast（用户感知＝缓存不了）。
                    // 轮询等待目录落库（上限 20s），拿到即继续。
                    AppLog.put("$TAG_VIDEO_CACHE 目录为空，等待目录落库（上限 20s）")
                    for (i in 1..EPISODE_WAIT_POLLS) {
                        if (!isActive) break
                        delay(EPISODE_WAIT_STEP_MS)
                        episodes = VideoCacheKernel.episodesOf(
                            appDb.bookChapterDao.getChapterList(bookUrl)
                        )
                        if (episodes.isNotEmpty()) break
                    }
                }
                if (episodes.isEmpty()) {
                    AppLog.put("$TAG_VIDEO_CACHE 启动失败：目录为空（已等待 ${EPISODE_WAIT_POLLS * EPISODE_WAIT_STEP_MS / 1000}s）")
                    VideoCacheKernel.onStopped(bookUrl)
                    return@execute
                }
                // 先按真实文件重建索引，避免把"外部已删除"的集当成已缓存
                VideoCacheKernel.refreshIndex(book)
                VideoCacheKernel.onStarted(bookUrl, episodes.size)
                val lastPosition = episodes.lastIndex
                val endPosition = if (to < 0) lastPosition else min(to, lastPosition)
                val startPosition = from.coerceIn(0, lastPosition)
                AppLog.put(
                    "$TAG_VIDEO_CACHE 开始缓存 total=${episodes.size} range=$startPosition..$endPosition"
                )
                for (position in startPosition..endPosition) {
                    if (!isActive) break
                    val chapter = episodes[position]
                    if (VideoCacheKernel.isCached(bookUrl, chapter.index)) continue
                    VideoCacheKernel.onEpisodeStart(bookUrl, chapter.index, chapter.title)
                    notificationContent = "缓存中 ${position + 1}/${episodes.size}"
                    upNotification()
                    kotlin.runCatching {
                        cacheEpisode(source, book, chapter)
                    }.onSuccess {
                        VideoCacheKernel.onEpisodeDone(bookUrl, chapter.index)
                        AppLog.putDebugWithTag(
                            TAG_VIDEO_CACHE,
                            "第 ${chapter.index} 集缓存完成",
                            level = AppLog.Level.INFO
                        )
                    }.onFailure {
                        VideoCacheKernel.onEpisodeFailed(bookUrl, chapter.index, it.localizedMessage)
                        AppLog.put("$TAG_VIDEO_CACHE 第 ${chapter.index} 集缓存失败", it)
                    }
                }
                notificationContent = "缓存完成"
                upNotification()
                VideoCacheKernel.onFinished(bookUrl)
            } finally {
                cacheRunning = false
                if (VideoCacheKernel.states.value.values.none { it.running }) {
                    stopSelf()
                }
            }
        }
    }

    private fun stopCache(bookUrl: String) {
        cacheJob?.cancel()
        cacheJob = null
        cacheRunning = false
        VideoCacheKernel.onStopped(bookUrl)
        stopSelf()
    }

    /**
     * 单集：正文/播放页 → 真实流地址 → 落盘 mp4。
     */
    private suspend fun cacheEpisode(source: BookSource, book: Book, chapter: BookChapter) {
        val content = WebBook.getContentAwait(source, book, chapter, needSave = false)
            .trim()
        AppLog.put("$TAG_VIDEO_CACHE index=${chapter.index} 正文长度=${content.length}")
        if (content.isEmpty()) {
            throw IOException("正文为空，未取到播放地址")
        }
        val firstLine = content.lines()
            .map { it.trim() }
            .firstOrNull { it.startsWith("http://") || it.startsWith("https://") }
            ?: content
        val isHls = VideoUrlExtractor.isDirectVideoStreamUrl(firstLine) &&
            firstLine.contains(".m3u8", ignoreCase = true)
        val streamUrl = if (VideoUrlExtractor.isDirectVideoStreamUrl(firstLine)) {
            firstLine
        } else {
            VideoUrlExtractor.extractVideoUrlForEpisode(firstLine, source, chapter)?.url
                ?: throw IOException("未能解析出视频流地址")
        }
        AppLog.put(
            "$TAG_VIDEO_CACHE index=${chapter.index} 流类型=${if (isHls) "HLS" else "直链"}, " +
                "urlLen=${streamUrl.length}"
        )
        val output = BookVideoCache.fileOf(book, chapter)
        output.parentFile?.mkdirs()
        if (output.exists() && output.length() > 0) return
        val headers = AnalyzeUrl(
            streamUrl,
            source = source,
            ruleData = book,
            chapter = chapter,
        ).headerMap
        if (streamUrl.contains("m3u8", ignoreCase = true)) {
            val tempDir = File(output.parentFile, "vcache_${chapter.index}")
            // 合并成功即取到完整 ts：即便 remux 失败也必须落盘（否则"下载成功但缓存被判失败"）
            var mergedTs: File? = null
            val result = HlsDownloader.download(
                m3u8Url = streamUrl,
                outputMp4 = output,
                tempDir = tempDir,
                headers = headers,
                onProgress = { _, _ -> },
                onMerged = { mergedTs = it },
            )
            AppLog.put(
                "$TAG_VIDEO_CACHE index=${chapter.index} HLS 结果=" +
                    "${result::class.simpleName}, ts=${mergedTs?.length() ?: 0}B"
            )
            if (result is HlsResult.TsFallback) {
                // ts 兜底：MPEG-TS 单文件可直接被 ExoPlayer 渐进式播放（按内容嗅探，不看后缀），
                // 故沿用主名 .mp4 落盘，避免缓存管理/本地优先的命名契约分叉。
                val ts = mergedTs?.takeIf { it.exists() && it.length() > 0 }
                    ?: throw IOException("HLS 合并产物缺失")
                output.outputStream().use { out -> ts.inputStream().use { it.copyTo(out) } }
                ts.delete()
            } else if (result !is HlsResult.Mp4) {
                throw IOException("HLS 下载未产出可用文件：$result")
            }
            tempDir.deleteRecursively()
        } else {
            downloadDirect(streamUrl, output, headers)
        }
        if (!output.exists() || output.length() <= 0) {
            throw IOException("落盘文件为空")
        }
        AppLog.put("$TAG_VIDEO_CACHE index=${chapter.index} 落盘完成 size=${output.length()}B")
    }

    private suspend fun downloadDirect(
        streamUrl: String,
        output: File,
        headers: Map<String, String>,
    ) {
        val temp = File(output.parentFile, output.name + ".part")
        okHttpClient.newCallResponse {
            url(streamUrl)
            addHeaders(headers)
        }.use { response ->
            if (!response.isSuccessful) {
                throw IOException("HTTP ${response.code}")
            }
            val body = response.body
            body.byteStream().use { input ->
                temp.outputStream().use { out ->
                    input.copyTo(out, DEFAULT_BUFFER_SIZE)
                }
            }
        }
        if (temp.exists()) {
            temp.renameTo(output)
        }
        if (!temp.exists() && !output.exists()) {
            throw IOException("下载未产生文件")
        }
    }
}
