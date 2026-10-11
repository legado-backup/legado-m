package io.legado.app.help.md

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Markdown 图片引用判定单测（epub-md-rich-rendering 补充任务 S3① 配对）。
 *
 * 这一层是**纯函数**：把"该不该内联 / 路径归一化 / MIME / 目录穿越"的决策矩阵逐格钉住，
 * 平台 IO（文件/SAF 查找）只在 `MdRelativeImageInliner` 且由真机 L2 覆盖。
 *
 * 关键不变量：
 * ①只放行"相对路径 + `file:`" —— `http(s)` 仍走网络、`data:` 不重复处理、协议相对不放行；
 * ②`..` 逃出文档目录必须被拒（内联等于把本地文件读进页面 ⇒ 目录穿越必须是硬约束）；
 * ③未知扩展名不内联（避免把 md 里误写的任意路径读成 `data:`）。
 */
class MdImageRefPolicyTest {

    // === ① 候选判定 ===

    @Test
    fun `相对路径与 file 协议是内联候选`() {
        assertTrue(MdImageRefPolicy.isInlineCandidate("./img/a.png"))
        assertTrue(MdImageRefPolicy.isInlineCandidate("img/a.png"))
        assertTrue(MdImageRefPolicy.isInlineCandidate("a.png"))
        assertTrue(MdImageRefPolicy.isInlineCandidate("../up/a.png"))
        assertTrue(MdImageRefPolicy.isInlineCandidate("/sdcard/x/a.png"))
        assertTrue(MdImageRefPolicy.isInlineCandidate("file:///sdcard/x/a.png"))
        assertTrue("前后空白应被容忍", MdImageRefPolicy.isInlineCandidate("  a.png  "))
    }

    @Test
    fun `网络协议协议相对与 data 都不是内联候选`() {
        assertFalse("线上图片仍走网络", MdImageRefPolicy.isInlineCandidate("https://example.com/a.png"))
        assertFalse(MdImageRefPolicy.isInlineCandidate("http://example.com/a.png"))
        assertFalse(MdImageRefPolicy.isInlineCandidate("//example.com/a.png"))
        assertFalse("已内联的不再处理", MdImageRefPolicy.isInlineCandidate("data:image/png;base64,AAAA"))
        assertFalse(MdImageRefPolicy.isInlineCandidate("content://media/external/images/1"))
        assertFalse(MdImageRefPolicy.isInlineCandidate(""))
        assertFalse(MdImageRefPolicy.isInlineCandidate("   "))
    }

    // === ② 路径归一化与目录穿越 ===

    @Test
    fun `相对路径归一化消去点段`() {
        assertEquals("a.png", MdImageRefPolicy.normalizeRelative("./a.png"))
        assertEquals("img/a.png", MdImageRefPolicy.normalizeRelative("img//a.png"))
        assertEquals("a.png", MdImageRefPolicy.normalizeRelative("img/../a.png"))
        assertEquals("img/a.png", MdImageRefPolicy.normalizeRelative("img/./sub/../a.png"))
    }

    @Test
    fun `逃出文档目录的相对路径被拒`() {
        assertNull("越界一次即拒", MdImageRefPolicy.normalizeRelative("../a.png"))
        assertNull(MdImageRefPolicy.normalizeRelative("../../etc/passwd"))
        assertNull("深度越界同样拒", MdImageRefPolicy.normalizeRelative("img/../../a.png"))
        assertNull("归一化后为空也拒（指向目录而非文件）", MdImageRefPolicy.normalizeRelative("./"))
    }

    @Test
    fun `绝对文件路径单独识别不走目录拼接`() {
        assertTrue(MdImageRefPolicy.isAbsoluteFilePath("/sdcard/x/a.png"))
        assertFalse(MdImageRefPolicy.isAbsoluteFilePath("./a.png"))
        assertFalse(MdImageRefPolicy.isAbsoluteFilePath("img/a.png"))
    }

