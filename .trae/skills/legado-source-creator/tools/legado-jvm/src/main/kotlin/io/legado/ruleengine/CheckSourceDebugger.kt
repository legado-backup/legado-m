package io.legado.ruleengine

import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.data.entities.BookSource
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.model.analyzeRule.AnalyzeRule.Companion.setChapter
import io.legado.app.model.analyzeRule.AnalyzeUrl
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URI

/**
 * 书源全流程校验器
 * 原始文件: io.legado.app.service.CheckSourceService + io.legado.app.model.CheckSource
 *
 * 校验流程（非线性，搜索和发现各自独立触发详情→目录→正文）:
 * 1. 域名检查: 验证书源URL是否可访问（Socket 连通性检测）
 * 2. 搜索链: 搜索→详情→目录→正文
 * 3. 发现链: 发现→详情→目录→正文
 *
 * state 状态码（与 BookSourceDebugger 一致）:
 * - 0: 域名检查
 * - 10: 列表页（搜索/发现）
 * - 20: 详情页
 * - 30: 目录页
 * - 40: 正文页
 *
 * 简化说明: WebBook 为 stub，直接使用 AnalyzeUrl/AnalyzeRule 内联实现各阶段逻辑 | 已知上限: 不仿真登录流程、不仿真 WebView JS 执行、不仿真并发超时 | 升级路径: 抽取 WebBook 模块后替换为 WebBook.searchBookAwait 等方法
 */
object CheckSourceDebugger {

    private const val MAX_TOC_PAGE = 100
    private const val MAX_CONTENT_PAGE = 100

    // ==================== 公共 API ====================

    /**
     * 域名检查：验证书源URL是否可访问
     * 源码参照: CheckSourceService.isDomainReachable
     */
    fun checkDomain(source: BookSource): JsonObject {
        val result = JsonObject()
        result.addProperty("state", 0)
        val domain = source.bookSourceUrl

        if (!domain.startsWith("http", true)) {
            result.addProperty("ok", false)
            result.addProperty("error", "源地址不是http链接")
            return result
        }

        val reachable = kotlin.runCatching {
            val url = URI(domain.substringBefore("#"))
            val port = url.port.takeIf { it > 0 } ?: 80
            Socket().use { socket ->
                socket.connect(InetSocketAddress(url.host, port), 1600)
                true
            }
        }.getOrDefault(false)

        result.addProperty("ok", reachable)
        if (!reachable) {
            result.addProperty("error", "源地址不可访问")
        }

        val data = JsonObject()
        data.addProperty("domain", domain)
        data.addProperty("reachable", reachable)
        result.add("data", data)
        return result
    }

    /**
     * 搜索检查：执行搜索，验证返回结果
     * 源码参照: CheckSourceService.doCheckSource 搜索部分 + WebBook.searchBookAwait
     */
    fun checkSearch(source: BookSource, searchKey: String = "测试"): JsonObject {
        val ws = wrapSource(source)
        val book = Book()
        val keyword = source.getCheckKeyword(searchKey)
        return doSearch(source, ws, book, keyword)
    }

    /**
     * 发现检查：执行发现，验证返回结果
     * 源码参照: CheckSourceService.doCheckSource 发现部分 + WebBook.exploreBookAwait
     */
    fun checkExplore(source: BookSource): JsonObject {
        val ws = wrapSource(source)
        val book = Book()
        val exploreUrl = source.exploreUrl
        if (exploreUrl.isNullOrBlank()) {
            return failResult(10, "发现URL为空")
        }
        val firstUrl = parseFirstExploreUrl(exploreUrl)
        if (firstUrl.isNullOrBlank()) {
            return failResult(10, "无法从发现URL中解析出有效地址")
        }
        return doExplore(source, ws, book, firstUrl)
    }

    /**
     * 详情检查：从搜索/发现结果取一本书，获取详情
     * 源码参照: CheckSourceService.checkBook 详情部分 + WebBook.getBookInfoAwait
     */
    fun checkDetail(source: BookSource, bookUrl: String): JsonObject {
        val ws = wrapSource(source)
        val book = Book()
        book.bookUrl = bookUrl
        return doDetail(source, ws, book, bookUrl)
    }

