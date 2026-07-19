package io.legado.app.help.book

import io.legado.app.constant.AppLog
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter

/**
 * EPUB 错误回退机制（EPUB-E-05，P2，用户价值 3.7）。
 *
 * 任务来源：docs/specs/forks-archive-borrow-implementation/design.md L897
 *
 * 核心能力：
 * - 章节解析失败时返回用户可见的提示 HTML（而非 null 或崩溃）
 * - 区分错误类型（IO/解析/资源缺失）给出不同提示
 * - 记录错误日志便于排查
 *
 * 简化说明：本项目保持极简，仅生成 HTML 提示，不弹 Toast/Dialog（避免阅读流程打断）
 * 已知上限：未实现错误统计上报与书籍级健康度评估
 * 升级路径：后续可扩展错误聚合、健康度评分、自动修复建议
 */
object EpubErrorFallbackHelper {

    /** 错误类型枚举 */
    enum class ErrorType {
        /** IO 异常（文件读取失败、PFD 失效等） */
        IO_ERROR,

        /** 解析异常（xhtml 格式错误、编码异常等） */
        PARSE_ERROR,

        /** 资源缺失（href 在 EPUB 中不存在） */
        RESOURCE_NOT_FOUND,

        /** 未知错误 */
        UNKNOWN
    }

    /**
     * 生成错误回退 HTML 内容。
     *
     * @param book 书籍实体
     * @param chapter 章节实体
     * @param errorType 错误类型
     * @param errorMessage 错误消息（可选，用于日志记录，不展示给用户）
     * @return 用户可见的 HTML 字符串（永远不会返回 null）
     */
    fun buildErrorHtml(
        book: Book,
        chapter: BookChapter,
        errorType: ErrorType,
        errorMessage: String? = null
    ): String {
        AppLog.put(
            "EpubErrorFallback: type=$errorType bookUrl=${book.bookUrl} chapterUrl=${chapter.url} msg=$errorMessage"
        )

        val titleText = when (errorType) {
            ErrorType.IO_ERROR -> "章节内容读取失败"
            ErrorType.PARSE_ERROR -> "章节内容解析失败"
            ErrorType.RESOURCE_NOT_FOUND -> "章节资源未找到"
            ErrorType.UNKNOWN -> "章节加载失败"
        }

        val detailText = when (errorType) {
            ErrorType.IO_ERROR -> "可能是文件被移动、删除或存储权限变更导致。请尝试重新导入书籍。"
            ErrorType.PARSE_ERROR -> "可能是 EPUB 文件格式不规范。请尝试跳过此章节或更换书籍版本。"
            ErrorType.RESOURCE_NOT_FOUND -> "EPUB 内缺少此章节对应的资源文件。请尝试跳过此章节。"
            ErrorType.UNKNOWN -> "发生未知错误。请尝试重新打开书籍或反馈给开发者。"
        }

        // 简单 HTML 结构，与阅读页 HtmlFormatter 兼容
        return buildString {
            append("<div style=\"padding:16px;margin:8px;border:1px solid #e0e0e0;border-radius:8px;background:#fafafa;\">")
            append("<h3 style=\"color:#d32f2f;margin:0 0 8px 0;font-size:16px;\">")
            append(titleText)
            append("</h3>")
            append("<p style=\"color:#616161;margin:0;font-size:14px;line-height:1.6;\">")
            append(detailText)
            append("</p>")
            append("<p style=\"color:#9e9e9e;margin:8px 0 0 0;font-size:12px;\">章节：")
            append(chapter.title.ifBlank { chapter.url })
            append("</p>")
            append("</div>")
        }
    }

    /**
     * 包装 EPUB 章节解析逻辑，捕获异常并返回错误回退 HTML。
     *
     * 用法（在 EpubFile.getContent 中）：
     * ```
     * return EpubErrorFallbackHelper.wrapContentParse(book, chapter) {
     *     // 原始解析逻辑
 *         parseChapterContent(chapter)
     * }
     * ```
     *
     * @param book 书籍实体
     * @param chapter 章节实体
     * @param block 实际解析逻辑（返回 HTML 字符串，失败时抛异常）
     * @return 解析成功的 HTML 或错误回退 HTML（永不返回 null）
     */
    inline fun wrapContentParse(
        book: Book,
        chapter: BookChapter,
        block: () -> String?
    ): String {
        return try {
            block() ?: buildErrorHtml(book, chapter, ErrorType.RESOURCE_NOT_FOUND, "parse returned null")
        } catch (e: Throwable) {
            val errorType = classifyError(e)
            buildErrorHtml(book, chapter, errorType, e.localizedMessage)
        }
    }

    /**
     * 根据异常类型分类错误。
     *
     * 简化说明：仅区分 IO/参数/未知三类，避免依赖 jsoup 内部异常类（不同版本可能不兼容）
     *
     * 注：public 是为 inline 函数 [wrapContentParse] 访问，非对外 API
     */
    fun classifyError(e: Throwable): ErrorType {
        return when (e) {
            is java.io.IOException -> ErrorType.IO_ERROR
            is IllegalArgumentException -> ErrorType.RESOURCE_NOT_FOUND
            else -> {
                // 通过异常类名关键字匹配解析类异常（兼容 jsoup 不同版本）
                val className = e.javaClass.name.lowercase()
                when {
                    className.contains("parse") || className.contains("validation") -> ErrorType.PARSE_ERROR
                    else -> ErrorType.UNKNOWN
                }
            }
        }
    }
}
