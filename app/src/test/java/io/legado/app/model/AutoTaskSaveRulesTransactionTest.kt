package io.legado.app.model

import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B2 · R10「规则保存事务化」回归测试（源码不变量）。
 *
 * 缺陷（修复前）：`saveRules` 先 `deleteAll()` 再 `insert()` 且**无事务** ⇒ insert 抛异常或
 * 进程中途被杀时，库中停留在「已清空」状态，用户规则全部丢失。
 *
 * 本测试锁三条不变量（顺序即语义）：
 * ①整表替换被 `appDb.runInTransaction { … }` 包裹；
 * ②`deleteAll()` 与 `insert(...)` 都在事务**之内**；
 * ③`CacheManager.delete(...)`（文件/缓存 IO）与 `refreshSchedule()`（排程副作用）都在事务**之后**
 *   —— 事务体只做 DB 写（长事务内含 IO 会放大锁窗口，且失败回滚不会撤销已发生的 IO 副作用）。
 *
 * 为什么用源码不变量：真实事务语义需 Room + Robolectric，本仓单测无 Robolectric。
 */
class AutoTaskSaveRulesTransactionTest {

    private fun saveRulesBody(): String {
        val rel = "src/main/java/io/legado/app/model/AutoTask.kt"
        val f = listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }
        val text = f.readText()
        val start = text.indexOf("fun saveRules(")
        assertTrue("未找到 saveRules", start >= 0)
        val end = text.indexOf("\n    }", start)
        val body = text.substring(start, if (end > start) end else text.length)
        // ⚠ 必须先剔除注释行：修复说明注释里会合法地出现 `deleteAll()` / `insert()` 等字面量，
        // 否则顺序断言会被注释命中而误报（本项目同类陷阱已两次踩到）。
        return body.lines()
            .filterNot { it.trimStart().let { t -> t.startsWith("*") || t.startsWith("//") || t.startsWith("/*") } }
            .joinToString("\n")
    }

    @Test
    fun wholeTableReplace_isWrappedInTransaction() {
        val body = saveRulesBody()
        assertTrue("必须使用 appDb.runInTransaction", body.contains("runInTransaction {"))
        val tx = body.indexOf("runInTransaction")
        val del = body.indexOf("deleteAll()")
        val ins = body.indexOf("insert(")
        assertTrue("deleteAll 必须在事务之内", tx in 0 until del)
        assertTrue("insert 必须在事务之内", del in 0 until ins)
    }

    @Test
    fun ioAndSchedulingSideEffects_areOutsideTransaction() {
        val body = saveRulesBody()
        val ins = body.indexOf("insert(")
        val cache = body.indexOf("CacheManager.delete(")
        val refresh = body.indexOf("refreshSchedule()")
        assertTrue("缓存清理必须在事务之后（事务体内禁 IO）", cache > ins)
        assertTrue("重排程必须在缓存清理之后", refresh > cache)
    }
}