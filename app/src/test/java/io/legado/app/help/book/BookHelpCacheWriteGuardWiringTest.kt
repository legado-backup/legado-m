package io.legado.app.help.book

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * `BookHelp` 内容写入链的**稳定性边界接线锁**（epub-md-rich-rendering 补充任务 S12 配对；AD-28⑥ / NFR-07①）。
 *
 * ### 为什么用"文本契约"而不是行为单测
 * 该边界只有在 Android 运行时才生效（真实写盘 + `Context.toastOnUi` 提示），单测进程起不了 Android 环境；
 * 而"接线被静默删除/改坏"是本项目**已多次实证**的失守方式（纯行为单测会漏掉"根本没接线"）。
 * 故把**接线事实**钉住：`BookHelp` 两处调用（写前把关 + 写失败处理）+ `ContentCacheWriteBoundary`
 * 的去重与留痕 —— 判据（纯函数）由 `ContentCacheWriteGuardTest` 覆盖，两侧合起来才是完整边界。
 */
class BookHelpCacheWriteGuardWiringTest {

    private fun read(rel: String): String {
        val f = File(rel)
        assertTrue("源文件缺失：${f.absolutePath}", f.isFile)
        // ⚠️ 必须归一化换行：工作副本可能是 CRLF（git checkout 时会转换）⇒ 跨行断言会因 `\r\n` 失配
        return f.readText().replace("\r\n", "\n")
    }

    @Test
    fun `正文写入链必须接入边界（写前把关 + 写失败处理）`() {
        val t = read("src/main/java/io/legado/app/help/book/BookHelp.kt")
        assertTrue(
            "写盘前须经『磁盘将满 ⇒ 禁写』把关（否则磁盘满时会反复写并留下半写缓存）",
            t.contains("ContentCacheWriteBoundary.blockWriteIfNoSpace(") &&
                t.contains("downloadDir.usableSpace, content.length, bookChapter.index")
        )
        assertTrue(
            "写失败须交边界处理（只有磁盘满/无权限才提示，其它异常不误报）",
            t.contains("ContentCacheWriteBoundary.onWriteFailure(e, bookChapter.index)")
        )
        assertTrue(
            "异常不得被吞掉（既有错误语义零变化）",
            Regex("""onWriteFailure\(e, bookChapter\.index\)\s*\n\s*throw e""").containsMatchIn(t)
        )
    }

    @Test
    fun `边界动作层必须去重并留痕`() {
        val t = read("src/main/java/io/legado/app/help/book/ContentCacheWriteBoundary.kt")
        assertTrue(
            "提示须走去重判据（批量缓存同一原因只提示一次，避免刷屏）",
            t.contains("ContentCacheWriteGuard.shouldNotify(lastNotifiedAt, now)")
        )
        assertTrue(
            "『禁写』路径须留痕",
            t.contains("磁盘空间不足，跳过正文写入")
        )
        assertTrue(
            "『写失败被拒』路径须留痕（只弹提示不留日志 ⇒ 真机无从取证提示有没有触发）",
            t.contains("正文写入被拒（磁盘满/无权限）⇒ 已提示用户")
        )
    }
}