package io.legado.app.model.localBook

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.ParcelFileDescriptor
import android.text.TextUtils
import androidx.collection.LruCache
import io.legado.app.constant.AppLog
import io.legado.app.data.appDb
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.book.BookHelp
import io.legado.app.help.config.AppConfig
import io.legado.app.help.coroutine.Coroutine
import io.legado.app.utils.FileUtils
import io.legado.app.utils.HtmlFormatter
import io.legado.app.utils.encodeURI
import io.legado.app.utils.isXml
import io.legado.app.utils.printOnDebug
import kotlinx.coroutines.Dispatchers.IO
import kotlinx.coroutines.runBlocking
import me.ag2s.epublib.domain.EpubBook
import me.ag2s.epublib.domain.Resource
import me.ag2s.epublib.domain.TOCReference
import me.ag2s.epublib.epub.EpubReader
import me.ag2s.epublib.util.zip.AndroidZipFile
import org.jsoup.Jsoup
import org.jsoup.nodes.Element
import org.jsoup.parser.Parser
import org.jsoup.select.Elements
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.URI
import java.net.URLDecoder
import java.nio.charset.Charset

class EpubFile(var book: Book) {

    companion object : BaseLocalBookParse {
        private var eFile: EpubFile? = null

        @Synchronized
        private fun getEFile(book: Book): EpubFile {
            if (eFile == null || eFile?.book?.bookUrl != book.bookUrl) {
                eFile = EpubFile(book)
                //对于Epub文件默认不启用替换
                //io.legado.app.data.entities.Book getUseReplaceRule
                return eFile!!
            }
            eFile?.book = book
            return eFile!!
        }

        @Synchronized
        override fun getChapterList(book: Book): ArrayList<BookChapter> {
            return getEFile(book).getChapterList()
        }

        @Synchronized
        override fun getContent(book: Book, chapter: BookChapter): String? {
            // EPUB-E-05: 包装错误回退机制，解析失败时返回用户可见的提示 HTML 而非崩溃
            return io.legado.app.help.book.EpubErrorFallbackHelper.wrapContentParse(book, chapter) {
                getEFile(book).getContent(chapter)
            }
        }

        @Synchronized
        override fun getImage(
            book: Book,
            href: String
        ): InputStream? {
            return getEFile(book).getImage(href)
        }

        @Synchronized
        override fun upBookInfo(book: Book) {
            return getEFile(book).upBookInfo()
        }

        fun clear() {
            eFile = null
        }
    }

    private var mCharset: Charset = Charset.defaultCharset()

    /**
     * EPUB-B-03 图片尺寸缓存（P1）。
     *
     * 借鉴 Archive `imageDimensionsCache`：用 inJustDecodeBounds=true 解码图片获取尺寸（不分配像素内存），
     * 缓存到 LruCache 避免重复解码。用于阅读页图片布局预占位，避免图片加载完成后页面跳动。
     *
     * key=href, value=Pair(width, height)。
     */
    private val imageDimensionsCache = LruCache<String, Pair<Int, Int>>(32)

    /**
     * EPUB-E-04 章节内容相邻预加载缓存（P1）。
     *
     * 借鉴 Archive `chapterContentCache`：缓存最近 N 个章节的解析后内容（HTML 字符串），
     * 用户翻页到相邻章节时直接命中缓存，避免重复解析 xhtml。
     *
     * key=chapter.url（带 fragmentId 区分），value=解析后的 HTML 字符串。
     *
     * 与 Archive 差异：Archive 用磁盘缓存支持跨进程重启，本项目保持极简仅内存缓存。
     */
    private val chapterContentCache = LruCache<String, String>(5)

