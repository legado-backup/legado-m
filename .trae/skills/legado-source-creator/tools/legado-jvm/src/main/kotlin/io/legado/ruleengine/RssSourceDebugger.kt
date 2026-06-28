package io.legado.ruleengine

import com.google.gson.JsonObject
import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.data.entities.RssArticle
import io.legado.app.data.entities.RssSource
import io.legado.app.help.http.StrResponse
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.model.analyzeRule.AnalyzeUrl
import io.legado.app.model.analyzeRule.RuleData

/**
 * 端到端订阅源调试器
 * 原始文件: io.legado.app.model.Debug (rssContentDebug)
 *
 * 调试链路: sort → content
 * - singleUrl 模式: 直接调试内容
 * - 普通模式: 获取文章列表 → 调试第一篇内容
 *
 * 内联实现 RSS 执行流程:
 * 1. sortUrl 解析（支持 `分类名::URL` 格式 + `@js:` 规则）
 * 2. AnalyzeUrl 构造请求
 * 3. AnalyzeUrl.getStrResponse() 获取响应
 * 4. AnalyzeRule.getElements() 解析文章列表
 * 5. AnalyzeRule.getString() 解析正文
 *
 * 三层 evalJS 注入变量差异（由抽取后的类自动处理）:
 * - BaseSource 层: sortUrl @js（通过 AnalyzeUrl.evalJS 执行，注入 java/baseUrl/cookie/cache/source）
 * - AnalyzeUrl 层: URL 中的 @js/<js>/{{js}}（AnalyzeUrl.evalJS，注入 java/baseUrl/cookie/cache/page/key/source）
 * - AnalyzeRule 层: 规则中的 @js/<js>/{{js}}（AnalyzeRule.evalJS，注入 java/cookie/cache/source/book/result/baseUrl/rssArticle）
 *
 * 简化说明: 从旧 MVP4 迁移，替换 MockSource/MinimalMockJsExtensions 为抽取后的 RssSource/AnalyzeRule/AnalyzeUrl | 已知上限: sortUrl JS 执行用 AnalyzeUrl 层变量（非 BaseSource 层），可能缺少 source 变量 | 升级路径: 抽取 BaseSource.evalJS
 */
