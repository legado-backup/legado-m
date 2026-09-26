package io.legado.app.model

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R 批 Q5/Q8（2026-09-26）正文/进度链路的**结构不变量**测试。
 *
 * Q8：`ReadBook.markRecentRead` 原先 `book.durChapterTime = now; book.update()` —— `Book.update()`
 *   是 `@Update` **整行写**，会用内存快照回写全部列，把并发协程期间改过的其它列静默覆盖回去
 *   （lost update），且每次「最近在读」打点都要写 30+ 列。修法 = 走 `bookDao.updateReadTime` 单列写。
 *
 * Q5：`CacheBook.downloadAwait` 失败时把「获取正文失败\n…」当**返回值**（错误文案即正文）⇒ 调用方
 *   只能靠字符串前缀猜失败（`LibraryCloudSync.canUpload` 正在嗅探），错误文案还会继续走展示/缓存/
 *   云上传链路。修法 = 新增 `failOnError`，`true` 时以异常表达失败；阅读器 await 路径改用 `true`，
 *   由外层既有 `catch (e: Exception) → showCurrentChapterLoadError` 呈现错误页。
 */
class BookProgressStampAwaitFailTest {

    private fun readBook(): String = SourceFileProbe.sourceText("model/ReadBook.kt")
    private fun cacheBook(): String = SourceFileProbe.sourceText("model/CacheBook.kt")

    /** 取函数体片段（从签名到下一个同缩进的 `fun ` 或文件尾），用于「函数内不得出现 X」类断言。 */
    private fun bodyOf(src: String, signature: String): String {
        val start = src.indexOf(signature)
        assertTrue("未找到函数：$signature", start >= 0)
        val rest = src.substring(start + signature.length)
        var idx = rest.indexOf("\n    fun ")
        if (idx < 0) idx = rest.indexOf("\n    private fun ")
        if (idx < 0) idx = rest.indexOf("\n    suspend fun ")
        return if (idx < 0) rest else rest.substring(0, idx)
    }

    @Test
    fun markRecentReadUsesSingleColumnStamp() {
        val src = readBook()
        val body = bodyOf(src, "fun markRecentRead(book: Book, readTime: Long = System.currentTimeMillis())")
        assertTrue("必须走单列写 updateReadTime", body.contains("appDb.bookDao.updateReadTime(book.bookUrl, readTime)"))
        assertFalse(
            "不得回退整行写 book.update()（会覆盖并发协程改过的其它列）",
            body.contains("book.update()")
        )
        assertTrue("最近在读记录仍须写入", body.contains("appDb.readRecentBookDao.insert(ReadRecentBook(book.bookUrl, readTime))"))
    }

    @Test
    fun cacheBookDownloadAwaitSupportsFailOnError() {
        val s = cacheBook()
        assertTrue(
            "downloadAwait 必须有 failOnError 形参（默认 false ⇒ 既有调用点零改动）",
            s.contains("suspend fun downloadAwait(chapter: BookChapter, failOnError: Boolean = false): String")
        )
        assertTrue("failOnError=true 必须以异常表达失败", s.contains("if (failOnError) throw e"))
        assertTrue(
            "默认形态仍须返回错误文案（向后兼容既有调用点）",
            s.contains("return \"获取正文失败\\n\${e.localizedMessage}\"")
        )
        assertTrue("取消不得被吞（CancellationException 仍走 onCancel）", s.contains("if (e is CancellationException)"))
    }

    @Test
    fun readBookAwaitThreadsFlagAndThrowsOnAllFailureBranches() {
        val src = readBook()
        val body = bodyOf(src, "private suspend fun downloadAwait(")
        assertTrue("必须把开关透传到 CacheBook", body.contains("downloadAwait(chapter, failOnError)"))
        assertTrue("书籍切换分支须抛异常", body.contains("if (failOnError) throw NoStackTraceException(\"Load content canceled: book changed\")"))
        assertTrue("无书源分支须抛异常", body.contains("if (failOnError) throw NoStackTraceException(msg)"))
        assertTrue(
            "阅读器 await 路径必须使用 failOnError = true（失败走错误页而非把错误文案当正文）",
            src.contains("?: downloadAwait(book, chapter, failOnError = true)")
        )
    }
}