package io.legado.app.ui.rss.article

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 2026-09-27 用户真机报障回归：订阅文章列表的**读取上下文字段单一数据源**。
 *
 * 现象：**自由布局（`articleStyle=5`，View 渲染路径）**下打开视频文章后，播放器内
 * 「上滑下滑切上/下一个视频」与「传统式上一部下一部」**全部失效**（真机安装测试包复现）。
 *
 * 根因：`articlesState`（`articles` getter 的唯一来源）**此前只在 Compose 分支赋值**，
 * 样式 5 的 View 路径只 `adapter.setItems(...)` ⇒ `articles` **恒为空列表** ⇒
 * `readRss` 交给播放器的 `rssArticles` 为空 ⇒ 播放器侧 `size > 1` 的文章模式判定全为假。
 * （与 IF-02 是**两条不同的链路**：IF-02 是自动路由只有单篇上下文，本条是列表路径传空列表。）
 */
class RssArticlesReadContextTest {

    private fun fragment(): String =
        SourceFileProbe.sourceText("ui/rss/article/RssArticlesFragment.kt")
            .replace("\r\n", "\n")

    @Test
    fun articlesStateAssignedOnceBeforeRenderPathSplit() {
        val s = fragment()
        val assigns = Regex("""articlesState\.value\s*=\s*newList""").findAll(s).count()
        assertTrue("articlesState 只允许一处赋值（双写会再次漂移）：实得 $assigns", assigns == 1)
        val assignAt = s.indexOf("articlesState.value = newList")
        val splitAt = s.indexOf("if (useComposeList)", assignAt)
        assertTrue("未找到渲染路径分派点", splitAt > 0)
        assertTrue(
            "赋值必须在 `if (useComposeList)` **之前** —— 否则 View 路径（样式 5 自由布局）" +
                "`articles` 恒为空 ⇒ 播放器拿不到上下滑上下文",
            assignAt < splitAt
        )
    }

    @Test
    fun readRssTakesListFromSingleSource() {
        assertTrue(
            "readRss 的文章列表必须取自单一数据源 `articles`（不得各自另取 adapter/DB）",
            fragment().contains("val rssArticles = articles")
        )
    }
}