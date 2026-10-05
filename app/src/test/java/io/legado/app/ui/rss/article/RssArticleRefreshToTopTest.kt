package io.legado.app.ui.rss.article

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * add-rss-article-refresh-to-top 配对测试。
 *
 * 锁三件事：
 * ① [RssArticleRefreshScrollPolicy] 四条件判定的完整真值表（纯函数，直接钉死）；
 * ② 宿主 `RssArticlesFragment` 的置位/消费接线不变量（置位点唯一、消费在数据落定之后、
 *    旋转恢复优先且**先读后消费**、失败路径清零、View 路径回顶走同步整表替换分支）；
 * ③ 设置键经 `AppConfig` 消费（防「设置无效」的静默失联）。
 */
class RssArticleRefreshToTopTest {

    private fun fragment(): String = SourceFileProbe.sourceText("ui/rss/article/RssArticlesFragment.kt")

    // ------------------------------------------------------------------ 策略纯函数真值表

    @Test
    fun policyReturnsTrueOnlyWhenAllFourConditionsHold() {
        assertTrue(
            "开关开启 + 刷新意图在途 + 无待恢复位置 + 非空 ⇒ 应回顶",
            RssArticleRefreshScrollPolicy.shouldScrollToTop(
                enabled = true,
                refreshPending = true,
                restoringPosition = false,
                hasItems = true
            )
        )
    }

    @Test
    fun policyDeniesWhenSettingDisabled() {
        assertFalse(
            "开关关闭（新模式：保持定位）⇒ 不回顶",
            RssArticleRefreshScrollPolicy.shouldScrollToTop(
                enabled = false,
                refreshPending = true,
                restoringPosition = false,
                hasItems = true
            )
        )
    }

    @Test
    fun policyDeniesWhenNoRefreshIntent() {
        assertFalse(
            "无刷新意图（如触底翻页 / 已读态刷新）⇒ 不回顶",
            RssArticleRefreshScrollPolicy.shouldScrollToTop(
                enabled = true,
                refreshPending = false,
                restoringPosition = false,
                hasItems = true
            )
        )
    }

    @Test
    fun policyDeniesWhenRestoringPosition() {
        assertFalse(
            "存在旋转/进程重建待恢复位置 ⇒ 位置恢复优先，不回顶",
            RssArticleRefreshScrollPolicy.shouldScrollToTop(
                enabled = true,
                refreshPending = true,
                restoringPosition = true,
                hasItems = true
            )
        )
    }

    @Test
    fun policyDeniesOnEmptyList() {
        assertFalse(
            "空表 ⇒ 不回顶（无视觉意义且会白跑一次挂起滚动）",
            RssArticleRefreshScrollPolicy.shouldScrollToTop(
                enabled = true,
                refreshPending = true,
                restoringPosition = false,
                hasItems = false
            )
        )
    }

    @Test
    fun policyFullTruthTable() {
        var trueCount = 0
        for (enabled in listOf(true, false)) {
            for (pending in listOf(true, false)) {
                for (restoring in listOf(true, false)) {
                    for (hasItems in listOf(true, false)) {
                        val actual = RssArticleRefreshScrollPolicy.shouldScrollToTop(
                            enabled = enabled,
                            refreshPending = pending,
                            restoringPosition = restoring,
                            hasItems = hasItems
                        )
                        val expected = enabled && pending && !restoring && hasItems
                        assertTrue(
                            "真值表不一致：enabled=$enabled pending=$pending restoring=$restoring hasItems=$hasItems",
                            actual == expected
                        )
                        if (expected) trueCount++
                    }
                }
            }
        }
        assertTrue("16 组组合中应恰有 1 组为真（当前 $trueCount）", trueCount == 1)
    }

    // ------------------------------------------------------------------ 宿主接线契约

    /** 置位点唯一：只有刷新入口 `loadArticles(fullRefresh)` 会置 true（页码切换与触底翻页不得置位）。 */
    @Test
    fun refreshIntentIsSetAtExactlyOneEntry() {
        val s = fragment()
        val setTrueCount = s.split("scrollTopOnNextData = true").size - 1
        assertTrue("`scrollTopOnNextData = true` 只应出现 1 次（刷新入口），实际 $setTrueCount", setTrueCount == 1)
        assertTrue(
            "置位必须发生在 refreshLayout 的加载入口 loadArticles(fullRefresh: Boolean = false) 内",
            s.contains("private fun loadArticles(fullRefresh: Boolean = false)") &&
                s.contains("scrollTopOnNextData = true")
        )
    }

