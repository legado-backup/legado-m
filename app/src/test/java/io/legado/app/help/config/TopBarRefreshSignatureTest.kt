package io.legado.app.help.config

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 顶栏刷新签名不变量回归测试（B7 R29，依据 theme-consistency-iron-rule K2/K4）。
 *
 * 缺陷（2026-09-23 审计实证 B3/C4）：`TopBarConfig.currentSignature` 的**自定义顶栏包分支**
 * 只含 `isNight + 包名 + 配置文件 mtime`，换主题色不改这三者 ⇒ 签名不变 ⇒ 消费方
 * （`RoundedTagBarView` / `MainTopBarView` / `ExploreFragment` / `ReadRecordFragment`）的
 * 非 force 刷新直接早退 ⇒ 标签栏底色不随主题色变化。
 *
 * `currentSignature` 需要真实 Context（SharedPreferences），本项目单测无 Robolectric，
 * 故按源码结构不变量固化：**两个返回分支都必须包含 themeUiSignature()**。
 */
class TopBarRefreshSignatureTest {

    @Test
    fun currentSignature_includesThemeUiSignatureInBothBranches() {
        val rel = "src/main/java/io/legado/app/help/config/TopBarConfig.kt"
        val candidates = listOf(File(rel), File("../app/$rel"), File("app/$rel"))
        val file = candidates.firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        val text = file.readText()

        val start = text.indexOf("fun currentSignature(")
        assertTrue("未定位到 currentSignature", start >= 0)
        val body = text.substring(start, text.indexOf("\n    }", start))

        val hits = Regex("themeUiSignature\\(\\)").findAll(body).count()
        assertTrue(
            "currentSignature 的默认与自定义顶栏包两个分支都必须纳入 themeUiSignature()，实际命中 $hits 次",
            hits >= 2
        )
    }
}