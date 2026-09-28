package io.legado.app.ui.scene

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W8 9.4（REQ-32）：名场面库页的**组件族符合性 + 入口可达性 + 跳回路由**不变量。
 *
 * 三条防失守：
 * ① **死页面**：新页面必须同时有「我的 → 工具」入口与 `handleSettingsRowClick` 分支（本主线已实证
 *    多次「只建页不接入口 = 用户永远到不了」）；
 * ② **组件族**：页面必须复用管理族既有组件，且**不得**自建取色链（M3 派生色 / 硬编码色）；
 * ③ **跳回路由**：`contentKind` 三分支必须齐全（文字/漫画走书、图片走 `ImagePlay` 重建）。
 */
class SceneBookmarkLibraryWiringTest {

    private val activity by lazy { SourceFileProbe.sourceText("ui/scene/SceneBookmarkActivity.kt") }
    private val screen by lazy { SourceFileProbe.sourceText("ui/scene/SceneBookmarkScreen.kt") }

    @Test
    fun activityIsAComposeShellHost() {
        assertTrue("必须用 composeShell 合成壳（禁手写匿名壳）", activity.contains("composeShell(this)"))
        assertTrue("必须经 attachComposeContent 挂载", activity.contains("attachComposeContent {"))
        assertTrue("必须包 LegadoTheme", activity.contains("LegadoTheme {"))
        assertTrue("必须渲染 SceneBookmarkScreen", activity.contains("SceneBookmarkScreen("))
    }

    @Test
    fun screenReusesManagementComponentFamily() {
        assertTrue("缺 AppManagementScaffold", screen.contains("AppManagementScaffold("))
        assertTrue("缺 AppManagementLazyColumn", screen.contains("AppManagementLazyColumn("))
        assertTrue("缺 AppManagementListRow", screen.contains("AppManagementListRow("))
        assertTrue("缺分组头 GroupHeader", screen.contains("GroupHeader("))
        assertTrue("缺空态 EmptyStatePlaceholder", screen.contains("EmptyStatePlaceholder("))
        assertTrue("缩略图必须沿用 FilletImageView", screen.contains("FilletImageView("))
        assertTrue("行高口径 56dp", screen.contains("minHeight = 56.dp"))
    }

    @Test
    fun screenDoesNotBuildItsOwnColorChain() {
        assertFalse(
            "页面不得硬编码颜色",
            screen.contains("Color(0x") || screen.contains("Color.White") || screen.contains("Color.Black")
        )
        assertFalse(
            "页面不得用 M3 派生色取色",
            screen.contains("MaterialTheme.colorScheme")
        )
        assertTrue("取色必须来自管理族 palette", screen.contains("rememberAppManagementPalette()"))
    }

    @Test
    fun jumpBackRoutesAllThreeContentKinds() {
        assertTrue(
            "必须按 contentKind 分流",
            activity.contains("when (bookmark.contentKind)") &&
                activity.contains("SceneBookmarkHelper.KIND_IMAGE -> openImageScene(bookmark)")
        )
        assertTrue(
            "文字/漫画必须走 startActivityForBook（含 index）",
            activity.contains("startActivityForBook(book)") && activity.contains("putExtra(\"index\", bookmark.chapterIndex)")
        )
        assertTrue(
            "文字路径须带 chapterPos 精确到段落",
            activity.contains("putExtra(\"chapterPos\", SceneBookmarkHelper.chapterPosOf(bookmark.anchor) ?: 0)")
        )
        assertTrue(
            "图片路径必须重建 ImagePlay 取图上下文",
            activity.contains("ImagePlay.rssArticles = listOf(") &&
                activity.contains("ImagePlay.clearImageCanvasState()")
        )
    }

    @Test
    fun bookFilterEntryShowsByBookTitle() {
        assertTrue(
            "按书过滤入口（阅读菜单「本书名场面」）必须存在",
            activity.contains("fun bookIntent(")
        )
        assertTrue(
            "按书视图须走 flowByBook、全量视图走 flowAll",
            activity.contains("SceneBookmarkHelper.flowByBook(it)") &&
                activity.contains("SceneBookmarkHelper.flowAll()")
        )
        assertTrue(
            "按书聚合必须复用 helper 的纯函数（不在页面重写分组逻辑）",
            activity.contains("SceneBookmarkHelper.groupByBook(it)")
        )
    }
}
