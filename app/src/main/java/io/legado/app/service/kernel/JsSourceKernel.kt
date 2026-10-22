package io.legado.app.service.kernel

import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.data.entities.BookSource
import io.legado.app.model.jsSource.JsSourceConfig
import io.legado.app.model.jsSource.JsSourceEngine
import io.legado.app.model.jsSource.JsSourceUpsert
import io.legado.app.model.webBook.WebBook
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout

/**
 * 单文件 JS 书源内核（Web / MCP 共用）。
 *
 * 只做三件事：脚本校验、落库（串行 + 体积门禁）、链路调试；
 * **不内含业务规则**，与 App 内编辑/导入走同一份 [JsSourceConfig] / [JsSourceUpsert]。
 */
object JsSourceKernel {

    private const val SCRIPT_TIMEOUT = 30_000L
    private const val MAX_RETURN_CHARS = 20_000

    /** 脚本 → 书源摘要（不落库）。 */
    suspend fun validate(script: String, externalJsLib: String? = null): Map<String, Any?> {
        JsSourceUpsert.validatePayload(script)?.let { issue ->
            throw IllegalArgumentException(
                if (issue == JsSourceUpsert.PayloadIssue.EMPTY) "JS 书源内容为空" else "JS 书源不能超过 1 MiB"
            )
        }
        return withContext(IO) {
            val source = withTimeout(SCRIPT_TIMEOUT) {
                JsSourceConfig.extract(script, currentCoroutineContext(), externalJsLib)
            }
            summary(source)
        }
    }

    /** 校验并落库（同 URL 覆盖；串行锁防并发覆盖）。 */
    suspend fun save(script: String, openedSourceUrl: String? = null): Map<String, Any?> {
        val source = JsSourceUpsert.save(script, openedSourceUrl)
        return summary(source) + ("saved" to true)
    }

    /**
     * 导出脚本正文。
     *
     * - MCP 工具用默认 [MAX_RETURN_CHARS] 做「预览」（大脚本如 800KB+ 不适合塞进 AI 上下文）
     * - Web 编辑器必须传 `limit = Int.MAX_VALUE` 拿全文：否则前端拿到截断文本再保存
     *   会**覆盖真实脚本造成数据丢失**（2026-10-22 真机源 889KB 实测暴露）
     */
    suspend fun export(sourceUrl: String, limit: Int = MAX_RETURN_CHARS): Map<String, Any?> = withContext(IO) {
        val script = appDb.bookSourceDao.getMainJs(sourceUrl)
            ?: throw IllegalArgumentException("该书源没有脚本内容")
        exportPayload(sourceUrl, script, limit)
    }

    /** 导出载荷构造（纯函数，供单测覆盖截断边界；不触库）。 */
    internal fun exportPayload(sourceUrl: String, script: String, limit: Int): Map<String, Any?> {
        val truncated = limit in 0 until script.length
        return mapOf(
            "url" to sourceUrl,
            "length" to script.length,
            "truncated" to truncated,
            "script" to if (truncated) script.take(limit) else script,
        )
    }