    /**
     * 目录检查：从详情页获取目录
     * 源码参照: CheckSourceService.checkBook 目录部分 + WebBook.getChapterListAwait
     */
    fun checkToc(source: BookSource, bookUrl: String): JsonObject {
        val ws = wrapSource(source)
        val book = Book()
        book.tocUrl = bookUrl
        book.bookUrl = bookUrl
        return doToc(source, ws, book, bookUrl)
    }

    /**
     * 正文检查：从目录取一章，获取正文
     * 源码参照: CheckSourceService.checkBook 正文部分 + WebBook.getContentAwait
     */
    fun checkContent(source: BookSource, chapterUrl: String): JsonObject {
        val ws = wrapSource(source)
        val book = Book()
        return doContent(source, ws, book, chapterUrl, null)
    }

    /**
     * 全流程校验：域名→搜索→详情→目录→正文（非线性）
     * 搜索和发现各自独立触发详情→目录→正文
     * 源码参照: CheckSourceService.doCheckSource + checkBook
     */
    fun checkAll(source: BookSource): JsonObject {
        val ws = wrapSource(source)
        val result = JsonObject()
        val errors = mutableListOf<String>()

        // 1. 域名检查
        val domainResult = checkDomain(source)
        result.add("domain", domainResult)
        if (!domainResult.get("ok").asBoolean) {
            errors.add("域名: ${domainResult.get("error")?.asString}")
        }

        // 2. 搜索链：搜索→详情→目录→正文
        val searchBook = Book()
        val keyword = source.getCheckKeyword("测试")
        val searchResult = doSearch(source, ws, searchBook, keyword)
        result.add("search", searchResult)
        if (searchResult.get("ok").asBoolean) {
            val searchData = searchResult.getAsJsonObject("data")
            val firstBookUrl = searchData?.get("firstBookUrl")?.asString
            if (!firstBookUrl.isNullOrBlank()) {
                val searchChain = checkBookChain(source, ws, searchBook, firstBookUrl, "搜索")
                result.add("searchChain", searchChain)
                if (!searchChain.get("ok").asBoolean) {
                    errors.add(searchChain.get("error")?.asString ?: "搜索链校验失败")
                }
            }
        } else {
            errors.add("搜索: ${searchResult.get("error")?.asString}")
        }

        // 3. 发现链：发现→详情→目录→正文
        if (!source.exploreUrl.isNullOrBlank()) {
            val exploreBook = Book()
            val firstExploreUrl = parseFirstExploreUrl(source.exploreUrl!!)
            if (!firstExploreUrl.isNullOrBlank()) {
                val exploreResult = doExplore(source, ws, exploreBook, firstExploreUrl)
                result.add("explore", exploreResult)
                if (exploreResult.get("ok").asBoolean) {
                    val exploreData = exploreResult.getAsJsonObject("data")
                    val firstBookUrl = exploreData?.get("firstBookUrl")?.asString
                    if (!firstBookUrl.isNullOrBlank()) {
                        val exploreChain = checkBookChain(source, ws, exploreBook, firstBookUrl, "发现")
                        result.add("exploreChain", exploreChain)
                        if (!exploreChain.get("ok").asBoolean) {
                            errors.add(exploreChain.get("error")?.asString ?: "发现链校验失败")
                        }
                    }
                } else {
                    errors.add("发现: ${exploreResult.get("error")?.asString}")
                }
            }
        }

        // 4. 汇总
        val allOk = errors.isEmpty()
        result.addProperty("ok", allOk)
        if (errors.isNotEmpty()) {
            result.addProperty("error", errors.joinToString("; "))
        }
        return result
    }

    // ==================== 私有实现 ====================