    /**
     *持有引用，避免被回收
     */
    private var fileDescriptor: ParcelFileDescriptor? = null
    private var epubBook: EpubBook? = null
        get() {
            if (field == null || fileDescriptor == null) {
                field = readEpub()
            }
            return field
        }
    private var epubBookContents: List<Resource>? = null
        get() {
            if (field == null || fileDescriptor == null) {
                field = epubBook?.contents
            }
            return field
        }
    /**
     * spine 优先索引（EPUB-B-01）。
     *
     * 借鉴 Archive `epubSpineContents`：优先用 `spineReferences` 构建章节资源索引，
     * 避免 `epubBookContents`（全资源遍历，含图片/CSS/字体等非内容资源）的性能开销。
     * spine 为空时回退到 `epubBook?.contents`，保证兼容性。
     *
     * 关联任务：EPUB-B-01（P0）getContent/parseFirstPage 使用此索引加速章节查找。
     */
    private var epubSpineContents: List<Resource>? = null
        get() {
            if (field == null || fileDescriptor == null) {
                val spineResources = epubBook?.spine?.spineReferences
                    ?.mapNotNull { it.resource }
                    ?.filter { it.href.isNotBlank() }
                    .orEmpty()
                field = spineResources.ifEmpty { epubBook?.contents.orEmpty() }
            }
            return field
        }

    init {
        upBookCover(true)
    }

    /**
     * 重写epub文件解析代码，直接读出压缩包文件生成Resources给epublib，这样的好处是可以逐一修改某些文件的格式错误
     */
    private fun readEpub(): EpubBook? {
        // EPUB-B-03: readEpub 性能日志（P1）
        val startTime = System.currentTimeMillis()
        return kotlin.runCatching {
            //ContentScheme拷贝到私有文件夹采用懒加载防止OOM
            //val zipFile = BookHelp.getEpubFile(book)
            BookHelp.getBookPFD(book)?.let {
                fileDescriptor = it
                val zipFile = AndroidZipFile(it, book.originName)
                EpubReader().readEpubLazy(zipFile, "utf-8")
            }


        }.onFailure {
            AppLog.put("读取Epub文件失败\n${it.localizedMessage}", it)
            it.printOnDebug()
        }.getOrThrow().also {
            AppLog.putDebug("EpubFile.readEpub cost=${System.currentTimeMillis() - startTime}ms")
        }
    }

    private fun getContent(chapter: BookChapter): String? {
        // EPUB-B-03: getContent 性能日志（P1）
        val startTime = System.currentTimeMillis()
        /*获取当前章节文本*/
        // EPUB-E-04: 命中相邻预加载缓存直接返回（避免重复解析 xhtml）
        chapterContentCache[chapter.url]?.let {
            AppLog.putDebug("EpubFile.getContent hit memory cache url=${chapter.url} cost=${System.currentTimeMillis() - startTime}ms")
            return it
        }
        // EPUB-E-03: 命中磁盘缓存直接返回（跨进程重启有效，避免重复解析 xhtml）
        io.legado.app.help.book.EpubPageCacheHelper.readCache(book, chapter)?.let { diskContent ->
            chapterContentCache.put(chapter.url, diskContent)
            AppLog.putDebug("EpubFile.getContent hit disk cache url=${chapter.url} cost=${System.currentTimeMillis() - startTime}ms")
            return diskContent
        }
        // EPUB-B-01: 优先用 spine 索引（仅章节资源），空时回退到 epubBookContents 保留原语义
        val contents = epubSpineContents?.takeIf { it.isNotEmpty() } ?: epubBookContents ?: return null
        val nextChapterFirstResourceHref = chapter.getVariable("nextUrl").substringBeforeLast("#")
        val currentChapterFirstResourceHref = chapter.url.substringBeforeLast("#")
        val isLastChapter = nextChapterFirstResourceHref.isBlank()
        val startFragmentId = chapter.startFragmentId
        val endFragmentId = chapter.endFragmentId
        val elements = Elements()
        var findChapterFirstSource = false
        val includeNextChapterResource = !endFragmentId.isNullOrBlank()
        /*一些书籍依靠href索引的resource会包含多个章节，需要依靠fragmentId来截取到当前章节的内容*/
        /*注:这里较大增加了内容加载的时间，所以首次获取内容后可存储到本地cache，减少重复加载*/
        for (res in contents) {
            if (!findChapterFirstSource) {
                if (currentChapterFirstResourceHref != res.href) continue
                findChapterFirstSource = true
                // 第一个xhtml文件
                elements.add(
                    getBody(res, startFragmentId, endFragmentId)
                )
                // 不是最后章节 且 已经遍历到下一章节的内容时停止
                if (!isLastChapter && res.href == nextChapterFirstResourceHref) break
                continue
            }
            if (nextChapterFirstResourceHref != res.href) {
                // 其余部分
                elements.add(getBody(res, null, null))
            } else {
                // 下一章节的第一个xhtml
                if (includeNextChapterResource) {
                    //有Fragment 则添加到上一章节
                    elements.add(getBody(res, null, endFragmentId))
                }
                break
            }
        }
        //title标签中的内容不需要显示在正文中，去除
        elements.select("title").remove()
        elements.select("[style*=display:none]").remove()
        elements.select("img[src=\"cover.jpeg\"]").forEachIndexed { i, it ->
            if (i > 0) it.remove()
        }
        elements.select("img").forEach {
            if (it.attributesSize() <= 1) {
                return@forEach
            }
            val src = it.attr("src")
            it.clearAttributes()
            it.attr("src", src)
        }
        val tag = Book.rubyTag
        if (book.getDelTag(tag)) {
            elements.select("rp, rt").remove()
        }
        val html = elements.outerHtml()
        val result = HtmlFormatter.formatKeepImg(html)
        // EPUB-E-04: 写入相邻预加载缓存（key=chapter.url，最近 5 章 LRU）
        chapterContentCache.put(chapter.url, result)
        // EPUB-E-03: 写入磁盘缓存（跨进程重启有效，避免重复解析 xhtml）
        io.legado.app.help.book.EpubPageCacheHelper.writeCache(book, chapter, result)
        AppLog.putDebug("EpubFile.getContent miss cache url=${chapter.url} cost=${System.currentTimeMillis() - startTime}ms")
        return result
    }

