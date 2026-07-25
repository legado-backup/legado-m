package io.legado.ruleengine

import com.google.gson.JsonObject
import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.data.entities.BookSource
import io.legado.app.help.http.StrResponse
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.model.analyzeRule.AnalyzeRule.Companion.setChapter
import io.legado.app.model.analyzeRule.AnalyzeRule.Companion.setNextChapterUrl
import io.legado.app.model.analyzeRule.AnalyzeUrl
import io.legado.app.model.analyzeRule.RuleData
import io.legado.app.utils.HtmlFormatter

/**
 * 端到端书源调试器
 * 原始文件: io.legado.app.model.Debug (searchDebug→infoDebug→tocDebug→contentDebug)
 *
 * 调试链路: search → detail → toc → content
 * - 变量跨阶段持久化: Book.variableMap
 * - Cookie 跨阶段持久化: CookieStoreStub（内存实现）
 * - 日志格式与真机 Debug.kt 一致
 *
 * 内联实现书源执行流程（4 阶段）:
 * 1. 搜索: AnalyzeUrl 构造请求 → getStrResponse → AnalyzeRule.getElements 解析书籍列表
 * 2. 详情: AnalyzeUrl 构造请求 → AnalyzeRule.getString 解析书籍信息
 * 3. 目录: AnalyzeUrl 构造请求 → AnalyzeRule.getElements 解析章节列表（含 nextTocUrl 分页）
 * 4. 正文: AnalyzeUrl 构造请求 → AnalyzeRule.getString 解析正文（含 nextContentUrl 分页 + replaceRegex）
 *
 * 三层 evalJS 注入变量差异（由抽取后的类自动处理）:
 * - AnalyzeUrl 层: URL 中的 @js/<js>/{{js}}（注入 java/baseUrl/cookie/cache/page/key/book/source/result）
 * - AnalyzeRule 层: 规则中的 @js/<js>/{{js}}（注入 java/cookie/cache/source/book/result/baseUrl/chapter/title/src）
 *
 * 简化说明: 从旧 MVP4 迁移，替换 MockSource/MinimalMockJsExtensions/MockBook/MockBookChapter 为抽取后的 BookSource/AnalyzeRule/AnalyzeUrl/Book/BookChapter | 已知上限: 不仿真登录流程、不仿真 WebView JS 执行 | 升级路径: 需要时补充登录流程
 */
