package io.legado.app.ui.source.recycle

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 回收站页「行/壳/容器」收敛不变量（源码文本断言；依据 `ui-standards/component-registry.md` §3.1
 * 三件套口径与用户 2026-09-26 裁定「我的」下的子页/子子页必须同脚手架同行）。
 *
 * **2026-09-27 第四批**：原实现是自绘 `GlassTopAppBar` + 页内 `LazyColumn` + 行间
 * `HorizontalDivider(0.5dp)` + 私有 `RecycleBinActionBar` + 自绘 `RecycleBinItemRow`
 * （取色走 M3 派生键）⇒ 全部换管理族单源。
 */
class RecycleBinScreenTokenTest {

    private val rel = "ui/source/recycle/RecycleBinScreen.kt"

    private fun code(): String = SourceFileProbe.rawText(rel)
        .replace(Regex("/\\*[\\s\\S]*?\\*/"), "")
        .lines()
        .filterNot { it.trimStart().startsWith("//") }
        .joinToString("\n")

    @Test
    fun listUsesSharedContainerAndRowWithoutDividers() {
        val t = code()
        assertTrue("列表容器须收敛到 AppManagementLazyColumn", t.contains("AppManagementLazyColumn("))
        assertTrue("行须收敛到 AppManagementListRow", t.contains("AppManagementListRow("))
        assertFalse("不得再由页内自绘分隔线（卡片行间距改由容器承载）", t.contains("HorizontalDivider"))
        assertFalse("自绘行组件须退役", t.contains("private fun RecycleBinItemRow"))
    }

    @Test
    fun shellUsesSharedManagementScaffold() {
        val t = code()
        assertTrue("壳层须改用管理族 AppManagementScaffold", t.contains("AppManagementScaffold("))
        assertFalse("不得残留页内自绘顶栏", t.contains("GlassTopAppBar("))
        assertFalse("不得残留页内私有批量操作栏", t.contains("RecycleBinActionBar"))
    }

    @Test
    fun noDerivedColorKeysRemain() {
        // H11/B7 取色铁律：页内不得再用 M3 派生键或硬编码色
        val t = code()
        assertFalse("不得再用 M3 派生键 onSurface", t.contains("colorScheme.onSurface"))
        assertFalse("不得再用 M3 派生键 onSurfaceVariant", t.contains("colorScheme.onSurfaceVariant"))
        assertFalse("不得再用 M3 派生键 primary/error", t.contains("colorScheme.primary") || t.contains("colorScheme.error"))
        assertFalse("不得出现 Color(0x…) 硬编码色", Regex("Color\\(0x").containsMatchIn(t))
    }

    @Test
    fun recycleBinPageHasALauncherInMainSources() {
        // 可达性兜底（2026-09-27 回归修复）：回收站页曾因 `3c8aa5c` 迁移丢入口而**全仓零入口**
        // ⇒ 功能存在但用户永远进不去（「其他设置 → 规则回收站」开关形同虚设）。
        // 断言：main 源集里除页面自身外，至少有一处引用它（当前唯一入口 = 书源管理 ⋮ 菜单）。
        val root = java.io.File(SourceFileProbe.mainJavaRoot().absolutePath)
        val launcherRefs = root.walkTopDown()
            .filter { it.isFile && it.extension == "kt" && it.name != "RecycleBinActivity.kt" }
            .count { it.readText().contains("RecycleBinActivity") }
        assertTrue("回收站页必须至少有一个入口（零入口 = 功能不可达）", launcherRefs >= 1)
    }

    @Test
    fun rowMenuCarriesDangerDeleteAndKeepsDialogs() {
        val t = code()
        assertTrue("彻底删除须走 danger 通道（原 tint 硬塞色经薄壳转换后无效）", t.contains("danger = true,"))
        assertTrue("三处危险动作确认框须保留 destructive 语义", t.contains("destructive = true,"))
        assertTrue("滑选多选交互须保留", t.contains("detectDragGesturesAfterLongPress"))
    }
}