    private fun getBody(res: Resource, startFragmentId: String?, endFragmentId: String?): Element {
        /**
         * <image width="1038" height="670" xlink:href="..."/>
         * ...titlepage.xhtml
         * 大多数epub文件的封面页都会带有cover，可以一定程度上解决封面读取问题
         */
        if (res.href.contains("titlepage.xhtml") ||
            res.href.contains("cover")
        ) {
            return Jsoup.parseBodyFragment("<img src=\"cover.jpeg\" />")
        }

        // Jsoup可能会修复不规范的xhtml文件 解析处理后再获取
        var bodyElement = Jsoup.parse(String(res.data, mCharset)).body()
        bodyElement.children().run {
            select("script").remove()
            select("style").remove()
        }
        // 获取body对应的文本
        var bodyString = bodyElement.outerHtml()
        val originBodyString = bodyString
        /**
         * 某些xhtml文件 章节标题和内容不在一个节点或者不是兄弟节点
         * <div>
         *    <a class="mulu1>目录1</a>
         * </div>
         * <p>....</p>
         * <div>
         *    <a class="mulu2>目录2</a>
         * </div>
         * <p>....</p>
         * 先找到FragmentId对应的Element 然后直接截取之间的html
         */
        if (!startFragmentId.isNullOrBlank()) {
            bodyElement.getElementById(startFragmentId)?.outerHtml()?.let {
                val tagStart = it.substringBefore("\n")
                bodyString = tagStart + bodyString.substringAfter(tagStart)
            }
        }
        if (!endFragmentId.isNullOrBlank() && endFragmentId != startFragmentId) {
            bodyElement.getElementById(endFragmentId)?.outerHtml()?.let {
                val tagStart = it.substringBefore("\n")
                bodyString = bodyString.substringBefore(tagStart)
            }
        }
        //截取过再重新解析
        if (bodyString != originBodyString) {
            bodyElement = Jsoup.parse(bodyString).body()
        }
        /*选择去除正文中的H标签，部分书籍标题与阅读标题重复待优化*/
        val tag = Book.hTag
        if (book.getDelTag(tag)) {
            bodyElement.run {
                select("h1, h2, h3, h4, h5, h6").remove()
                //getElementsMatchingOwnText(chapter.title)?.remove()
            }
        }
        bodyElement.select("image").forEach {
            it.tagName("img", Parser.NamespaceHtml)
            it.attr("src", it.attr("xlink:href"))
        }
        bodyElement.select("img").forEach {
            val src = it.attr("src").trim().encodeURI()
            val href = res.href.encodeURI()
            val resolvedHref = URLDecoder.decode(URI(href).resolve(src).toString(), "UTF-8")
            it.attr("src", resolvedHref)
        }
        return bodyElement
    }

