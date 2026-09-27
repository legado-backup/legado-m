package io.legado.app.service

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W3 / REQ-16（AD-07 v3.0）：朗读**段落级恢复**的接线不变量。
 *
 * 为什么用源码不变量：朗读依赖 TTS/ExoPlayer 运行时与真实章节内容，纯 JVM 无法驱动；
 * 而本批最易失守的是「接线点遗漏」与「越权劫持用户显式定位」，两者都能用静态断言锁定。
 *
 * 四条约定：
 * ① 写入点是**段落切换 / 暂停 / 服务销毁**（且覆盖系统 TTS 与 HTTP 两条链路的切换点）；
 * ② 读回**仅在「章首默认位置」**生效（选句朗读 / 面板拖进度 / 选章不得被锚点劫持）；
 * ③ 冲突校验三律齐备（章节不匹配 / 越界 / 页号无效 ⇒ 静默回落段落起点）；
 * ④ 旧的注释残片（`putLong(METADATA_KEY_DURATION, nowSpeak…)`）必须已删除，不留悬空注释。
 */
class ReadAloudVoiceAnchorTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
            .readText()
            // 工作副本可能是 CRLF（Windows 检出）⇒ 归一到 LF，保证多行断言稳定
            .replace("\r\n", "\n")

    private val base by lazy { read("src/main/java/io/legado/app/service/BaseReadAloudService.kt") }
    private val http by lazy { read("src/main/java/io/legado/app/service/HttpReadAloudService.kt") }
    private val tts by lazy { read("src/main/java/io/legado/app/service/TTSReadAloudService.kt") }

    @Test
    fun anchorIsWrittenOnParagraphSwitchPauseAndDestroy() {
        listOf("prev", "next", "pause", "destroy").forEach { reason ->
            assertTrue(
                "BaseReadAloudService 缺少「$reason」时点的锚点写入",
                base.contains("persistVoiceParagraphAnchor(\"$reason\")")
            )
        }
        assertTrue(
            "HTTP 朗读链路段落切换须写锚点",
            http.contains("persistVoiceParagraphAnchor(\"http-paragraph\")")
        )
        assertTrue(
            "系统 TTS 链路段落切换须写锚点",
            tts.contains("persistVoiceParagraphAnchor(\"tts-paragraph\")")
        )
    }

    @Test
    fun anchorIsScopedToChapterToAvoidCrossChapterResume() {
        assertTrue(
            "写入须同时写归属章节",
            base.contains("book.voiceParagraphAnchorChapter = chapterIndex")
        )
        assertTrue(
            "读回须校验章节匹配（否则切章后误用旧锚点跳错位置）",
            base.contains("章节不匹配丢弃")
        )
    }

    @Test
    fun resumeOnlyAppliesWhenCallerGivesDefaultChapterStart() {
        val gate = "if (play && !toLast && pageIndex == 0 && startPos == 0) {"
        assertTrue("读回须受「章首默认位置」门禁（防劫持显式定位）", base.contains(gate))
        val resolveAt = base.indexOf("resolveVoiceAnchorStart(textChapter)")
        val gateAt = base.indexOf(gate)
        assertTrue("解析调用须在门禁之内", resolveAt > gateAt && gateAt > 0)
    }

    @Test
    fun conflictFallsBackSilentlyWithAllThreeRules() {
        listOf("锚点越界丢弃", "页号无效丢弃", "章节不匹配丢弃").forEach { rule ->
            assertTrue("缺冲突校验：$rule", base.contains(rule))
        }
        assertTrue(
            "冲突须静态降级（返回 null 由调用方保持原起播位置，不抛异常）",
            base.contains("private fun resolveVoiceAnchorStart(chapter: TextChapter): Pair<Int, Int>?")
        )
    }

    @Test
    fun staleCommentedOutMetadataLineIsRemoved() {
        assertFalse(
            "旧注释残片必须删除（与实现不一致的悬空注释）",
            base.contains("METADATA_KEY_DURATION, nowSpeak.toLong()")
        )
    }

    @Test
    fun anchorPersistenceLeavesDiagnosableLog() {
        assertTrue("写锚点须留可定位日志", base.contains("ReadAloudAnchor: 写入"))
        assertTrue("读回须留可定位日志", base.contains("ReadAloudAnchor: 读回命中"))
    }
}