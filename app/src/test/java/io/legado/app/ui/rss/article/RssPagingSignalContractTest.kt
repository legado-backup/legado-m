package io.legado.app.ui.rss.article

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅列表翻页**信号契约**回归测试（2026-10-01 缺陷①②）。
 *
 * 为什么用源码契约（而非行为测试）：本缺陷的根因是「**某个出口忘记发完成信号**」——
 * 这类结构性问题无法被既有单测捕获（前序 spec 红队第 5 轮曾**错误断言**该出口已全覆盖），
 * 只能把「唯一出口必经」这一不变式钉死在源码层。
 *
 * 两条断言缺一不可：
 * ① `loadMoreSuccess` 内 `loadFinallyLiveData.postValue` **恰 1 处**；
 * ② 该函数体**无提前 `return`**。
 * 只断言①会被「新增静默分支」绕过（计数不变、测试仍绿 = 假保险）；②才是「必经唯一出口」的保证。
 */
class RssPagingSignalContractTest {

    private val source: String by lazy {
        SourceFileProbe.sourceText("ui/rss/article/RssArticlesViewModel.kt")
    }

    @Test
    fun loadMoreSuccessHasExactlyOneCompletionSignalAndNoEarlyReturn() {
        val body = functionBody(source, "private fun loadMoreSuccess(")

        val posts = Regex("""loadFinallyLiveData\.postValue""").findAll(body).count()
        assertEquals(
            "loadMoreSuccess 必须恰有 1 处完成信号（0 处 = 漏发 ⇒ 在途闸永不复位；多处 = 出口分散易漂移）：实得 $posts",
            1, posts
        )

        assertFalse(
            "loadMoreSuccess 不得有提前 return（否则新增静默分支时 ① 的计数不变、测试仍绿 = 假保险）" +
                "：函数体应为「单出口」写法",
            Regex("""\breturn\b""").containsMatchIn(body)
        )
    }

    @Test
    fun loadMoreSyncsPageIndicator() {
        val body = functionBody(source, "fun loadMore(")
        assertTrue(
            "缺陷②：滑动翻页必须同步顶栏页码 chip（loadMore 内应有 pageLiveData.postValue）",
            body.contains("pageLiveData.postValue(page)")
        )
    }

    @Test
    fun loadMoreRevertsPageOnFailure() {
        val body = functionBody(source, "fun loadMore(")
        val revert = Regex("""page--""").findAll(body).count()
        assertTrue(
            "缺陷②：未发起请求与网络异常两条路径都必须回退页码（以免页码与实页漂移、重试跳页）：实得 $revert",
            revert >= 2
        )
    }

    /** 取「签名 → 配对右花括号」之间的函数体（注释已由 SourceFileProbe 剥离）。 */
    private fun functionBody(text: String, signature: String): String {
        val start = text.indexOf(signature)
        assertTrue("未找到函数签名：$signature", start >= 0)
        val open = text.indexOf('{', start)
        var depth = 0
        var i = open
        while (i < text.length) {
            when (text[i]) {
                '{' -> depth++
                '}' -> {
                    depth--
                    if (depth == 0) return text.substring(open + 1, i)
                }
            }
            i++
        }
        throw AssertionError("函数体括号不匹配：$signature")
    }
}