    @Test
    fun `file 协议被剥成文件系统路径`() {
        assertEquals("/sdcard/x/a.png", MdImageRefPolicy.toFilePath("file:///sdcard/x/a.png"))
        assertEquals("a.png", MdImageRefPolicy.toFilePath("a.png"))
        assertEquals("/sdcard/x/a.png", MdImageRefPolicy.toFilePath("/sdcard/x/a.png"))
        // 剥完后必须落在"绝对文件路径"分支上（否则会被误当相对路径拼目录）
        assertTrue(MdImageRefPolicy.isAbsoluteFilePath(MdImageRefPolicy.toFilePath("file:///sdcard/x/a.png")))
    }

    // === ③ 类型与 MIME ===

    @Test
    fun `已知图片扩展名给出具体 MIME`() {
        assertEquals("image/png", MdImageRefPolicy.mimeFor("a.png"))
        assertEquals("image/jpeg", MdImageRefPolicy.mimeFor("a.JPG"))
        assertEquals("image/jpeg", MdImageRefPolicy.mimeFor("a.jpeg"))
        assertEquals("image/gif", MdImageRefPolicy.mimeFor("a.gif"))
        assertEquals("image/webp", MdImageRefPolicy.mimeFor("a.webp"))
        assertEquals("image/svg+xml", MdImageRefPolicy.mimeFor("a.svg"))
        assertEquals("image/bmp", MdImageRefPolicy.mimeFor("a.bmp"))
    }

    @Test
    fun `未知扩展名与无扩展名不内联`() {
        assertNull("不得把任意文件读成 data:", MdImageRefPolicy.mimeFor("a.txt"))
        assertNull(MdImageRefPolicy.mimeFor("a"))
        assertNull(MdImageRefPolicy.mimeFor("a.png.exe"))
        assertNull(MdImageRefPolicy.mimeFor(""))
    }

    // === 引用串清洗 ===

    @Test
    fun `查询串与片段被剥离`() {
        assertEquals("a.png", MdImageRefPolicy.stripQueryAndFragment("a.png?x=1#f"))
        assertEquals("a.png", MdImageRefPolicy.stripQueryAndFragment("a.png?v=2"))
        assertEquals("a.png", MdImageRefPolicy.stripQueryAndFragment("a.png#anchor"))
        assertEquals("a.png", MdImageRefPolicy.stripQueryAndFragment("a.png"))
    }

    @Test
    fun `百分号转义被解码而加号保持字面量`() {
        assertEquals("a b.png", MdImageRefPolicy.percentDecode("a%20b.png"))
        assertEquals("图/a.png", MdImageRefPolicy.percentDecode("%E5%9B%BE/a.png"))
        assertEquals("图 片.png", MdImageRefPolicy.percentDecode("%E5%9B%BE%20%E7%89%87.png"))
        assertEquals("a+b.png", MdImageRefPolicy.percentDecode("a+b.png"))
        assertEquals("100%.png", MdImageRefPolicy.percentDecode("100%.png"))
        assertEquals("截%断", MdImageRefPolicy.percentDecode("截%断"))
    }

    @Test
    fun `文件名取最后一个斜杠之后`() {
        assertEquals("a.png", MdImageRefPolicy.fileNameOf("img/sub/a.png"))
        assertEquals("a.png", MdImageRefPolicy.fileNameOf("a.png"))
        assertEquals("", MdImageRefPolicy.fileNameOf("img/"))
    }

    @Test
    fun `data URI 构造形态固定`() {
        assertEquals("data:image/png;base64,AAAA", MdImageRefPolicy.dataUri("image/png", "AAAA"))
    }

    @Test
    fun `预算上限存在且单图小于总量`() {
        assertTrue(MdImageRefPolicy.MaxInlineBytes > 0)
        assertTrue(
            "单图上限必须小于总量上限（否则单图即可击穿总预算）",
            MdImageRefPolicy.MaxInlineBytes < MdImageRefPolicy.MaxInlineTotalBytes
        )
    }
}