    /**
     * 搜索执行（内联 WebBook.searchBookAwait 逻辑）
     */
    private fun doSearch(
        source: BookSource,
        ws: BaseSourceInterface,
        book: Book,
        searchKey: String
    ): JsonObject {
        val searchUrl = source.searchUrl
        if (searchUrl.isNullOrBlank()) {
            return failResult(10, "搜索URL为空")
        }

        return kotlin.runCatching {
            val analyzeUrl = AnalyzeUrl(
                searchUrl,
                key = searchKey,
                page = 1,
                baseUrl = source.bookSourceUrl,
                source = ws,
                ruleData = book
            )
            val response = analyzeUrl.getStrResponse(useWebView = false)

            if (response.code() != 200) {
                return failResult(10, "搜索页请求失败: HTTP ${response.code()}")
            }

            val html = response.body ?: ""
            val analyzeRule = AnalyzeRule(book, source = ws)
            analyzeRule.setContent(html, response.url)

            val bookListRule = source.getSearchRule().bookList
            if (bookListRule.isNullOrBlank()) {
                return failResult(10, "搜索规则 bookList 为空")
            }

            val bookList = analyzeRule.getElements(bookListRule)
            if (bookList.isEmpty()) {
                return failResult(10, "搜索结果为空")
            }

            // 提取第一本书字段
            analyzeRule.setContent(bookList[0], response.url)
            val name = analyzeRule.getString(source.getSearchRule().name)
            val author = analyzeRule.getString(source.getSearchRule().author)
            val bookUrl = analyzeRule.getString(source.getSearchRule().bookUrl, isUrl = true)

            if (name.isNotEmpty()) book.name = name
            if (author.isNotEmpty()) book.author = author
            if (bookUrl.isNotEmpty()) book.bookUrl = bookUrl

            // 构建书籍列表（最多5本）
            val books = JsonArray()
            val maxShow = minOf(bookList.size, 5)
            for (i in 0 until maxShow) {
                if (i > 0) analyzeRule.setContent(bookList[i], response.url)
                val b = JsonObject()
                b.addProperty("name", analyzeRule.getString(source.getSearchRule().name))
                b.addProperty("author", analyzeRule.getString(source.getSearchRule().author))
                b.addProperty("bookUrl", analyzeRule.getString(source.getSearchRule().bookUrl, isUrl = true))
                books.add(b)
            }

            val data = JsonObject()
            data.addProperty("searchKey", searchKey)
            data.addProperty("bookCount", bookList.size)
            data.addProperty("firstBookUrl", bookUrl)
            data.addProperty("firstBookName", name)
            data.add("books", books)
            okResult(10, data)
        }.getOrElse { e ->
            failResult(10, "搜索异常: ${e.message}")
        }
    }

    /**
     * 发现执行（内联 WebBook.exploreBookAwait 逻辑）
     */
    private fun doExplore(
        source: BookSource,
        ws: BaseSourceInterface,
        book: Book,
        url: String
    ): JsonObject {
        return kotlin.runCatching {
            val analyzeUrl = AnalyzeUrl(
                url,
                baseUrl = source.bookSourceUrl,
                source = ws,
                ruleData = book
            )
            val response = analyzeUrl.getStrResponse(useWebView = false)

            if (response.code() != 200) {
                return failResult(10, "发现页请求失败: HTTP ${response.code()}")
            }

            val html = response.body ?: ""
            val analyzeRule = AnalyzeRule(book, source = ws)
            analyzeRule.setContent(html, response.url)

            val bookListRule = source.getExploreRule().bookList
            if (bookListRule.isNullOrBlank()) {
                return failResult(10, "发现规则 bookList 为空")
            }

            val bookList = analyzeRule.getElements(bookListRule)
            if (bookList.isEmpty()) {
                return failResult(10, "发现结果为空")
            }

            // 提取第一本书字段
            analyzeRule.setContent(bookList[0], response.url)
            val name = analyzeRule.getString(source.getExploreRule().name)
            val author = analyzeRule.getString(source.getExploreRule().author)
            val bookUrl = analyzeRule.getString(source.getExploreRule().bookUrl, isUrl = true)

            if (name.isNotEmpty()) book.name = name
            if (author.isNotEmpty()) book.author = author
            if (bookUrl.isNotEmpty()) book.bookUrl = bookUrl

            // 构建书籍列表（最多5本）
            val books = JsonArray()
            val maxShow = minOf(bookList.size, 5)
            for (i in 0 until maxShow) {
                if (i > 0) analyzeRule.setContent(bookList[i], response.url)
                val b = JsonObject()
                b.addProperty("name", analyzeRule.getString(source.getExploreRule().name))
                b.addProperty("author", analyzeRule.getString(source.getExploreRule().author))
                b.addProperty("bookUrl", analyzeRule.getString(source.getExploreRule().bookUrl, isUrl = true))
                books.add(b)
            }

            val data = JsonObject()
            data.addProperty("exploreUrl", url)
            data.addProperty("bookCount", bookList.size)
            data.addProperty("firstBookUrl", bookUrl)
            data.addProperty("firstBookName", name)
            data.add("books", books)
            okResult(10, data)
        }.getOrElse { e ->
            failResult(10, "发现异常: ${e.message}")
        }
    }