    private fun getImage(href: String): InputStream? {
        if (href == "cover.jpeg") return epubBook?.coverImage?.inputStream
        val abHref = URLDecoder.decode(href, "UTF-8")
        return epubBook?.resources?.getByHref(abHref)?.inputStream
    }

    /**
     * 获取字体资源流（EPUB-E-02）。
     *
     * 用于 [io.legado.app.help.book.EpubFontHelper] 提取 EPUB 内嵌字体。
     * 内部复用 [getImage] 逻辑，EPUB 中字体资源与图片资源都通过 resources.getByHref 获取。
     *
     * @param href 字体在 EPUB 中的 href
     * @return 字体输入流，失败返回 null
     */
    fun getFontStream(href: String): InputStream? = getImage(href)

    /**
     * 获取图片尺寸（EPUB-B-03）。
     *
     * 借鉴 Archive `getImageDimensions`：用 inJustDecodeBounds=true 解码图片获取尺寸（不分配像素内存），
     * 缓存到 [imageDimensionsCache] 避免重复解码。用于阅读页图片布局预占位，避免图片加载完成后页面跳动。
     *
     * @param href 图片在 EPUB 中的 href
     * @return Pair(width, height)，解码失败返回 null
     */
    fun getImageDimensions(href: String): Pair<Int, Int>? {
        imageDimensionsCache[href]?.let { return it }
        val stream = getImage(href) ?: return null
        val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        return kotlin.runCatching {
            BitmapFactory.decodeStream(stream, null, options)
            val dimen = Pair(options.outWidth, options.outHeight)
            if (options.outWidth > 0 && options.outHeight > 0) {
                imageDimensionsCache.put(href, dimen)
                dimen
            } else null
        }.onFailure {
            AppLog.put("EpubFile.getImageDimensions failed href=$href", it)
        }.getOrNull().also {
            stream.close()
        }
    }

    /**
     * 预加载相邻章节内容到缓存（EPUB-E-04）。
     *
     * 借鉴 Archive `chapterContentCache` 预加载策略：用户翻页到相邻章节时直接命中缓存，
     * 避免重复解析 xhtml。调用方传入相邻章节列表，内部用 Coroutine.async 异步预加载，
     * 不阻塞当前章节加载。
     *
     * 与 Archive 差异：Archive 用磁盘缓存支持跨进程重启，本项目保持极简仅内存缓存（[chapterContentCache]）。
     *
     * @param adjacentChapters 相邻章节列表（如上一章+下一章），跳过已缓存章节
     */
    fun preloadAdjacentChapters(adjacentChapters: List<BookChapter>) {
        val toPreload = adjacentChapters.filter { chapter ->
            chapterContentCache[chapter.url] == null
        }
        if (toPreload.isEmpty()) return
        Coroutine.async {
            toPreload.forEach { chapter ->
                kotlin.runCatching { getContent(chapter) }.onFailure {
                    AppLog.put("EpubFile.preloadAdjacentChapters failed url=${chapter.url}", it)
                }
            }
        }.onError {
            AppLog.put("EpubFile.preloadAdjacentChapters error", it)
        }
    }

    private fun upBookCover(fastCheck: Boolean = false) {
        try {
            epubBook?.let {
                if (book.coverUrl.isNullOrEmpty()) {
                    book.coverUrl = LocalBook.getCoverPath(book)
                }
                if (fastCheck && File(book.coverUrl!!).exists()) {
                    return
                }
                /*部分书籍DRM处理后，封面获取异常，待优化*/
                it.coverImage?.inputStream?.use { input ->
                    val cover = BitmapFactory.decodeStream(input)
                    val out = FileOutputStream(FileUtils.createFileIfNotExist(book.coverUrl!!))
                    cover.compress(Bitmap.CompressFormat.JPEG, 90, out)
                    out.flush()
                    out.close()
                } ?: AppLog.putDebug("Epub: 封面获取为空. path: ${book.bookUrl}")
            }
        } catch (e: Exception) {
            AppLog.put("加载书籍封面失败\n${e.localizedMessage}", e)
            e.printOnDebug()
        }
    }