    /**
     * 链路调试：search / explore / info / toc / content。
     * `scriptOverride` 仅本次生效，不落库（与 App 内「调试不保存」同口径）。
     */
    suspend fun debug(
        sourceUrl: String,
        chain: String,
        params: Map<String, String>,
        scriptOverride: String? = null,
    ): Map<String, Any?> = withContext(IO) {
        val stored = appDb.bookSourceDao.getBookSource(sourceUrl)
            ?: throw IllegalArgumentException("书源不存在")
        val source = if (scriptOverride.isNullOrBlank()) {
            stored
        } else {
            // 覆盖脚本仅限本次调用：复用导入校验拿到最新 config，再替换脚本本体
            val parsed = withTimeout(SCRIPT_TIMEOUT) {
                JsSourceConfig.extract(scriptOverride, currentCoroutineContext(), stored.jsLib)
            }
            parsed
        }
        if (source.mainJs.isNullOrBlank()) throw IllegalArgumentException("该书源没有脚本内容")
        val result: Any? = withTimeout(SCRIPT_TIMEOUT + 15_000L) {
            when (chain) {
                "search" -> {
                    val key = params["key"].orEmpty()
                    require(key.isNotEmpty()) { "search 需要 key 参数" }
                    val page = params["page"]?.toIntOrNull() ?: 1
                    WebBook.searchBookAwait(source, key, page).map { it.toBook() }
                }

                "explore" -> {
                    val url = params["url"].orEmpty()
                    require(url.isNotEmpty()) { "explore 需要 url 参数" }
                    val page = params["page"]?.toIntOrNull() ?: 1
                    WebBook.exploreBookAwait(source, url, page).map { it.toBook() }
                }

                "info" -> {
                    val bookUrl = params["bookUrl"].orEmpty()
                    require(bookUrl.isNotEmpty()) { "info 需要 bookUrl 参数" }
                    WebBook.getBookInfoAwait(source, buildBook(source, bookUrl), true)
                }

                "toc" -> {
                    val bookUrl = params["bookUrl"].orEmpty()
                    require(bookUrl.isNotEmpty()) { "toc 需要 bookUrl 参数" }
                    val book = buildBook(source, bookUrl).also {
                        it.tocUrl = params["tocUrl"]?.takeIf(String::isNotBlank) ?: bookUrl
                    }
                    WebBook.getChapterListAwait(source, book).getOrThrow()
                }

                "content" -> {
                    val bookUrl = params["bookUrl"].orEmpty()
                    val chapterUrl = params["chapterUrl"].orEmpty()
                    require(bookUrl.isNotEmpty() && chapterUrl.isNotEmpty()) {
                        "content 需要 bookUrl 与 chapterUrl 参数"
                    }
                    val book = buildBook(source, bookUrl).also {
                        it.tocUrl = params["tocUrl"]?.takeIf(String::isNotBlank) ?: bookUrl
                    }
                    val chapter = BookChapter(
                        bookUrl = bookUrl,
                        title = params["chapterTitle"].orEmpty(),
                        url = chapterUrl,
                        index = 0,
                        baseUrl = book.tocUrl,
                    )
                    mapOf(
                        "content" to WebBook.getContentAwait(
                            bookSource = source,
                            book = book,
                            bookChapter = chapter,
                            nextChapterUrl = params["nextChapterUrl"],
                            needSave = false,
                        )
                    )
                }

                else -> throw IllegalArgumentException("不支持的链路：$chain（search/explore/info/toc/content）")
            }
        }
        val json = io.legado.app.utils.GSON.toJson(result ?: emptyMap<String, Any?>())
        mapOf(
            "chain" to chain,
            "isJsSource" to true,
            "truncated" to (json.length > MAX_RETURN_CHARS),
            "result" to if (json.length > MAX_RETURN_CHARS) json.take(MAX_RETURN_CHARS) else json,
        )
    }

    private fun buildBook(source: BookSource, bookUrl: String): Book {
        return Book(
            bookUrl = bookUrl,
            origin = source.bookSourceUrl,
            originName = source.bookSourceName,
        )
    }

    private fun summary(source: BookSource): Map<String, Any?> {
        val jsLib = source.jsLib
        return mapOf(
            "url" to source.bookSourceUrl,
            "name" to source.bookSourceName,
            "type" to source.bookSourceType,
            "hasExplore" to !source.exploreUrl.isNullOrBlank(),
            "hasLogin" to (!source.loginUi.isNullOrBlank() || !source.loginUrl.isNullOrBlank()),
            "scriptLength" to (source.mainJs?.length ?: 0),
            "jsLibKind" to when {
                jsLib.isNullOrBlank() -> "none"
                jsLib.trimStart().startsWith('{') -> "bundle"
                else -> "legacy"
            },
        )
    }
}