    /** 消费语义：无论是否回顶都清零（consume-once），且判定经单源纯函数。 */
    @Test
    fun consumeClearsFlagAndDelegatesToPolicy() {
        val s = fragment()
        assertTrue("必须有单源消费入口 decideRefreshScrollToTop", s.contains("private fun decideRefreshScrollToTop("))
        assertTrue(
            "判定必须委派纯函数（不得内联多条件）",
            s.contains("RssArticleRefreshScrollPolicy.shouldScrollToTop(")
        )
        assertTrue(
            "开关必须经 AppConfig 消费（防设置无效的静默失联）",
            s.contains("enabled = AppConfig.rssArticleRefreshToTop")
        )
        assertTrue("消费后必须清零标志", s.contains("scrollTopOnNextData = false"))
    }

    /** 回顶必须在数据写入列表状态之后；且 Compose 路径必须先读旋转恢复下标再消费。 */
    @Test
    fun composePathReadsRestoreIndexBeforeConsumeAndScrollsAfterData() {
        val s = fragment()
        val restoringRead = s.indexOf("val restoringPosition = pendingScrollIndex > 0")
        assertTrue("Compose 路径必须先读 pendingScrollIndex 作为 restoringPosition", restoringRead >= 0)
        val consumeCall = s.indexOf("consumePendingScroll()", restoringRead)
        assertTrue(
            "必须先读下标再调用 consumePendingScroll()（后者会把下标置 -1 ⇒ 顺序颠倒使旋转恢复失效）",
            consumeCall > restoringRead
        )
        val dataWrite = s.indexOf("articlesState.value = newList")
        assertTrue("数据写入必须在回顶判定之前", dataWrite in 0..<restoringRead)
        assertTrue(
            "Compose 路径回顶必须由判定结果驱动",
            s.contains("if (decideRefreshScrollToTop(restoringPosition, newList.isNotEmpty())) {")
        )
    }

    /** View 路径（样式 5）：判定为真时改走同步整表替换，规避 DiffUtil 异步派发覆盖回顶。 */
    @Test
    fun viewPathUsesSynchronousReplaceWhenScrollingToTop() {
        val s = fragment()
        assertTrue(
            "View 路径必须在 setItems 之前取判定结果",
            s.contains("val refreshScrollToTop = decideRefreshScrollToTop(false, newList.isNotEmpty())")
        )
        assertTrue(
            "判定为真必须落入同步整表替换分支（setItems(newList) 而非 DiffUtil 异步派发）",
            s.contains("|| refreshScrollToTop) {")
        )
        assertTrue(
            "回顶调用必须在该分支之后执行",
            s.contains("if (refreshScrollToTop) {")
        )
    }

    /** 失败路径：加载失败不产生本次数据发射 ⇒ 必须清零意图，防悬挂标志被已读态发射误消费。 */
    @Test
    fun loadErrorClearsRefreshIntent() {
        val s = fragment()
        val anchor = s.indexOf("loadErrorLiveData.observe(viewLifecycleOwner)")
        assertTrue("必须保留 loadErrorLiveData 观察者", anchor >= 0)
        val window = s.substring(anchor, (anchor + 400).coerceAtMost(s.length))
        assertTrue(
            "loadErrorLiveData 观察者内必须清零回顶意图（防标志悬挂 ⇒ 阅读时突然跳顶）",
            window.contains("scrollTopOnNextData = false")
        )
    }

    /** 防回退：不得改动列表 key 锚定机制（回顶靠命令式滚动，不靠换 key）。 */
    @Test
    fun listKeyAnchoringMechanismUntouched() {
        val compose = SourceFileProbe.sourceText("ui/rss/article/compose/RssArticlesComposeList.kt")
        assertTrue("条目稳定 key 必须保持单源", compose.contains("RssArticleKey::of"))
        assertFalse(
            "回顶不得通过清空/篡改 key 实现（会整条重建并重取封面）",
            compose.contains("key = { index, _ -> index.toString() }")
        )
    }
}