    private fun upBookInfo() {
        if (epubBook == null) {
            eFile = null
            book.intro = "书籍导入异常"
        } else {
            upBookCover()
            val metadata = epubBook!!.metadata
            book.name = metadata.firstTitle
            if (book.name.isEmpty()) {
                book.name = book.originName.replace(".epub", "")
            }

            if (metadata.authors.isNotEmpty()) {
                val author =
                    metadata.authors[0].toString().replace("^, |, $".toRegex(), "")
                book.author = author
            }
            if (metadata.descriptions.isNotEmpty()) {
                val desc = metadata.descriptions[0]
                book.intro = if (desc.isXml()) {
                    Jsoup.parse(metadata.descriptions[0]).text()
                } else {
                    desc
                }
            }
        }
    }

    private fun getChapterList(): ArrayList<BookChapter> {
        // EPUB-B-03: getChapterList 性能日志（P1）
        val startTime = System.currentTimeMillis()
        val chapterList = ArrayList<BookChapter>()
        epubBook?.let { eBook ->
            val refs = eBook.tableOfContents.tocReferences
            if (refs == null || refs.isEmpty()) {
                AppLog.putDebug("Epub: NCX file parse error, check the file: ${book.bookUrl}")
                val spineReferences = eBook.spine.spineReferences
                var i = 0
                val size = spineReferences.size
                while (i < size) {
                    val resource = spineReferences[i].resource
                    var title = resource.title
                    if (TextUtils.isEmpty(title)) {
                        try {
                            val doc =
                                Jsoup.parse(String(resource.data, mCharset))
                            val elements = doc.getElementsByTag("title")
                            if (elements.isNotEmpty()) {
                                title = elements[0].text()
                            }
                        } catch (e: IOException) {
                            AppLog.put("EpubFile: parse", e)
                        }
                    }
                    val chapter = BookChapter()
                    chapter.index = i
                    chapter.bookUrl = book.bookUrl
                    chapter.url = resource.href
                    // EPUB-B-02: 标题归一化（清理后为空则走"封面"分支，比原 title.isEmpty() 更严格）
                    val cleanedTitle = title.cleanEpubChapterTitle()
                    if (i == 0 && cleanedTitle.isEmpty()) {
                        chapter.title = "封面"
                    } else {
                        chapter.title = cleanedTitle
                    }
                    chapterList.lastOrNull()?.putVariable("nextUrl", chapter.url)
                    chapterList.add(chapter)
                    i++
                }
            } else {
                parseFirstPage(chapterList, refs)
                parseMenu(chapterList, refs, 0)
                for (i in chapterList.indices) {
                    chapterList[i].index = i
                }
            }
        }
        getWordCount(chapterList, book)
        AppLog.putDebug("EpubFile.getChapterList cost=${System.currentTimeMillis() - startTime}ms size=${chapterList.size}")
        return chapterList
    }

    /*获取书籍起始页内容。部分书籍第一章之前存在封面，引言，扉页等内容*/
    /*tile获取不同书籍风格杂乱，格式化处理待优化*/
    private var durIndex = 0
    private fun parseFirstPage(
        chapterList: ArrayList<BookChapter>,
        refs: List<TOCReference>?
    ) {
        // EPUB-B-01: 优先用 spine 索引（仅章节资源），避免全资源遍历
        val contents = epubSpineContents
        if (contents.isNullOrEmpty() || refs == null) return
        val firstRef = refs.firstOrNull { it.resource != null } ?: return
        var i = 0
        durIndex = 0
        while (i < contents.size) {
            val content = contents[i]
            // EPUB-B-02: 用 isReadableEpubResource 统一过滤非内容资源（图片/CSS/字体等）
            if (!content.isReadableEpubResource()) {
                i++
                continue
            }
            /**
             * 检索到第一章href停止
             * completeHref可能有fragment(#id) 必须去除
             * fix https://github.com/gedoor/legado/issues/1932
             */
            if (firstRef.completeHref.substringBeforeLast("#") == content.href) break
            val chapter = BookChapter()
            var title = content.title
            if (TextUtils.isEmpty(title)) {
                val elements = Jsoup.parse(
                    String(epubBook!!.resources.getByHref(content.href).data, mCharset)
                ).getElementsByTag("title")
                title =
                    if (elements.isNotEmpty() && elements[0].text().isNotBlank())
                        elements[0].text()
                    else
                        "--卷首--"
            }
            chapter.bookUrl = book.bookUrl
            chapter.title = title.cleanEpubChapterTitle()
            chapter.url = content.href
            chapter.startFragmentId =
                if (content.href.substringAfter("#") == content.href) null
                else content.href.substringAfter("#")

            chapterList.lastOrNull()?.endFragmentId = chapter.startFragmentId
            chapterList.lastOrNull()?.putVariable("nextUrl", chapter.url)
            chapterList.add(chapter)
            durIndex++
            i++
        }
    }