    /**
     * 详情执行（内联 WebBook.getBookInfoAwait 逻辑）
     */
    private fun doDetail(
        source: BookSource,
        ws: BaseSourceInterface,
        book: Book,
        bookUrl: String
    ): JsonObject {
        return kotlin.runCatching {
            val analyzeUrl = AnalyzeUrl(
                bookUrl,
                baseUrl = source.bookSourceUrl,
                source = ws,
                ruleData = book
            )
            val response = analyzeUrl.getStrResponse(useWebView = false)

            if (response.code() != 200) {
                return failResult(20, "详情页请求失败: HTTP ${response.code()}")
            }

            val html = response.body ?: ""
            val analyzeRule = AnalyzeRule(book, source = ws)
            analyzeRule.setContent(html, response.url)

            // 执行 init 规则（如有）
            val initRule = source.getBookInfoRule().init
            if (!initRule.isNullOrBlank()) {
                kotlin.runCatching { analyzeRule.getString(initRule) }
            }

            // 提取字段
            val name = analyzeRule.getString(source.getBookInfoRule().name)
            if (name.isNotEmpty()) book.name = name

            val author = analyzeRule.getString(source.getBookInfoRule().author)
            if (author.isNotEmpty()) book.author = author

            val intro = analyzeRule.getString(source.getBookInfoRule().intro)
            if (intro.isNotEmpty()) book.intro = intro

            val coverUrl = analyzeRule.getString(source.getBookInfoRule().coverUrl, isUrl = true)
            if (coverUrl.isNotEmpty()) book.coverUrl = coverUrl

            val tocUrl = analyzeRule.getString(source.getBookInfoRule().tocUrl, isUrl = true)
            val finalTocUrl = tocUrl.ifBlank { response.url }
            book.tocUrl = finalTocUrl

            val kind = analyzeRule.getString(source.getBookInfoRule().kind)
            val lastChapter = analyzeRule.getString(source.getBookInfoRule().lastChapter)

            val data = JsonObject()
            data.addProperty("bookUrl", bookUrl)
            data.addProperty("name", name)
            data.addProperty("author", author)
            data.addProperty("intro", intro.take(200))
            data.addProperty("coverUrl", coverUrl)
            data.addProperty("tocUrl", finalTocUrl)
            data.addProperty("kind", kind)
            data.addProperty("lastChapter", lastChapter)
            okResult(20, data)
        }.getOrElse { e ->
            failResult(20, "详情异常: ${e.message}")
        }
    }

