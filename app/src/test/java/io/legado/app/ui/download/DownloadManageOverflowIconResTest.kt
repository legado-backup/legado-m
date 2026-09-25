package io.legado.app.ui.download

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏包 §1.2 路径 B：`DownloadManageScreen` 的 `MenuAction → AppManagementMenuAction` 转换必须透传
 * **图标双源**（`icon` / `iconRes`）。
 * 本页同时保留「header 分组标签 → 禁用行」的既有映射语义（不得因补图标而改动）。
 */
class DownloadManageOverflowIconResTest {

    @Test
    fun transformPassesBothIconSources() {
        val rel = "ui/download/DownloadManageScreen.kt"
        val code = SourceFileProbe.sourceText(rel)
        assertTrue("转换点必须透传 drawable 源", code.contains("iconRes = menuAction.iconRes,"))
        assertTrue("转换点必须透传 ImageVector 源", code.contains("icon = menuAction.icon,"))
        assertTrue("既有 header → 禁用行映射语义不得回归", code.contains("enabled = !menuAction.header,"))
        assertTrue(
            "透传点须带用途注释（防后人「清理无用参数」误删）",
            SourceFileProbe.rawText(rel).contains("图标双源同链透传")
        )
    }
}