    private fun parseMenu(
        chapterList: ArrayList<BookChapter>,
        refs: List<TOCReference>?,
        level: Int
    ) {
        refs?.forEach { ref ->
            if (ref.resource != null) {
                val chapter = BookChapter()
                chapter.bookUrl = book.bookUrl
                chapter.title = ref.title.cleanEpubChapterTitle()
                chapter.url = ref.completeHref
                chapter.startFragmentId = ref.fragmentId
                chapterList.lastOrNull()?.endFragmentId = chapter.startFragmentId
                chapterList.lastOrNull()?.putVariable("nextUrl", chapter.url)
                chapterList.add(chapter)
                durIndex++
            }
            if (ref.children != null && ref.children.isNotEmpty()) {
                chapterList.lastOrNull()?.isVolume = true
                parseMenu(chapterList, ref.children, level + 1)
            }
        }
    }

    /**
     * 判断资源是否为可读内容资源（EPUB-B-02）。
     *
     * 借鉴 Archive `Resource.isReadableEpubResource`：过滤非内容资源（图片/CSS/字体等），
     * 只保留 html/xhtml/htm 资源。用于 parseFirstPage 遍历时跳过非内容资源。
     *
     * 关联任务：EPUB-B-02（P0）1.10.1 非内容资源过滤。
     */
    private fun Resource.isReadableEpubResource(): Boolean {
        val lowerHref = href.lowercase()
        if (!mediaType.toString().contains("htm") &&
            !lowerHref.endsWith(".html") &&
            !lowerHref.endsWith(".xhtml") &&
            !lowerHref.endsWith(".htm")
        ) {
            return false
        }
        return true
    }

    /**
     * 章节标题归一化（EPUB-B-02）。
     *
     * 借鉴 Archive `cleanEpubChapterTitle` 精简版：
     * - 去除 HTML 标签（防止 title 标签内容带标签）
     * - 合并多余空白为单个空格
     * - 去除常见前缀/后缀符号（-、—、–、_、空格、全角空格）
     * - 清理后为空则保留原始 title（避免覆盖默认值如"封面"/"--卷首--"）
     *
     * 关联任务：EPUB-B-02（P0）1.10.2 标题归一化。
     */
    private fun String?.cleanEpubChapterTitle(): String {
        if (isNullOrBlank()) return this.orEmpty()
        val cleaned = this
            .replace(Regex("<[^>]+>"), "")      // 去除 HTML 标签
            .replace(Regex("\\s+"), " ")         // 合并多余空白
            .trim('-', '—', '–', '_', ' ', '　') // 去除常见前缀/后缀符号
            .trim()
        return cleaned.ifBlank { this } // 清理后为空则保留原始 title
    }


    protected fun finalize() {
        fileDescriptor?.close()
    }

    private fun getWordCount(list: ArrayList<BookChapter>, book: Book) {
        if (!AppConfig.tocCountWords) {
            return
        }
        val chapterList = runBlocking(IO) { appDb.bookChapterDao.getChapterList(book.bookUrl) }
        if (chapterList.isNotEmpty()) {
            val map = chapterList.associateBy({ it.getFileName() }, { it.wordCount })
            for (bookChapter in list) {
                val wordCount = map[bookChapter.getFileName()]
                if (wordCount != null) {
                    bookChapter.wordCount = wordCount
                }
            }
        }
    }

}