    /**
     * 目录执行（内联 WebBook.getChapterListAwait 逻辑，含 nextTocUrl 分页）
     */
    private fun doToc(
        source: BookSource,
        ws: BaseSourceInterface,
        book: Book,
        tocUrl: String
    ): JsonObject {
        val chapterListRule = source.getTocRule().chapterList
        if (chapterListRule.isNullOrBlank()) {
            return failResult(30, "目录规则 chapterList 为空")
        }

        return kotlin.runCatching {
            var currentTocUrl = tocUrl
            var page = 0
            val allChapters = mutableListOf<BookChapter>()

            // nextTocUrl 分页循环
            while (page < MAX_TOC_PAGE) {
                page++
                val analyzeUrl = AnalyzeUrl(
                    currentTocUrl,
                    baseUrl = book.bookUrl,
                    source = ws,
                    ruleData = book
                )
                val response = analyzeUrl.getStrResponse(useWebView = false)

                if (response.code() != 200) {
                    return failResult(30, "目录页请求失败: HTTP ${response.code()}")
                }

                val html = response.body ?: ""
                val analyzeRule = AnalyzeRule(book, source = ws)
                analyzeRule.setContent(html, response.url)

                val chapterList = analyzeRule.getElements(chapterListRule)
                if (chapterList.isEmpty() && page == 1) {
                    return failResult(30, "目录为空")
                }

                for (chapterElement in chapterList) {
                    analyzeRule.setContent(chapterElement, response.url)
                    val chapterName = analyzeRule.getString(source.getTocRule().chapterName)
                    val chapterUrl = analyzeRule.getString(source.getTocRule().chapterUrl, isUrl = true)
                    allChapters.add(BookChapter(
                        title = chapterName,
                        url = chapterUrl,
                        baseUrl = response.url,
                        bookUrl = book.bookUrl,
                        index = allChapters.size
                    ))
                }

                // 获取 nextTocUrl
                val nextTocUrlRule = source.getTocRule().nextTocUrl
                if (nextTocUrlRule.isNullOrBlank()) break
                val nextTocUrl = analyzeRule.getString(nextTocUrlRule, isUrl = true)
                if (nextTocUrl.isBlank() || nextTocUrl == currentTocUrl) break
                currentTocUrl = nextTocUrl
            }

            if (allChapters.isEmpty()) {
                return failResult(30, "目录为空")
            }

            // 构建章节列表（最多5章）
            val chapters = JsonArray()
            val maxShow = minOf(allChapters.size, 5)
            for (i in 0 until maxShow) {
                val c = JsonObject()
                c.addProperty("title", allChapters[i].title)
                c.addProperty("url", allChapters[i].url)
                chapters.add(c)
            }

            val data = JsonObject()
            data.addProperty("tocUrl", tocUrl)
            data.addProperty("chapterCount", allChapters.size)
            data.addProperty("firstChapterUrl", allChapters[0].url)
            data.addProperty("firstChapterTitle", allChapters[0].title)
            data.add("chapters", chapters)
            okResult(30, data)
        }.getOrElse { e ->
            failResult(30, "目录异常: ${e.message}")
        }
    }

    /**
     * 正文执行（内联 WebBook.getContentAwait 逻辑，含 nextContentUrl 分页 + replaceRegex）
     */
    private fun doContent(
        source: BookSource,
        ws: BaseSourceInterface,
        book: Book,
        chapterUrl: String,
        chapter: BookChapter?
    ): JsonObject {
        return kotlin.runCatching {
            val mockChapter = chapter ?: BookChapter(url = chapterUrl, title = "未知章节")

            val analyzeUrl = AnalyzeUrl(
                chapterUrl,
                baseUrl = book.bookUrl,
                source = ws,
                ruleData = book,
                chapter = mockChapter
            )
            val response = analyzeUrl.getStrResponse(
                jsStr = source.getContentRule().webJs,
                sourceRegex = source.getContentRule().sourceRegex,
                useWebView = false
            )

            if (response.code() != 200) {
                return failResult(40, "正文页请求失败: HTTP ${response.code()}")
            }

            val html = response.body ?: ""
            val analyzeRule = AnalyzeRule(book, source = ws)
            analyzeRule.setChapter(mockChapter)
            analyzeRule.setContent(html, response.url)

            val contentRule = source.getContentRule().content
            if (contentRule.isNullOrBlank()) {
                return failResult(40, "正文规则 content 为空")
            }

            // 获取正文内容（含 nextContentUrl 分页）
            val contentBuilder = StringBuilder()
            contentBuilder.append(analyzeRule.getString(contentRule))

            val nextContentUrlRule = source.getContentRule().nextContentUrl
            if (!nextContentUrlRule.isNullOrBlank()) {
                var currentPage = 0
                var currentUrl = analyzeRule.getString(nextContentUrlRule, isUrl = true)
                while (currentUrl.isNotBlank() && currentPage < MAX_CONTENT_PAGE) {
                    currentPage++
                    val nextAnalyzeUrl = AnalyzeUrl(
                        currentUrl,
                        baseUrl = response.url,
                        source = ws,
                        ruleData = book,
                        chapter = mockChapter
                    )
                    val nextResponse = nextAnalyzeUrl.getStrResponse(useWebView = false)
                    if (nextResponse.code() != 200) break

                    val nextAnalyzeRule = AnalyzeRule(book, source = ws)
                    nextAnalyzeRule.setChapter(mockChapter)
                    nextAnalyzeRule.setContent(nextResponse.body ?: "", nextResponse.url)
                    contentBuilder.append(nextAnalyzeRule.getString(contentRule))
                    currentUrl = nextAnalyzeRule.getString(nextContentUrlRule, isUrl = true)
                }
            }

            var content = contentBuilder.toString()

            // 应用 replaceRegex
            val replaceRegexRule = source.getContentRule().replaceRegex
            if (!replaceRegexRule.isNullOrBlank()) {
                kotlin.runCatching {
                    content = analyzeRule.getString(replaceRegexRule, content)
                }
            }

            val data = JsonObject()
            data.addProperty("chapterUrl", chapterUrl)
            data.addProperty("chapterTitle", mockChapter.title)
            data.addProperty("contentLength", content.length)
            data.addProperty("contentPreview", content.take(500))
            okResult(40, data)
        }.getOrElse { e ->
            failResult(40, "正文异常: ${e.message}")
        }
    }

