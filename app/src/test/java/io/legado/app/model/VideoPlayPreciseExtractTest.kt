package io.legado.app.model

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * REQ-10 / tasks 2.1：`ruleContent` 解析结果非视频 URL 时的**降级顺序**不变量。
 *
 * 原行为：直接进 R5 嗅探（WebView 渲染，秒级）。新行为：**先**零成本 `extractPrecise`
 * 在已取到的正文 HTML 里精确找直链，未命中才回落 R5 ⇒ 命中路径从「秒级」变「毫秒级」。
 *
 * 由于 `VideoPlay.startPlay` 依赖播放器/协程运行时，纯 JVM 无法驱动 ⇒ 以源码不变量锁定
 * **顺序**与**去重 key 不被破坏**（后者是 R5 嗅探的内存去重依据，改错会退化为重复嗅探）。
 */
class VideoPlayPreciseExtractTest {

    private val videoPlay by lazy {
        listOf(
            File("src/main/java/io/legado/app/model/VideoPlay.kt"),
            File("../app/src/main/java/io/legado/app/model/VideoPlay.kt"),
            File("app/src/main/java/io/legado/app/model/VideoPlay.kt")
        ).first { it.isFile }.readText()
    }

    @Test
    fun preciseExtractRunsBeforeR5SniffingInRuleContentFailureBranch() {
        val branchStart = videoPlay.indexOf("ruleContent返回非视频URL")
        assertTrue("未找到 ruleContent 失败分支", branchStart > 0)
        val preciseAt = videoPlay.indexOf("extractPrecise(content, rssArticle.link)", branchStart)
        val sniffAt = videoPlay.indexOf("extractWithWebView(", branchStart)
        assertTrue("分支内必须先调用 extractPrecise", preciseAt > branchStart)
        assertTrue("extractPrecise 必须在 R5 嗅探之前", preciseAt < sniffAt)
    }

    @Test
    fun preciseHitIsPreferredOverSniffing() {
        // 命中即取用（if 分支在 sniff 之前结束），未命中才走嗅探
        val branchStart = videoPlay.indexOf("ruleContent返回非视频URL")
        val hitBranch = videoPlay.indexOf("if (precise.isNotEmpty())", branchStart)
        val sniffAt = videoPlay.indexOf("extractWithWebView(", branchStart)
        assertTrue("命中判断须存在", hitBranch > branchStart)
        assertTrue("命中判断须在嗅探之前", hitBranch < sniffAt)
    }

    @Test
    fun r5DedupKeyIsUnchanged() {
        // R5 嗅探的内存去重 key = 完整 URL ⇒ 调用必须仍以 rssArticle.link 为 url 参数
        val branchStart = videoPlay.indexOf("ruleContent返回非视频URL")
        val sniffBlock = videoPlay.substring(branchStart, videoPlay.indexOf("videoUrl = mUrl", branchStart))
        assertTrue(
            "R5 嗅探去重 key（完整 URL）不得被改动",
            sniffBlock.contains("extractWithWebView(") && sniffBlock.contains("url = rssArticle.link")
        )
    }

    @Test
    fun existingRuleContentValidPathIsUntouched() {
        // 只增不换：URL 有效时仍直接使用 resolved（不引入额外提取/嗅探）
        val validAt = videoPlay.indexOf("if (isValidVideoContentUrl(resolved))")
        assertTrue("有效性判断仍须存在", validAt > 0)
        val nextLine = videoPlay.substring(validAt).lines().getOrNull(1)?.trim()
        assertEquals("有效 URL 分支须原样返回 resolved", "resolved", nextLine)
    }
}