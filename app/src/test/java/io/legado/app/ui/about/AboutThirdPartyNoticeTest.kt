package io.legado.app.ui.about

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 许可聚合载体（epub-md-rich-rendering 阶段 6.5 / XB.8 配对）。
 *
 * **为什么必须机检**：第三方素材带**署名/许可/非官方声明**义务，而这些义务只写进
 * `NOTICE.md` 就是"自证"——把某段删掉、把入口摘掉，都不会让任何测试变红（用户与审计都看不到）。
 * 故把三件事锁死：①载体资产在场且含全部**必备义务条目**；②关于页确实挂了入口；③文案资源在中文包里存在。
 *
 * 判据修正（2026-10-17）：原内置 11 套主题（含 Orbitron / Share Tech Mono 字体、PD 天球图、CC0 水墨图）
 * 已按用户裁定**全部删除** ⇒ 这些条目不再随包，断言随之改为**当前载体真正承载的义务**：
 * 非官方声明 / 不暗示原作方背书 / SHA-256 逐项登记 / 成人恐怖向剔除红线 / 富渲染 JS 库许可。
 */
class AboutThirdPartyNoticeTest {

    private fun asset(path: String): File? = listOf(
        File("src/main/assets/$path"),
        File("../app/src/main/assets/$path"),
        File("app/src/main/assets/$path")
    ).firstOrNull { it.isFile }

    @Test
    fun `许可聚合载体在场且覆盖必备义务`() {
        val file = asset("NOTICE.md")
        assertTrue("NOTICE.md 必须随包存在（否则关于页入口点了没反应）", file != null)
        val text = file!!.readText()
        assertTrue("载体不得为空", text.length > 800)
        listOf(
            "非官方",                    // 第三方素材准入的第一条兜底声明
            "不代表原作方",               // 不暗示原作方背书
            "SHA-256",                  // 逐项登记可考证
            "sources.json",              // 登记落点指引
            "剔除",                      // 成人向/恐怖向红线
            "不内置第三方 IP 的名称与文案", // 新红线表述（旧"不内置原作素材"已随口径更新）
            "mermaid", "KaTeX", "highlight.js",  // 富渲染 JS 库
            "MIT", "BSD-3-Clause"        // 库许可
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