class BookSourceDebugger(
    private val sourceJson: String,
    private val key: String,
    private val logger: DebugLogger
) {
    private val bookSource: BookSource = parseBookSource(sourceJson) ?: BookSource(bookSourceUrl = "unknown")
    private val source: BaseSourceInterface = wrapSource(bookSource)
    private val book = Book()

    // 修复9.3 GAP-24: 取消机制（对齐真机 Debug.kt cancelDebug 通过 Job.cancel() 实现）
    @Volatile
    private var cancelled = false

    /**
     * 取消调试
     * 真机通过 Job.cancel() 实现，仿真端通过标志位在循环中检查
     */
    fun cancel() {
        cancelled = true
    }

    /**
     * 检查是否已取消，若已取消则抛出 InterruptedException 中断当前流程
     */
    private fun checkCancelled() {
        if (cancelled) {
            throw InterruptedException("调试已取消")
        }
    }

    companion object {
        private const val MAX_TOC_PAGE = 100
        private const val MAX_CONTENT_PAGE = 100
    }

    /**
     * 修复 GAP-67a: 执行请求并检测 loginCheckJs（对齐真机 WebBook.searchBookAwait 第70-94行）
     * 真机模式: getStrResponse → evalJS(checkJs, response) → 若 code==500 表示需要登录
     * 异常模式: getStrResponse 失败 → getErrStrResponse → evalJS(checkJs, errResponse) → 若 code==500 抛出原异常
     * 简化说明: 仿真端 evalJS 返回 StrResponse 时检测 code==500 抛 UserInterventionException | 已知上限: 无登录UI交互 | 升级路径: 接入登录流程
     */
    private fun executeRequest(
        analyzeUrl: AnalyzeUrl,
        stage: String,
        jsStr: String? = null,
        sourceRegex: String? = null,
        useWebView: Boolean = false
    ): StrResponse {
        val checkJs = bookSource.loginCheckJs
        // 修复 GAP-67a: 异常时尝试 loginCheckJs 检测（对齐真机 runCatching getOrElse 逻辑）
        val response = try {
            analyzeUrl.getStrResponse(jsStr, sourceRegex, useWebView)
        } catch (e: Exception) {
            if (checkJs.isNullOrBlank()) throw e
            val errResponse = analyzeUrl.getErrStrResponse(e)
            try {
                val result = analyzeUrl.evalJS(checkJs, errResponse) as? StrResponse
                if (result != null && result.code() == 500) {
                    throw UserInterventionException(stage, "需要登录")
                }
                result ?: throw e
            } catch (uie: UserInterventionException) {
                throw uie
            } catch (_: Exception) {
                throw e
            }
        }
        // 修复 GAP-67a: 成功时检测 loginCheckJs
        if (checkJs.isNullOrBlank()) return response
        return try {
            val result = analyzeUrl.evalJS(checkJs, response) as? StrResponse
            if (result != null && result.code() == 500) {
                throw UserInterventionException(stage, "需要登录")
            }
            result ?: response
        } catch (e: UserInterventionException) {
            throw e
        } catch (e: Exception) {
            logger.log("⚠️ loginCheckJs 执行失败: ${e.message}")
            response
        }
    }

    /**
     * 修复 GAP-67e: 检测重定向（对齐真机 WebBook.checkRedirect 第504-512行）
     * 真机模式: 检查 response.raw.priorResponse?.isRedirect，记录重定向日志
     */
    private fun checkRedirect(response: StrResponse) {
        response.raw.priorResponse?.let {
            if (it.isRedirect) {
                logger.log("≡检测到重定向(${it.code})")
                logger.log("┌重定向后地址")
                logger.log("└${response.url}")
            }
        }
    }

    /**
     * 调试入口 - 根据 key 格式分发
     * - isAbsUrl → 详情页调试
     * - 含 "::" → 发现页调试
     * - 以 "++" 开头 → 目录页调试
     * - 以 "--" 开头 → 正文页调试
     * - else → 搜索页调试（完整链路）
     *
     * 修复9.4 GAP-25: 添加 validateMode 参数，校验模式下只检查规则是否存在，不执行请求
     *
     * @param validateMode true 时只校验规则是否存在，不执行完整调试
     */
    fun debug(validateMode: Boolean = false): DebugResult {
        return try {
            if (validateMode) {
                return validateRules()
            }
            when {
                isAbsUrl(key) -> debugInfo(key)
                key.contains("::") -> debugExplore()
                key.startsWith("++") -> debugToc(key.removePrefix("++"))
                key.startsWith("--") -> debugContent(key.removePrefix("--"))
                else -> debugSearch()
            }
        } catch (e: WebViewRequiredException) {
            logger.error(
                msg = "需要WebView渲染: ${e.message}",
                stackTrace = e.stackTraceToString(),
                failedStage = e.stage
            )
            DebugResult(
                success = false,
                needsWebView = true,
                webViewRequests = e.requests,
                errorStage = e.stage,
                errorMessage = e.message
            )
        } catch (e: UserInterventionException) {
            logger.error(
                msg = "需要用户介入: ${e.message}",
                stackTrace = e.stackTraceToString(),
                failedStage = e.stage
            )
            DebugResult(
                success = false,
                needsUserIntervention = true,
                errorStage = e.stage,
                errorMessage = e.message
            )
        } catch (e: InterruptedException) {
            // 修复9.3 GAP-24: 取消调试
            logger.log("⇒调试已取消")
            DebugResult(
                success = false,
                errorStage = "cancelled",
                errorMessage = "调试已取消"
            )
        } catch (e: Exception) {
            logger.error(
                msg = "调试异常: ${e.message}",
                stackTrace = e.stackTraceToString(),
                failedStage = "unknown"
            )
            DebugResult(
                success = false,
                errorStage = "unknown",
                errorMessage = e.message
            )
        }
    }

    // ==================== 校验模式（GAP-25） ====================

    /**
     * 修复9.4 GAP-25: 校验模式
     * 只检查必填规则是否存在，不执行网络请求
     * 真机 Debug.kt 中通过 startChecking/finishChecking 实现，仿真端简化为静态规则校验
     */
    private fun validateRules(): DebugResult {
        logger.log("⇒开始校验规则（校验模式）")
        logger.separator()

        val missingRules = mutableListOf<String>()

        // 必填: bookSourceUrl
        if (bookSource.bookSourceUrl.isNullOrBlank()) {
            missingRules.add("bookSourceUrl")
        }
        // 必填: searchUrl（书源必须支持搜索）
        if (bookSource.searchUrl.isNullOrBlank()) {
            missingRules.add("searchUrl")
        }
        // 必填: 搜索规则 bookList
        val searchBookList = bookSource.getSearchRule().bookList
        if (searchBookList.isNullOrBlank()) {
            missingRules.add("searchRule.bookList")
        }
        // 必填: 目录规则 chapterList
        val tocChapterList = bookSource.getTocRule().chapterList
        if (tocChapterList.isNullOrBlank()) {
            missingRules.add("tocRule.chapterList")
        }
        // 必填: 正文规则 content
        val contentRule = bookSource.getContentRule().content
        if (contentRule.isNullOrBlank()) {
            missingRules.add("contentRule.content")
        }

        // 可选规则校验（仅提示，不计入失败）
        if (bookSource.getSearchRule().name.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: searchRule.name")
        if (bookSource.getSearchRule().author.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: searchRule.author")
        if (bookSource.getSearchRule().bookUrl.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: searchRule.bookUrl")
        if (bookSource.getTocRule().chapterName.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: tocRule.chapterName")
        if (bookSource.getTocRule().chapterUrl.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: tocRule.chapterUrl")

        return if (missingRules.isEmpty()) {
            logger.log("✓ 必填规则校验通过")
            val summary = JsonObject().apply {
                addProperty("mode", "validate")
                addProperty("result", "passed")
            }
            logger.result(success = true, summary = summary)
            DebugResult(success = true, summary = summary)
        } else {
            val errorMsg = "必填规则缺失: ${missingRules.joinToString(", ")}"
            logger.error(msg = errorMsg, failedStage = "validate")
            val summary = JsonObject().apply {
                addProperty("mode", "validate")
                addProperty("result", "failed")
                addProperty("missingRules", missingRules.joinToString(","))
            }
            DebugResult(
                success = false,
                errorStage = "validate",
                errorMessage = errorMsg,
                summary = summary
            )
        }
    }

    // ==================== 搜索阶段 ====================

    private fun debugSearch(): DebugResult {
        logger.log("⇒开始搜索关键字:$key")
        logger.log("︾开始解析搜索页")
        logger.separator()

        val searchUrl = bookSource.searchUrl
        if (searchUrl.isNullOrBlank()) {
            logger.error(msg = "搜索URL为空", failedStage = "search")
            return DebugResult(success = false, errorStage = "search", errorMessage = "搜索URL为空")
        }

        // 1. 构造搜索 URL 并请求
        // 修复 GAP-39: 搜索阶段创建独立 RuleData()，避免 book 共享导致并发冲突（对齐真机 WebBook.searchBookAwait）
        val searchRuleData = RuleData()
        val analyzeUrl = AnalyzeUrl(
            searchUrl,
            key = key,
            page = 1,
            baseUrl = bookSource.bookSourceUrl,
            source = source,
            ruleData = searchRuleData
        )
        // 修复 GAP-67a: 执行请求并检测 loginCheckJs
        val response = executeRequest(analyzeUrl, "search")
        // 修复 GAP-67e: 检测重定向
        checkRedirect(response)

        if (response.code() != 200) {
            logger.error(
                msg = "搜索页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                failedStage = "search"
            )
            return DebugResult(
                success = false,
                errorStage = "search",
                errorMessage = "搜索页请求失败: HTTP ${response.code()}"
            )
        }

        val html = response.body ?: ""
        logger.log("≡获取成功:${response.url}", state = 10, html = html)
        logger.separator()

        // 2. 解析搜索列表
        val analyzeRule = AnalyzeRule(book, source = source)
        analyzeRule.setContent(html, response.url)

        val bookListRule = bookSource.getSearchRule().bookList
        if (bookListRule.isNullOrBlank()) {
            logger.error(msg = "搜索规则 bookList 为空", failedStage = "search")
            return DebugResult(success = false, errorStage = "search", errorMessage = "搜索规则 bookList 为空")
        }

        val bookList = analyzeRule.getElements(bookListRule)
        logger.log("┌获取书籍列表")
        logger.log("└列表大小:${bookList.size}")

        if (bookList.isEmpty()) {
            val analysis = HtmlStructureAnalyzer().analyze(html)
            logger.log("[HTML结构分析-搜索页]\n$analysis", state = 10)
            logger.error(msg = "搜索结果为空", failedStage = "search")
            return DebugResult(success = false, errorStage = "search", errorMessage = "搜索结果为空")
        }

        // 3. 提取第一本书字段
        val firstBook = bookList[0]
        analyzeRule.setContent(firstBook, response.url)

        val name = analyzeRule.getString(bookSource.getSearchRule().name)
        logger.log("┌获取书名")
        logger.log("└$name")
        if (name.isNotEmpty()) book.name = name

        val author = analyzeRule.getString(bookSource.getSearchRule().author)
        logger.log("┌获取作者")
        logger.log("└$author")
        if (author.isNotEmpty()) book.author = author

        val bookUrl = analyzeRule.getString(bookSource.getSearchRule().bookUrl, isUrl = true)
        logger.log("┌获取详情页链接")
        logger.log("└$bookUrl")

        val intro = analyzeRule.getString(bookSource.getSearchRule().intro)
        if (intro.isNotEmpty()) {
            logger.log("┌获取简介")
            logger.log("└${intro.take(100)}${if (intro.length > 100) "..." else ""}")
            book.intro = intro
        }

        val coverUrl = analyzeRule.getString(bookSource.getSearchRule().coverUrl, isUrl = true)
        if (coverUrl.isNotEmpty()) {
            logger.log("┌获取封面链接")
            logger.log("└$coverUrl")
            book.coverUrl = coverUrl
        }

        logger.log("◇书籍总数:${bookList.size}")
        logger.log("︽搜索页解析完成")
        logger.separator()

        // 4. 继续详情阶段
        return if (bookUrl.isNotEmpty()) {
            book.bookUrl = bookUrl
            debugInfo(bookUrl)
        } else {
            logger.error(msg = "详情页链接为空，无法继续", failedStage = "search")
            DebugResult(success = false, errorStage = "search", errorMessage = "详情页链接为空，无法继续")
        }
    }

    // ==================== 发现阶段 ====================

    private fun debugExplore(): DebugResult {
        val exploreUrl = key.substringAfter("::")
        logger.log("⇒开始访问发现页:$exploreUrl")
        logger.log("︾开始解析发现页")
        logger.separator()

        if (exploreUrl.isBlank()) {
            logger.error(msg = "发现页URL为空", failedStage = "explore")
            return DebugResult(success = false, errorStage = "explore", errorMessage = "发现页URL为空")
        }

        // 1. 构造发现页 URL 并请求
        // 修复 GAP-39: 发现阶段创建独立 RuleData()，避免 book 共享导致并发冲突（对齐真机 WebBook.exploreBookAwait）
        // 简化说明: infoMap 传 null，仿真端无 UI 筛选交互（真机 exploreInfoMapList 来自 ExploreAdapter） | 已知上限: 不支持发现页筛选规则 | 升级路径: 需实现 exploreInfoMapList 解析
        val exploreRuleData = RuleData()
        val analyzeUrl = AnalyzeUrl(
            exploreUrl,
            page = 1,
            baseUrl = bookSource.bookSourceUrl,
            source = source,
            ruleData = exploreRuleData
        )
        // 修复 GAP-67a: 执行请求并检测 loginCheckJs
        val response = executeRequest(analyzeUrl, "explore")
        // 修复 GAP-67e: 检测重定向
        checkRedirect(response)

        if (response.code() != 200) {
            logger.error(
                msg = "发现页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                failedStage = "explore"
            )
            return DebugResult(
                success = false,
                errorStage = "explore",
                errorMessage = "发现页请求失败: HTTP ${response.code()}"
            )
        }

        val html = response.body ?: ""
        logger.log("≡获取成功:${response.url}", state = 10, html = html)
        logger.separator()

        // 2. 解析发现页列表
        val analyzeRule = AnalyzeRule(book, source = source)
        analyzeRule.setContent(html, response.url)

        val bookListRule = bookSource.getExploreRule().bookList
        if (bookListRule.isNullOrBlank()) {
            logger.error(msg = "发现规则 bookList 为空", failedStage = "explore")
            return DebugResult(success = false, errorStage = "explore", errorMessage = "发现规则 bookList 为空")
        }

        val bookList = analyzeRule.getElements(bookListRule)
        logger.log("┌获取书籍列表")
        logger.log("└列表大小:${bookList.size}")
        // 诊断日志: 发现页解析详情
        System.err.println("[DIAG] 发现页 bookListRule=$bookListRule")
        System.err.println("[DIAG] 发现页 HTML长度=${html.length}, 书籍数=${bookList.size}")
        if (bookList.isNotEmpty()) {
            System.err.println("[DIAG] 第一本书类型=${bookList[0]?.javaClass?.name}, 值=${bookList[0]?.toString()?.take(100)}")
        }

        if (bookList.isEmpty()) {
            val analysis = HtmlStructureAnalyzer().analyze(html)
            logger.log("[HTML结构分析-发现页]\n$analysis", state = 10)
            logger.error(msg = "发现页结果为空", failedStage = "explore")
            return DebugResult(success = false, errorStage = "explore", errorMessage = "发现页结果为空")
        }

        // 3. 提取第一本书字段
        val firstBook = bookList[0]
        analyzeRule.setContent(firstBook, response.url)

        val name = analyzeRule.getString(bookSource.getExploreRule().name)
        logger.log("┌获取书名")
        logger.log("└$name")
        if (name.isNotEmpty()) book.name = name

        val author = analyzeRule.getString(bookSource.getExploreRule().author)
        logger.log("┌获取作者")
        logger.log("└$author")
        if (author.isNotEmpty()) book.author = author

        val bookUrl = analyzeRule.getString(bookSource.getExploreRule().bookUrl, isUrl = true)
        logger.log("┌获取详情页链接")
        logger.log("└$bookUrl")

        val intro = analyzeRule.getString(bookSource.getExploreRule().intro)
        if (intro.isNotEmpty()) {
            logger.log("┌获取简介")
            logger.log("└${intro.take(100)}${if (intro.length > 100) "..." else ""}")
            book.intro = intro
        }

        val coverUrl = analyzeRule.getString(bookSource.getExploreRule().coverUrl, isUrl = true)
        if (coverUrl.isNotEmpty()) {
            logger.log("┌获取封面链接")
            logger.log("└$coverUrl")
            book.coverUrl = coverUrl
        }

        logger.log("◇书籍总数:${bookList.size}")
        logger.log("︽发现页解析完成")
        logger.separator()

        // 4. 继续详情阶段
        return if (bookUrl.isNotEmpty()) {
            book.bookUrl = bookUrl
            debugInfo(bookUrl)
        } else {
            logger.error(msg = "详情页链接为空，无法继续", failedStage = "explore")
            DebugResult(success = false, errorStage = "explore", errorMessage = "详情页链接为空，无法继续")
        }
    }

    // ==================== 详情阶段 ====================

    private fun debugInfo(bookUrl: String): DebugResult {
        // 修复 GAP-40: 详情阶段重置 BookType（对齐真机 WebBook.getBookInfoAwait 第197-198行）
        // 简化说明: 内联 removeAllBookType+addType 逻辑，不引入 BookType 常量文件 | 已知上限: 无 | 升级路径: 创建 BookType.kt 和扩展函数
        val allBookType = 0b111011100  // video(4) | text(8) | audio(32) | image(64) | webFile(128)
        book.type = book.type and allBookType.inv()  // removeAllBookType
        book.type = book.type or when (bookSource.bookSourceType) {
            3 -> 0b10001000  // file -> text(8) | webFile(128)
            2 -> 0b1000000   // image -> image(64)
            1 -> 0b100000    // audio -> audio(32)
            4 -> 0b100       // video -> video(4)
            else -> 0b1000   // default -> text(8)
        }

        // 差距2: tocUrl 已有值时跳过详情页（与真机 Debug.kt 第313-318行一致）
        if (book.tocUrl.isNotBlank()) {
            logger.log("≡已获取目录链接,跳过详情页")
            logger.separator()
            return debugToc(book.tocUrl)
        }
        logger.log("⇒开始访问详情页:$bookUrl")
        logger.log("︾开始解析详情页")
        logger.separator()

        // 1. 构造详情 URL 并请求
        val analyzeUrl = AnalyzeUrl(
            bookUrl,
            baseUrl = bookSource.bookSourceUrl,
            source = source,
            ruleData = book
        )
        // 修复 GAP-67a: 执行请求并检测 loginCheckJs
        val response = executeRequest(analyzeUrl, "detail")
        // 修复 GAP-67e: 检测重定向
        checkRedirect(response)

        if (response.code() != 200) {
            logger.error(
                msg = "详情页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                failedStage = "detail"
            )
            return DebugResult(
                success = false,
                errorStage = "detail",
                errorMessage = "详情页请求失败: HTTP ${response.code()}"
            )
        }

        val html = response.body ?: ""
        logger.log("≡获取成功:${response.url}", state = 20, html = html)
        logger.separator()

        // 2. 解析详情页
        val analyzeRule = AnalyzeRule(book, source = source)
        analyzeRule.setContent(html, response.url)
        // 保存详情页URL，用于后续init规则执行后恢复baseUrl上下文
        val detailPageUrl = response.url

        // 3. 执行 init 规则（如有）
        val initRule = bookSource.getBookInfoRule().init
        if (!initRule.isNullOrBlank()) {
            logger.log("┌执行 init 规则")
            // 诊断日志: init规则内容
            System.err.println("[DIAG] init规则: ${initRule.take(200)}")
            try {
                // 修复 GAP-67c: init 规则执行方式改为 getElement（对齐真机 BookInfo.kt 第62行）
                // 真机模式: analyzeRule.setContent(analyzeRule.getElement(initRule))
                val initResult = analyzeRule.getElement(initRule)
                System.err.println("[DIAG] init规则返回: type=${initResult?.javaClass?.name}, value=${initResult?.toString()?.take(100)}")
                // 修复: init规则执行后setContent需要传baseUrl，否则后续@get:{url}等规则无法拼接相对路径
                analyzeRule.setContent(initResult, detailPageUrl)
                analyzeRule.setRedirectUrl(detailPageUrl)
                logger.log("└init 执行完成")
            } catch (e: Exception) {
                // 诊断日志: init规则执行失败
                System.err.println("[DIAG] init规则异常: ${e.javaClass.name}: ${e.message}")
                logger.log("└init 执行失败: ${e.message}")
            }
        }

        // 4. 提取字段
        val name = analyzeRule.getString(bookSource.getBookInfoRule().name)
        if (name.isNotEmpty()) {
            logger.log("┌获取书名")
            logger.log("└$name")
            book.name = name
        } else {
            val analysis = HtmlStructureAnalyzer().analyze(html)
            logger.log("[HTML结构分析-详情页]\n$analysis", state = 20)
        }

        val author = analyzeRule.getString(bookSource.getBookInfoRule().author)
        if (author.isNotEmpty()) {
            logger.log("┌获取作者")
            logger.log("└$author")
            book.author = author
        }

        val intro = analyzeRule.getString(bookSource.getBookInfoRule().intro)
        if (intro.isNotEmpty()) {
            logger.log("┌获取简介")
            // 修复 GAP-67d: 移植完整正文格式化链（对齐真机 BookInfo.kt 第122-133行）
            // 真机模式: <usehtml>/<md>/<useweb> 开头保持原样，否则 HtmlFormatter.format
            val introTrimS = intro.trimStart()
            val formattedIntro = if (introTrimS.startsWith("<usehtml>") ||
                introTrimS.startsWith("<md>") || introTrimS.startsWith("<useweb>")) {
                introTrimS
            } else {
                HtmlFormatter.format(intro)
            }
            logger.log("└${formattedIntro.take(100)}${if (formattedIntro.length > 100) "..." else ""}")
            book.intro = formattedIntro
        }

        val coverUrl = analyzeRule.getString(bookSource.getBookInfoRule().coverUrl, isUrl = true)
        if (coverUrl.isNotEmpty()) {
            logger.log("┌获取封面链接")
            logger.log("└$coverUrl")
            book.coverUrl = coverUrl
        }

        val tocUrl = analyzeRule.getString(bookSource.getBookInfoRule().tocUrl, isUrl = true)
        // 诊断日志: tocUrl规则执行结果
        System.err.println("[DIAG] tocUrl规则: ${bookSource.getBookInfoRule().tocUrl?.take(100)}")
        System.err.println("[DIAG] tocUrl结果: $tocUrl")
        logger.log("┌获取目录链接")
        logger.log("└${tocUrl.ifBlank { response.url }}")

        val kind = analyzeRule.getString(bookSource.getBookInfoRule().kind)
        if (kind.isNotEmpty()) {
            logger.log("┌获取分类")
            logger.log("└$kind")
            book.kind = kind
        }

        val lastChapter = analyzeRule.getString(bookSource.getBookInfoRule().lastChapter)
        if (lastChapter.isNotEmpty()) {
            logger.log("┌获取最新章节")
            logger.log("└$lastChapter")
        }

        logger.log("︽详情页解析完成")
        logger.separator()

        // 5. 继续目录阶段
        val finalTocUrl = tocUrl.ifBlank { response.url }
        book.tocUrl = finalTocUrl
        // 差距3: 文件类书源跳过目录解析（与真机 Debug.kt 第324-328行一致）
        // 简化说明: 直接用 type 位判断 webFile(0b10000000)，不引入 BookType 常量 | 已知上限: 无 | 升级路径: 引入 BookType 常量时替换魔法数
        return if (book.type and 0b10000000 != 0) {
            logger.log("≡文件类书源跳过解析目录", state = 1000)
            DebugResult(success = true)
        } else {
            debugToc(finalTocUrl)
        }
    }

    // ==================== 目录阶段 ====================

    private fun debugToc(tocUrl: String): DebugResult {
        logger.log("⇒开始访问目录页:$tocUrl")
        logger.log("︾开始解析目录页")
        logger.separator()

        val chapterListRule = bookSource.getTocRule().chapterList
        if (chapterListRule.isNullOrBlank()) {
            logger.error(msg = "目录规则 chapterList 为空", failedStage = "toc")
            return DebugResult(success = false, errorStage = "toc", errorMessage = "目录规则 chapterList 为空")
        }

        var currentTocUrl = tocUrl
        var page = 0
        val allChapters = mutableListOf<BookChapter>()

        // nextTocUrl 分页循环
        while (page < MAX_TOC_PAGE) {
            // 修复9.3 GAP-24: 取消检查
            checkCancelled()
            page++

            // 1. 构造目录 URL 并请求
            val analyzeUrl = AnalyzeUrl(
                currentTocUrl,
                baseUrl = book.bookUrl,
                source = source,
                ruleData = book
            )
            // 修复 GAP-67a: 执行请求并检测 loginCheckJs
            val response = executeRequest(analyzeUrl, "toc")
            // 修复 GAP-67e: 检测重定向
            checkRedirect(response)

            if (response.code() != 200) {
                logger.error(
                    msg = "目录页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                    failedStage = "toc"
                )
                return DebugResult(
                    success = false,
                    errorStage = "toc",
                    errorMessage = "目录页请求失败: HTTP ${response.code()}"
                )
            }

            val html = response.body ?: ""
            if (page == 1) {
                logger.log("≡获取成功:${response.url}", state = 30, html = html)
                logger.separator()
            }

            // 2. 解析目录列表
            val analyzeRule = AnalyzeRule(book, source = source)
            analyzeRule.setContent(html, response.url)

            val chapterList = analyzeRule.getElements(chapterListRule)
            if (page == 1) {
                logger.log("┌获取目录列表")
                logger.log("└本页章节数:${chapterList.size}")
                // 诊断日志: 目录页解析详情
                System.err.println("[DIAG] 目录页 chapterListRule=$chapterListRule")
                System.err.println("[DIAG] 目录页 HTML长度=${html.length}, 章节数=${chapterList.size}")
                if (chapterList.isNotEmpty()) {
                    System.err.println("[DIAG] 第一章节类型=${chapterList[0]?.javaClass?.name}, 值=${chapterList[0]?.toString()?.take(100)}")
                }
            }

            if (chapterList.isEmpty() && page == 1) {
                val analysis = HtmlStructureAnalyzer().analyze(html)
                logger.log("[HTML结构分析-目录页]\n$analysis", state = 30)
                logger.error(msg = "目录为空", failedStage = "toc")
                return DebugResult(success = false, errorStage = "toc", errorMessage = "目录为空")
            }

            // 3. 提取章节字段
            for ((index, chapterElement) in chapterList.withIndex()) {
                analyzeRule.setContent(chapterElement, response.url)

                val chapterName = analyzeRule.getString(bookSource.getTocRule().chapterName)
                val chapterUrl = analyzeRule.getString(bookSource.getTocRule().chapterUrl, isUrl = true)

                val chapter = BookChapter(
                    title = chapterName,
                    url = chapterUrl,
                    baseUrl = response.url,
                    bookUrl = book.bookUrl,
                    index = allChapters.size
                )
                allChapters.add(chapter)

                // 首页前5章输出详细日志
                if (page == 1 && index < 5) {
                    logger.log("┌获取章节名[$index]")
                    logger.log("└$chapterName")
                    logger.log("┌获取章节链接[$index]")
                    logger.log("└$chapterUrl")
                }
            }

            // 4. 获取 nextTocUrl
            val nextTocUrlRule = bookSource.getTocRule().nextTocUrl
            if (nextTocUrlRule.isNullOrBlank()) break

            // 修复: JSONPath字段不存在时会抛出PathNotFoundException，需要捕获
            val nextTocUrl = try {
                analyzeRule.getString(nextTocUrlRule, isUrl = true)
            } catch (e: Exception) {
                System.err.println("[DIAG] nextTocUrl解析异常: ${e.javaClass.name}: ${e.message}")
                ""
            }
            if (nextTocUrl.isBlank() || nextTocUrl == currentTocUrl) break

            currentTocUrl = nextTocUrl
        }

        logger.log("◇目录总数:${allChapters.size}")
        logger.log("︽目录页解析完成")
        logger.separator()

        // 5. 过滤卷标题并继续正文阶段（与真机 Debug.kt 第342行一致）
        val validChapters = allChapters.filter { !(it.isVolume && it.url.startsWith(it.title)) }
        return if (validChapters.isNotEmpty()) {
            // 差距1: 计算 nextChapterUrl 并传递（与真机 Debug.kt 第347行一致）
            val nextChapterUrl = validChapters.getOrNull(1)?.url ?: validChapters[0].url
            debugContent(validChapters[0].url, validChapters[0], nextChapterUrl, validChapters.size)
        } else {
            logger.error(msg = "无可用章节，无法调试正文", failedStage = "toc")
            DebugResult(success = false, errorStage = "toc", errorMessage = "无可用章节，无法调试正文")
        }
    }

    // ==================== 正文阶段 ====================

    private fun debugContent(chapterUrl: String, chapter: BookChapter? = null, nextChapterUrl: String? = null, tocCount: Int = 0): DebugResult {
        logger.log("⇒开始访问正文页:$chapterUrl")
        logger.log("︾开始解析正文页")
        logger.separator()

        val mockChapter = chapter ?: BookChapter(url = chapterUrl, title = "未知章节")

        // 1. 构造正文 URL 并请求
        val analyzeUrl = AnalyzeUrl(
            chapterUrl,
            baseUrl = book.bookUrl,
            source = source,
            ruleData = book,
            chapter = mockChapter
        )
        // 修复 GAP-67a: 执行请求并检测 loginCheckJs
        val response = executeRequest(
            analyzeUrl, "content",
            jsStr = bookSource.getContentRule().webJs,
            sourceRegex = bookSource.getContentRule().sourceRegex
        )
        // 修复 GAP-67e: 检测重定向
        checkRedirect(response)

        if (response.code() != 200) {
            logger.error(
                msg = "正文页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                failedStage = "content"
            )
            return DebugResult(
                success = false,
                errorStage = "content",
                errorMessage = "正文页请求失败: HTTP ${response.code()}"
            )
        }

        val html = response.body ?: ""
        logger.log("≡获取成功:${response.url}", state = 40, html = html)
        logger.separator()

        // 2. 解析正文
        val analyzeRule = AnalyzeRule(book, source = source)
        analyzeRule.setChapter(mockChapter)
        analyzeRule.setNextChapterUrl(nextChapterUrl)  // 差距1: 传递 nextChapterUrl（与真机 BookContent.kt 第230行一致）
        // 修复 GAP-67d: 设置重定向URL，用于后续 formatKeepImg 图片URL补全（对齐真机 BookContent.kt 第229行）
        val rUrl = analyzeRule.setRedirectUrl(response.url)
        analyzeRule.setContent(html, response.url)

        val contentRule = bookSource.getContentRule().content
        if (contentRule.isNullOrBlank()) {
            logger.error(msg = "正文规则 content 为空", failedStage = "content")
            return DebugResult(success = false, errorStage = "content", errorMessage = "正文规则 content 为空")
        }

        // 3. 获取正文内容（含 nextContentUrl 分页）
        val contentBuilder = StringBuilder()
        var currentContent = analyzeRule.getString(contentRule)
        if (currentContent.isBlank()) {
            val analysis = HtmlStructureAnalyzer().analyze(html)
            logger.log("[HTML结构分析-正文页]\n$analysis", state = 40)
        }
        contentBuilder.append(currentContent)

        // nextContentUrl 分页
        val nextContentUrlRule = bookSource.getContentRule().nextContentUrl
        if (!nextContentUrlRule.isNullOrBlank()) {
            var currentPage = 0
            var currentUrl = analyzeRule.getString(nextContentUrlRule, isUrl = true)
            while (currentUrl.isNotBlank() && currentPage < MAX_CONTENT_PAGE) {
                // 修复9.3 GAP-24: 取消检查
                checkCancelled()
                currentPage++
                logger.log("⇒获取正文下一页:$currentUrl")

                val nextAnalyzeUrl = AnalyzeUrl(
                    currentUrl,
                    baseUrl = response.url,
                    source = source,
                    ruleData = book,
                    chapter = mockChapter
                )
                // 修复 GAP-67a: 执行请求并检测 loginCheckJs
                val nextResponse = executeRequest(nextAnalyzeUrl, "content")
                if (nextResponse.code() != 200) break

                val nextHtml = nextResponse.body ?: ""
                val nextAnalyzeRule = AnalyzeRule(book, source = source)
                nextAnalyzeRule.setChapter(mockChapter)
                nextAnalyzeRule.setContent(nextHtml, nextResponse.url)
                contentBuilder.append(nextAnalyzeRule.getString(contentRule))

                currentUrl = nextAnalyzeRule.getString(nextContentUrlRule, isUrl = true)
            }
        }

        var content = contentBuilder.toString()

        // 修复 GAP-67d: 移植完整正文格式化链（对齐真机 BookContent.kt 第235-251行）
        // 真机模式: 非音频/视频书籍应用 HtmlFormatter.formatKeepImg 内置净化格式化
        // 简化说明: 跳过 useHtmlMap 和 StringEscapeUtils.unescapeHtml4，仅保留 formatKeepImg；isAudio/isVideo 用 type 位判断 | 已知上限: 无 usehtml 占位符支持 | 升级路径: 补充 useHtmlMap 逻辑
        val isAudio = book.type and 0b100000 != 0  // audio(32)
        val isVideo = book.type and 0b100 != 0      // video(4)
        if (!isAudio && !isVideo) {
            content = HtmlFormatter.formatKeepImg(content, rUrl)
        }

        // 4. 应用 replaceRegex
        val replaceRegexRule = bookSource.getContentRule().replaceRegex
        if (!replaceRegexRule.isNullOrBlank()) {
            logger.log("┌应用 replaceRegex")
            try {
                content = analyzeRule.getString(replaceRegexRule, content)
                logger.log("└replaceRegex 应用完成")
            } catch (e: Exception) {
                logger.log("└replaceRegex 应用失败: ${e.message}")
            }
        }

        // 5. 输出结果
        logger.log("┌获取章节名称")
        logger.log("└${mockChapter.title}")
        logger.log("┌获取正文内容")
        val preview = content.take(500)
        logger.log("└\n$preview${if (content.length > 500) "\n...(共${content.length}字)" else ""}")
        logger.log("◇正文长度:${content.length}")
        logger.log("︽正文页解析完成")
        logger.separator()

        // 有效数据校验：正文长度为 0 视为失败
        val isValid = content.isNotEmpty()

        // 6. 输出最终结果
        val summary = JsonObject()
        summary.addProperty("searchCount", 1)
        summary.addProperty("bookName", book.name)
        summary.addProperty("author", book.author)
        summary.addProperty("tocCount", tocCount)
        summary.addProperty("contentLength", content.length)
        summary.addProperty("stages", "search→detail→toc→content")
        logger.result(success = isValid, summary = summary)
        return DebugResult(success = isValid, summary = summary)
    }

    // ==================== 辅助方法 ====================

    private fun isAbsUrl(url: String): Boolean {
        return url.startsWith("http://", true) || url.startsWith("https://", true)
    }
}
