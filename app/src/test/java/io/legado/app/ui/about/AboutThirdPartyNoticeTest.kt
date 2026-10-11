package io.legado.app.ui.about

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 许可聚合载体（epub-md-rich-rendering 阶段 6.5 / XB.8 配对）。
 *
 * **为什么必须机检**：4.16 引入的 OFL 字体与 CC0/PD 图片带**署名/许可随包**义务，而这些义务只写进
 * `NOTICE.md` 就是"自证"——把某段删掉、把入口摘掉，都不会让任何测试变红（用户与审计都看不到）。
 * 故把三件事锁死：①载体资产在场且含全部必备条目；②关于页确实挂了入口；③文案资源在中文包里存在
 * （缺 string 会在运行期直接崩或显示成键名）。
 */
class AboutThirdPartyNoticeTest {

    private fun asset(path: String): File? = listOf(
        File("src/main/assets/$path"),
        File("../app/src/main/assets/$path"),
        File("app/src/main/assets/$path")
    ).firstOrNull { it.isFile }

    @Test
    fun `许可聚合载体在场且覆盖四类义务`() {
        val file = asset("NOTICE.md")
        assertTrue("NOTICE.md 必须随包存在（否则关于页入口点了没反应）", file != null)
        val text = file!!.readText()
        assertTrue("载体不得为空", text.length > 800)
        listOf(
            "OFL-1.1",                 // 字体许可（含"许可原文随包"说明）
            "Orbitron",                // 霓虹夜行标题字
            "Share Tech Mono",         // 星图读数
            "Public domain",           // 星图底纹（PD）
            "CC0",                     // 墨迹底纹（CC0）
            "Wikimedia",               // 可考证来源
            "不代表",                   // 不暗示机构背书（来源标注纪律）
            "mermaid", "KaTeX", "highlight.js",  // 富渲染 JS 库
            "MIT", "BSD-3-Clause",      // 库许可
            "不内置第三方 IP",           // 合规红线（AD-21）
            "sources.json"              // 逐项登记（含 SHA-256）落点指引
        ).forEach { mark ->
            assertTrue("NOTICE.md 缺少必备条目：$mark", text.contains(mark))
        }
    }

    @Test
    fun `关于页挂载了第三方素材许可入口`() {
        val fragment = SourceFileProbe.sourceText("ui/about/AboutFragment.kt")
        assertTrue("必须有独立入口键", fragment.contains("KEY_THIRD_PARTY_NOTICE"))
        assertTrue("入口必须打开聚合载体", fragment.contains("\"NOTICE.md\""))
        assertTrue("入口标题必须走资源（不得硬编码文案）", fragment.contains("R.string.about_third_party_notice"))
    }

    @Test
    fun `文案资源在中文包存在`() {
        val zh = File(File("src/main/res"), "values-zh/strings.xml")
            .takeIf { it.isFile }
            ?: File(File("../app/src/main/res"), "values-zh/strings.xml")
        assertTrue("必须能读到 values-zh/strings.xml", zh.isFile)
        val text = zh.readText()
        assertTrue("缺 about_third_party_notice 标题", text.contains("name=\"about_third_party_notice\""))
        assertTrue("缺 about_third_party_notice_summary 摘要", text.contains("name=\"about_third_party_notice_summary\""))
    }
}