class RssSourceDebugger(
    private val sourceJson: String,
    private val key: String,
    private val logger: DebugLogger
) {
    private val rssSource: RssSource = parseRssSource(sourceJson) ?: RssSource(sourceUrl = "unknown")
    private val source: BaseSourceInterface = wrapSource(rssSource)

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

    /**
     * 修复 GAP-67a: 执行请求并检测 loginCheckJs（对齐真机 Rss.getArticlesAwait 第53-77行）
     * 真机模式: getStrResponse → evalJS(checkJs, response) → 若 code==500 表示需要登录
     * 异常模式: getStrResponse 失败 → getErrStrResponse → evalJS(checkJs, errResponse) → 若 code==500 抛出原异常
     * 简化说明: 仿真端 evalJS 返回 StrResponse 时检测 code==500 抛 UserInterventionException | 已知上限: 无登录UI交互 | 升级路径: 接入登录流程
     */
    private fun executeRequest(
        analyzeUrl: AnalyzeUrl,
        stage: String,
        useWebView: Boolean = false
    ): StrResponse {
        val checkJs = rssSource.loginCheckJs
        // 修复 GAP-67a: 异常时尝试 loginCheckJs 检测（对齐真机 runCatching getOrElse 逻辑）
        val response = try {
            analyzeUrl.getStrResponse(useWebView = useWebView)
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
     * 修复 GAP-67e: 检测重定向（对齐真机 Rss.checkRedirect 第147-155行）
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

    // RssSource 规则字段
    private val ruleArticles: String? get() = rssSource.ruleArticles?.ifBlank { null }
    private val ruleDescription: String? get() = rssSource.ruleDescription?.ifBlank { null }
    private val ruleNextPage: String? get() = rssSource.ruleNextPage?.ifBlank { null }
    private val ruleContent: String? get() = extractJsRule(rssSource.ruleContent?.ifBlank { null })
    private val ruleTitle: String? get() = rssSource.ruleTitle?.ifBlank { null }
    private val ruleLink: String? get() = rssSource.ruleLink?.ifBlank { null }
    private val rulePubDate: String? get() = rssSource.rulePubDate?.ifBlank { null }
    private val ruleImage: String? get() = rssSource.ruleImage?.ifBlank { null }
    private val singleUrl: Boolean get() = rssSource.singleUrl

    companion object {
        private const val MAX_SORT_PAGE = 50

        /**
         * 从 ruleContent 中提取 JS 规则（保留 <js></js> 标签）
         * 简化说明: JS规则后的HTML模板会被getString当作CSS选择器解析导致异常，只保留JS部分 | 已知上限: 丢失HTML模板 | 升级路径: 在AnalyzeRule中修复splitSourceRule，JS执行后跳过后续规则
         */
        private fun extractJsRule(rule: String?): String? {
            if (rule.isNullOrBlank()) return rule
            val jsPattern = Regex("<js>([\\s\\S]*?)</js>", RegexOption.IGNORE_CASE)
            val match = jsPattern.find(rule)
            return if (match != null) {
                match.value  // 保留 <js></js> 标签
            } else {
                rule
            }
        }
    }

    /**
     * 调试入口 - 根据 key 格式分发
     * - isAbsUrl → 内容页调试
     * - singleUrl=true → 直接调试内容
     * - else → 列表页调试（完整链路）
     *
     * 修复9.4 GAP-25: 添加 validateMode 参数，校验模式下只检查规则是否存在，不执行请求
     * 修复9.5 GAP-26: 处理 key 为空的情况，使用第一个 sortUrl 条目
     *
     * @param validateMode true 时只校验规则是否存在，不执行完整调试
     */
    fun debug(validateMode: Boolean = false): DebugResult {
        return try {
            if (validateMode) {
                return validateRules()
            }
            when {
                // 修复9.5 GAP-26: 无参key入口，使用第一个 sortUrl 条目
                key.isBlank() -> debugSortWithEmptyKey()
                isAbsUrl(key) -> {
                    // 对齐真机 Debug.kt:155-171 的 ruleDescription 判断逻辑
                    if (!ruleArticles.isNullOrBlank() && ruleDescription.isNullOrBlank()) {
                        if (ruleContent.isNullOrBlank()) {
                            logger.log("⇒内容规则为空，默认获取整个网页")
                            val summary = JsonObject().apply {
                                addProperty("stages", "sort")
                                addProperty("result", "skipped_content")
                            }
                            logger.result(success = true, summary = summary)
                            DebugResult(success = true, summary = summary)
                        } else {
                            debugContent(key)
                        }
                    } else {
                        logger.log("⇒存在描述规则，不解析内容页")
                        logger.log("︽解析完成")
                        val summary = JsonObject().apply {
                            addProperty("stages", "sort")
                            addProperty("result", "skipped_content")
                        }
                        logger.result(success = true, summary = summary)
                        DebugResult(success = true, summary = summary)
                    }
                }
                singleUrl -> debugSingleUrl()
                else -> debugSort()
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

        // 必填: sourceUrl
        if (rssSource.sourceUrl.isNullOrBlank()) {
            missingRules.add("sourceUrl")
        }
        // 必填: ruleArticles（文章列表规则）
        if (ruleArticles.isNullOrBlank()) {
            missingRules.add("ruleArticles")
        }
        // 必填: searchUrl 或 sortUrl（至少有一个）
        val hasSearchUrl = !rssSource.searchUrl.isNullOrBlank() &&
            !rssSource.searchUrl!!.startsWith("@js:", ignoreCase = true) &&
            !rssSource.searchUrl!!.startsWith("<js>", ignoreCase = true)
        val hasSortUrl = !rssSource.sortUrl.isNullOrBlank()
        if (!hasSearchUrl && !hasSortUrl) {
            missingRules.add("searchUrl或sortUrl")
        }

        // 内容规则: ruleContent 或 ruleDescription 至少有一个
        if (ruleContent.isNullOrBlank() && ruleDescription.isNullOrBlank()) {
            logger.log("⚠️ ruleContent 和 ruleDescription 均为空，将默认获取整个网页")
        }

        // 可选规则校验（仅提示，不计入失败）
        if (ruleTitle.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: ruleTitle")
        if (ruleLink.isNullOrBlank()) logger.log("⚠️ 可选规则缺失: ruleLink")

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

    // ==================== 无参key入口（GAP-26） ====================

    /**
     * 修复9.5 GAP-26: 无参key入口
     * 真机 Debug.kt:111-140 startDebug(scope, rssSource) 无 key 参数，使用 sortUrls().first()
     * 仿真端使用 sortUrl 的第一个条目或 searchUrl 作为入口
     */
    private fun debugSortWithEmptyKey(): DebugResult {
        logger.log("⇒无参key模式，使用第一个分类入口")
        logger.separator()

        // 优先从 sortUrl 提取第一个条目
        val sortUrlRaw = rssSource.sortUrl
        val effectiveSortUrl = if (sortUrlRaw != null && (sortUrlRaw.startsWith("@js:", ignoreCase = true) ||
                sortUrlRaw.startsWith("<js>", ignoreCase = true))) {
            executeSortUrlJs(sortUrlRaw)
        } else {
            sortUrlRaw
        }

        var firstUrl: String? = null
        var firstName: String = ""
        if (!effectiveSortUrl.isNullOrBlank()) {
            val sortEntries = effectiveSortUrl!!.split("(&&|\n)+".toRegex())
            for (entry in sortEntries) {
                val name = entry.substringBefore("::").trim()
                val url = entry.substringAfter("::", "").trim()
                if (url.isNotEmpty()) {
                    firstName = name
                    firstUrl = url
                    break
                }
            }
        }

        // 降级到 searchUrl
        if (firstUrl.isNullOrBlank()) {
            val searchUrl = rssSource.searchUrl
            if (searchUrl != null && !searchUrl.startsWith("@js:", ignoreCase = true) &&
                !searchUrl.startsWith("<js>", ignoreCase = true)) {
                firstUrl = searchUrl
                firstName = "搜索"
            }
        }

        // 降级到 sourceUrl
        if (firstUrl.isNullOrBlank()) {
            firstUrl = rssSource.sourceUrl
            firstName = "默认"
        }

        if (firstUrl.isNullOrBlank()) {
            logger.error(msg = "无参key模式下无可用URL", failedStage = "sort")
            return DebugResult(success = false, errorStage = "sort", errorMessage = "无参key模式下无可用URL")
        }

        logger.log("⇒使用分类: $firstName")
        logger.log("⇒使用URL: $firstUrl")

        // 复用 debugSort 逻辑，通过临时构造一个带URL的调试
        // 简化说明: 直接调用 debugContent 或 debugSingleUrl，根据 singleUrl 标志 | 已知上限: 跳过列表页解析 | 升级路径: 重构 debugSort 支持外部传入URL
        return if (singleUrl) {
            debugSingleUrl()
        } else {
            // 模拟真机 startDebug(scope, rssSource) 行为：直接获取文章列表
            debugContent(firstUrl)
        }
    }

    // ==================== 列表阶段 ====================

    private fun debugSort(): DebugResult {
        logger.log("⇒开始获取订阅源列表")
        logger.log("︾开始解析列表页")
        logger.separator()

        // 从 sortUrl 中根据 key 提取 URL
        // sortUrl 格式: "分类名::URL\n分类名2::URL2" 或 "@js:JS代码" 或 "<js>JS代码</js>"
        val sortUrlRaw = rssSource.sortUrl
        // searchUrl 如果是 @js:/<js> 规则，不能直接当 URL 用，需走 sortUrl 解析
        var searchUrl: String? = rssSource.searchUrl
        if (searchUrl != null && (searchUrl.startsWith("@js:", ignoreCase = true) ||
                searchUrl.startsWith("<js>", ignoreCase = true))) {
            searchUrl = null
        }
        // 降级：searchUrl 为空时使用 sourceUrl（修复美图公社/吞金影院/源仓库等源只有 sourceUrl 的问题）
        if (searchUrl.isNullOrBlank()) {
            searchUrl = rssSource.sourceUrl
        }

        // 处理 @js: 和 <js> 格式的 sortUrl（JS 动态生成分类列表）
        val effectiveSortUrl = if (sortUrlRaw != null && (sortUrlRaw.startsWith("@js:", ignoreCase = true) ||
                sortUrlRaw.startsWith("<js>", ignoreCase = true))) {
            executeSortUrlJs(sortUrlRaw)
        } else {
            sortUrlRaw
        }

        // 先从 sortUrl 中查找 key 对应的 URL（优先级最高）
        var resolvedUrl: String? = null
        if (!effectiveSortUrl.isNullOrBlank()) {
            val sortEntries = effectiveSortUrl!!.split("(&&|\n)+".toRegex())
            for (entry in sortEntries) {
                val name = entry.substringBefore("::").trim()
                val url = entry.substringAfter("::", "").trim()
                if (url.isNotEmpty() && name == key.trim()) {
                    resolvedUrl = url
                    break
                }
            }
            // 如果没找到匹配的key，用第一个条目的URL
            if (resolvedUrl.isNullOrBlank() && sortEntries.isNotEmpty()) {
                val firstUrl = sortEntries[0].substringAfter("::", "").trim()
                if (firstUrl.isNotEmpty()) {
                    logger.log("⚠️ sortUrl中未找到匹配key '$key'，降级使用第一个条目URL")
                    resolvedUrl = firstUrl
                }
            }
        }

        // sortUrl 中找到 URL 时优先使用；否则降级到 searchUrl
        if (!resolvedUrl.isNullOrBlank()) {
            searchUrl = resolvedUrl
        }
        if (searchUrl.isNullOrBlank()) {
            logger.error(msg = "订阅源URL为空", failedStage = "sort")
            return DebugResult(success = false, errorStage = "sort", errorMessage = "订阅源URL为空")
        }

        var currentUrl: String = searchUrl
        // 相对URL自动拼接baseUrl（修复51cg/acgfta/mjv006等源的相对路径问题）
        currentUrl = toAbsoluteUrl(currentUrl, rssSource.sourceUrl)
        var page = 0
        val allArticles = mutableListOf<RssArticle>()
        // 修复 GAP-41: 列表阶段创建独立 RuleData()，避免共享 ruleData 导致并发冲突（对齐真机 Rss.getArticlesAwait）
        val rssRuleData = RuleData()

        // ruleNextPage 分页循环
        while (page < MAX_SORT_PAGE) {
            // 修复9.3 GAP-24: 取消检查
            checkCancelled()
            page++

            val analyzeUrl = AnalyzeUrl(
                currentUrl,
                key = if (page == 1) key else null,
                page = page,
                baseUrl = rssSource.sourceUrl,
                source = source,
                ruleData = rssRuleData
            )
            logger.log("⇒请求URL: ${analyzeUrl.url}", state = 1)
            // 诊断日志: RSS请求详情
            System.err.println("[DIAG] RSS请求: page=$page, url=${analyzeUrl.url}, key=$key")
            // 修复 GAP-67a: 执行请求并检测 loginCheckJs
            val response = executeRequest(analyzeUrl, "sort")
            // 修复 GAP-67e: 检测重定向
            checkRedirect(response)
            // 诊断日志: RSS响应详情
            System.err.println("[DIAG] RSS响应: code=${response.code()}, body长度=${response.body?.length ?: 0}")

            if (response.code() != 200) {
                logger.error(
                    msg = "列表页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                    failedStage = "sort"
                )
                return DebugResult(
                    success = false,
                    errorStage = "sort",
                    errorMessage = "列表页请求失败: HTTP ${response.code()}"
                )
            }

            val html = response.body ?: ""
            if (page == 1) {
                logger.log("≡获取成功:${response.url}", state = 10, html = html)
                logger.separator()
            }

            if (ruleArticles.isNullOrBlank()) {
                logger.error(msg = "文章列表规则 ruleArticles 为空", failedStage = "sort")
                return DebugResult(success = false, errorStage = "sort", errorMessage = "文章列表规则 ruleArticles 为空")
            }

            val analyzeRule = AnalyzeRule(source = source)
            analyzeRule.setContent(html, response.url)

            val articleList = analyzeRule.getElements(ruleArticles!!)
            if (page == 1) {
                logger.log("┌获取文章列表")
                logger.log("└本页文章数:${articleList.size}")
                // 诊断日志: RSS列表页解析详情
                System.err.println("[DIAG] RSS列表页 ruleArticles=$ruleArticles")
                System.err.println("[DIAG] RSS列表页 HTML长度=${html.length}, 文章数=${articleList.size}")
                System.err.println("[DIAG] RSS列表页 HTML前200字符=${html.take(200)}")
                if (articleList.isNotEmpty()) {
                    System.err.println("[DIAG] 第一文章类型=${articleList[0]?.javaClass?.name}, 值=${articleList[0]?.toString()?.take(100)}")
                }
            }

            if (articleList.isEmpty() && page == 1) {
                val analysis = HtmlStructureAnalyzer().analyze(html)
                logger.log("[HTML结构分析-列表页]\n$analysis", state = 10)
                logger.error(msg = "文章列表为空", failedStage = "sort")
                return DebugResult(success = false, errorStage = "sort", errorMessage = "文章列表为空")
            }

            // 提取文章字段
            for ((index, articleElement) in articleList.withIndex()) {
                analyzeRule.setContent(articleElement, response.url)

                val title = analyzeRule.getString(ruleTitle)
                val link = analyzeRule.getString(ruleLink, isUrl = true)
                val description = analyzeRule.getString(ruleDescription)
                val pubDate = analyzeRule.getString(rulePubDate)
                val image = analyzeRule.getString(ruleImage, isUrl = true)

                val article = RssArticle(
                    origin = rssSource.sourceUrl,
                    title = title,
                    link = link,
                    description = description,
                    pubDate = pubDate,
                    image = image
                )
                allArticles.add(article)

                // 首页前3篇输出详细日志
                if (page == 1 && index < 3) {
                    logger.log("┌获取标题[$index]")
                    logger.log("└$title")
                    logger.log("┌获取文章链接[$index]")
                    logger.log("└$link")
                    if (description.isNotEmpty()) {
                        logger.log("┌获取描述[$index]")
                        logger.log("└${description.take(100)}${if (description.length > 100) "..." else ""}")
                    }
                    if (pubDate.isNotEmpty()) {
                        logger.log("┌获取发布时间[$index]")
                        logger.log("└$pubDate")
                    }
                    if (image.isNotEmpty()) {
                        logger.log("┌获取图片[$index]")
                        logger.log("└$image")
                    }
                }
            }

            // 获取下一页
            if (ruleNextPage.isNullOrBlank()) break
            // 修复 GAP-67b: PAGE 模式下，下一页URL为原始searchUrl，由AnalyzeUrl的page参数处理翻页
            // 真机模式: RssParserByRule.kt 第58行 ruleNextPage.uppercase()=="PAGE" 时 nextUrl=sortUrl
            val nextPageRule = ruleNextPage!!  // 上面 isNullOrBlank break 保证非空
            val isPageMode = nextPageRule.uppercase() == "PAGE"
            val nextPageUrl = if (isPageMode) {
                searchUrl  // PAGE模式: 保持原始URL，由page参数递增
            } else {
                analyzeRule.getString(nextPageRule, isUrl = true)
            }
            if (isPageMode) {
                // PAGE模式: 空文章列表作为终止条件
                if (articleList.isEmpty()) break
            } else {
                if (nextPageUrl.isBlank() || nextPageUrl == currentUrl) break
            }
            currentUrl = nextPageUrl
        }

        logger.log("◇文章总数:${allArticles.size}")
        logger.log("︽列表页解析完成")
        logger.separator()

        // 继续内容阶段（对齐真机 Debug.kt:123-134 的 ruleDescription 判断逻辑）
        return if (allArticles.isNotEmpty()) {
            if (!ruleArticles.isNullOrBlank() && ruleDescription.isNullOrBlank()) {
                // ruleDescription 为空 → 解析内容页
                if (ruleContent.isNullOrBlank()) {
                    logger.log("⇒内容规则为空，默认获取整个网页")
                    val summary = JsonObject().apply {
                        addProperty("articleCount", allArticles.size)
                        addProperty("stages", "sort")
                        addProperty("result", "skipped_content")
                    }
                    logger.result(success = true, summary = summary)
                    DebugResult(success = true, summary = summary)
                } else {
                    debugContent(allArticles[0].link, allArticles[0])
                }
            } else {
                // ruleDescription 非空 → 不解析内容页
                logger.log("⇒存在描述规则，不解析内容页")
                logger.log("︽解析完成")
                val summary = JsonObject().apply {
                    addProperty("articleCount", allArticles.size)
                    addProperty("stages", "sort")
                    addProperty("result", "skipped_content")
                }
                logger.result(success = true, summary = summary)
                DebugResult(success = true, summary = summary)
            }
        } else {
            logger.error(msg = "无可用文章，无法调试内容", failedStage = "sort")
            DebugResult(success = false, errorStage = "sort", errorMessage = "无可用文章，无法调试内容")
        }
    }

    // ==================== 内容阶段 ====================

    private fun debugContent(articleUrl: String, article: RssArticle? = null): DebugResult {
        logger.log("⇒开始访问文章内容页:$articleUrl")
        logger.log("︾开始解析正文页")
        logger.separator()

        // 相对URL自动拼接baseUrl（与 debugSort 一致）
        val contentUrl = toAbsoluteUrl(articleUrl, rssSource.sourceUrl)

        // 使用 RssArticle 作为 ruleData（实现 RuleDataInterface）
        val rssArticle = article ?: RssArticle(origin = rssSource.sourceUrl, link = articleUrl)

        // 修复 GAP-41: 内容阶段 AnalyzeUrl 注入 rssArticle 作为 ruleData（对齐真机 Rss.getContentAwait）
        val analyzeUrl = AnalyzeUrl(
            contentUrl,
            baseUrl = rssSource.sourceUrl,
            source = source,
            ruleData = rssArticle
        )
        // 修复 GAP-67a: 执行请求并检测 loginCheckJs
        val response = executeRequest(analyzeUrl, "content")
        // 修复 GAP-67e: 检测重定向
        checkRedirect(response)

        if (response.code() != 200) {
            logger.error(
                msg = "内容页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                failedStage = "content"
            )
            return DebugResult(
                success = false,
                errorStage = "content",
                errorMessage = "内容页请求失败: HTTP ${response.code()}"
            )
        }

        val html = response.body ?: ""
        logger.log("≡获取成功:${response.url}", state = 40, html = html)
        logger.separator()

        val analyzeRule = AnalyzeRule(rssArticle, source = source)
        analyzeRule.setContent(html, response.url)

        // 获取内容
        val content = if (!ruleContent.isNullOrBlank()) {
            analyzeRule.getString(ruleContent)
        } else if (!ruleDescription.isNullOrBlank()) {
            analyzeRule.getString(ruleDescription)
        } else {
            logger.log("⚠️ 规则缺失: ruleContent 和 ruleDescription 均为空，回退到原始HTML")
            html
        }

        logger.log("┌获取正文内容")
        val preview = content.take(500)
        logger.log("└\n$preview${if (content.length > 500) "\n...(共${content.length}字)" else ""}")
        logger.log("◇正文长度:${content.length}")
        logger.log("︽正文页解析完成")
        logger.separator()

        // 有效数据校验：正文长度为 0 视为失败
        val isValid = content.isNotEmpty()

        // 输出结果
        val summary = JsonObject()
        summary.addProperty("articleCount", 1)
        summary.addProperty("contentLength", content.length)
        summary.addProperty("stages", "sort→content")
        logger.result(success = isValid, summary = summary)
        return DebugResult(success = isValid, summary = summary)
    }

    // ==================== 单URL模式 ====================

    private fun debugSingleUrl(): DebugResult {
        logger.log("⇒单URL模式，直接调试内容")
        logger.log("︾开始解析内容")
        logger.separator()

        val searchUrl = rssSource.sourceUrl
        if (searchUrl.isNullOrBlank()) {
            logger.error(msg = "订阅源URL为空", failedStage = "content")
            return DebugResult(success = false, errorStage = "content", errorMessage = "订阅源URL为空")
        }

        val analyzeUrl = AnalyzeUrl(
            searchUrl,
            baseUrl = rssSource.sourceUrl,
            source = source
        )
        // 修复 GAP-67a: 执行请求并检测 loginCheckJs
        val response = executeRequest(analyzeUrl, "content")
        // 修复 GAP-67e: 检测重定向
        checkRedirect(response)

        if (response.code() != 200) {
            logger.error(
                msg = "内容页请求失败: HTTP ${response.code()}, ${response.body ?: ""}",
                failedStage = "content"
            )
            return DebugResult(
                success = false,
                errorStage = "content",
                errorMessage = "内容页请求失败: HTTP ${response.code()}"
            )
        }

        val html = response.body ?: ""
        logger.log("≡获取成功:${response.url}", state = 40, html = html)
        logger.separator()

        val analyzeRule = AnalyzeRule(source = source)
        analyzeRule.setContent(html, response.url)

        val content = if (!ruleContent.isNullOrBlank()) {
            analyzeRule.getString(ruleContent)
        } else {
            html
        }

        logger.log("┌获取正文内容")
        val preview = content.take(500)
        logger.log("└\n$preview${if (content.length > 500) "\n...(共${content.length}字)" else ""}")
        logger.log("◇正文长度:${content.length}")
        logger.log("︽内容解析完成")
        logger.separator()

        // 有效数据校验：正文长度为 0 视为失败
        val isValid = content.isNotEmpty()

        val summary = JsonObject()
        summary.addProperty("contentLength", content.length)
        summary.addProperty("stages", "content")
        logger.result(success = isValid, summary = summary)
        return DebugResult(success = isValid, summary = summary)
    }

    // ==================== 辅助方法 ====================

    /**
     * 执行 @js: 或 <js>...</js> 格式的 sortUrl，返回解析后的分类列表字符串
     * 源码参照: app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L324-L343 (BaseSource.evalJS)
     * 修复内容: 改用 BaseSourceInterface.evalJS 执行，注入 source=rssSource，与真机一致
     * 简化说明: rssSource 是纯 data class，JS 中调用 source.getKey() 等方法会失败 | 已知上限: 仅支持属性访问 | 升级路径: 让 RssSource 实现 BaseSourceInterface
     */
    private fun executeSortUrlJs(sortUrl: String): String? {
        val jsStr = when {
            sortUrl.startsWith("@js:", ignoreCase = true) -> sortUrl.substring(4)
            sortUrl.startsWith("<js>", ignoreCase = true) -> {
                val endIdx = sortUrl.lastIndexOf("</js>", ignoreCase = true)
                if (endIdx > 4) sortUrl.substring(4, endIdx) else sortUrl.substring(4)
            }
            else -> return sortUrl
        }

        return try {
            // 修复: 改用 BaseSourceInterface.evalJS 执行，通过 bindingsConfig 注入 source=rssSource
            // 真机中 sortUrl JS 通过 BaseSource.evalJS 执行，bindings["source"] = this（指向 RssSource）
            // 仿真端 source 变量指向 rssSource（RssSource 数据对象），可访问 sortUrl/sourceUrl 等属性
            // java 变量指向 source（BaseSourceInterface 包装对象），可调用 JsExtensions 方法
            // baseUrl 变量指向 getKey()（即 sourceUrl），与真机一致
            val result = source.evalJS(jsStr) {
                this["source"] = rssSource
            }
            val resultStr = result?.toString() ?: ""
            if (resultStr.isNotBlank()) {
                logger.log("⇒sortUrl JS执行成功: ${resultStr.take(80)}...")
                resultStr
            } else {
                logger.error(msg = "sortUrl JS执行返回空结果", failedStage = "sort")
                null
            }
        } catch (e: Exception) {
            logger.error(
                msg = "sortUrl JS执行失败: ${e.message}",
                stackTrace = e.stackTraceToString(),
                failedStage = "sort"
            )
            null
        }
    }

    /**
     * 相对URL转绝对URL
     * 使用 NetworkUtilsStub.getAbsoluteURL（与真机行为一致）
     */
    private fun toAbsoluteUrl(url: String, baseUrl: String): String {
        if (url.startsWith("http", ignoreCase = true)) return url
        if (baseUrl.isBlank()) return url
        return io.legado.app.utils.NetworkUtilsStub.getAbsoluteURL(baseUrl, url)
    }

    private fun isAbsUrl(url: String): Boolean {
        return url.startsWith("http://", true) || url.startsWith("https://", true)
    }
}