    /**
     * 详情→目录→正文链式校验（对应真机 CheckSourceService.checkBook）
     * 搜索和发现各自独立调用此方法
     */
    private fun checkBookChain(
        source: BookSource,
        ws: BaseSourceInterface,
        book: Book,
        bookUrl: String,
        label: String
    ): JsonObject {
        val result = JsonObject()
        val stages = JsonObject()

        // 1. 详情
        val detailResult = doDetail(source, ws, book, bookUrl)
        stages.add("detail", detailResult)
        if (!detailResult.get("ok").asBoolean) {
            result.addProperty("ok", false)
            result.addProperty("error", "${label}详情失效: ${detailResult.get("error")?.asString}")
            result.add("stages", stages)
            return result
        }

        // 2. 目录
        val tocUrl = book.tocUrl.ifBlank { bookUrl }
        val tocResult = doToc(source, ws, book, tocUrl)
        stages.add("toc", tocResult)
        if (!tocResult.get("ok").asBoolean) {
            result.addProperty("ok", false)
            result.addProperty("error", "${label}目录失效: ${tocResult.get("error")?.asString}")
            result.add("stages", stages)
            return result
        }

        // 3. 正文
        val tocData = tocResult.getAsJsonObject("data")
        val firstChapterUrl = tocData?.get("firstChapterUrl")?.asString
        if (firstChapterUrl.isNullOrBlank()) {
            result.addProperty("ok", false)
            result.addProperty("error", "${label}正文失效: 无可用章节")
            result.add("stages", stages)
            return result
        }

        val contentResult = doContent(source, ws, book, firstChapterUrl, null)
        stages.add("content", contentResult)
        if (!contentResult.get("ok").asBoolean) {
            result.addProperty("ok", false)
            result.addProperty("error", "${label}正文失效: ${contentResult.get("error")?.asString}")
            result.add("stages", stages)
            return result
        }

        result.addProperty("ok", true)
        result.add("stages", stages)
        return result
    }

    // ==================== 辅助方法 ====================

    /**
     * 从 exploreUrl 中解析第一个有效 URL
     * 支持格式: 文本(title::url 分隔) 和 JSON 数组
     * 简化说明: 不支持 @js:/<js> 发现URL规则 | 已知上限: 仅支持文本格式和JSON数组 | 升级路径: 需要时补充 JS 执行
     */
    private fun parseFirstExploreUrl(exploreUrl: String): String? {
        if (exploreUrl.isBlank()) return null
        return kotlin.runCatching {
            val trimmed = exploreUrl.trim()
            if (trimmed.startsWith("[")) {
                // JSON 数组格式: [{"title":"...", "url":"..."}, ...]
                val array = JsonParser.parseString(trimmed).asJsonArray
                for (item in array) {
                    val url = item.asJsonObject.get("url")?.asString
                    if (!url.isNullOrBlank()) return url
                }
                null
            } else {
                // 文本格式: title::url，按 && 或 \n 分隔
                exploreUrl.split("(&&|\n)+".toRegex()).forEach { kindStr ->
                    val parts = kindStr.split("::")
                    if (parts.size >= 2) {
                        val url = parts[1].trim()
                        if (url.isNotBlank()) return url
                    }
                }
                null
            }
        }.getOrNull()
    }

    private fun failResult(state: Int, error: String): JsonObject {
        val result = JsonObject()
        result.addProperty("ok", false)
        result.addProperty("state", state)
        result.addProperty("error", error)
        return result
    }

    private fun okResult(state: Int, data: JsonObject): JsonObject {
        val result = JsonObject()
        result.addProperty("ok", true)
        result.addProperty("state", state)
        result.add("data", data)
        return result
    }
}
