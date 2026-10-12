package io.legado.app.help.md

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * S9「tiny / 完整双档产物」构建契约（epub-md-rich-rendering · AD-27 / NFR-06 · 审计 P-03 配对）。
 *
 * 为什么必须机检：`build.gradle` 里的资产排除项有**两类静默失效**——
 * ①**属性没接线**（写了排除但不由 `mdTiny` 驱动 ⇒ 默认构建也被砍掉 mermaid，用户侧"图表不渲染"却无测试变红）；
 * ②**路径写岔**（排除一个没人使用的路径 ⇒ 体积没降、也没人发现）。
 * 两者都不会让任何现有用例变红 ⇒ 必须把"属性驱动 + 路径与注入器同源"钉在源码/构建脚本层。
 */
class MdTinyArtifactPolicyTest {

    private val gradle: String get() = SourceFileProbe.appBuildGradleText()

    /**
     * **剥掉行注释**后的构建脚本。
     *
     * 为什么必须：本文件的"禁回改"红线断言（`!contains("assets.filter.exclude")`）会被 build.gradle 里
     * **解释该红线本身的注释**命中 ⇒ 假失败（与项目既有铁律"断言行前先剔注释"同源）。
     */
    private val gradleCode: String get() = SourceFileProbe.stripComments(gradle)

    @Test
    fun `tiny 档由 mdTiny 属性驱动且排除项落在打包阶段`() {
        val g = gradleCode
        assertTrue("必须存在 mdTiny 属性判据（否则无法产出 tiny 档）", g.contains("mdTiny"))
        assertTrue(
            "排除项必须走 aapt2 的 ignoreAssetsPatterns（**打包阶段**）",
            g.contains("ignoreAssetsPatterns.add(")
        )
        // 默认构建零影响：属性缺失时不得进入排除分支（`project.hasProperty('mdTiny')` 是唯一门）
        assertTrue(
            "属性必须以 hasProperty 判空为门（缺失时默认构建不受影响）",
            g.contains("project.hasProperty('mdTiny')")
        )
        // ⚠️ 机制红线（2026-10-13 实测）：`assets.filter` 的 `exclude` 在 AGP 8 下**静默失效**
        // （已登记、无报错，但产物 APK 内仍含该文件）⇒ 禁止改回该写法。
        assertTrue(
            "禁止改回 assets.filter 的 exclude 写法（AGP 8 下静默失效，体积零变化）",
            !g.contains("assets.filter")
        )
    }

    @Test
    fun `排除模式与注入器资产常量同源`() {
        // 写岔即静默失效：aapt2 按**资源名**匹配 ⇒ 模式必须等于注入器真正读取的那个资产的**文件名**
        val assetName = MdRichRenderInjector.MermaidAsset.substringAfterLast('/')
        assertEquals("注入器 mermaid 资产文件名", "mermaid.min.js", assetName)
        assertEquals("注入器 mermaid 资产路径", "md/vendor/mermaid.min.js", MdRichRenderInjector.MermaidAsset)
        assertTrue(
            "排除模式必须等于注入器资产的文件名（否则排除的是没人用的名字）",
            gradle.contains("ignoreAssetsPatterns.add('$assetName')")
        )
    }
}