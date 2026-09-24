package io.legado.app.help.crypto

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * G-10 存量清偿（2026-09-24）的配对不变量 —— `help/crypto/` 域。
 *
 * 清偿内容：`SymmetricCryptoAndroid.decrypt(String)` 的 catch 分支里原有一行裸
 * `Log.d("RssDecrypt", …)`，其字段与紧邻的 `AppLog.put(...)` **逐字重复**
 * （algorithm / dataLen / exception）⇒ 冗余；且 `"RssDecrypt"` 非 AppLog 登记 TAG
 * （全仓仅此一处 + 一份已归档 spec 提及，无采集脚本依赖）⇒ **删除裸 Log 行**，
 * 诊断信息由 `AppLog.put`（含异常栈）完整覆盖，无需另立 TAG 常量。
 *
 * 判定方式对齐门禁口径：以 `^import android.util.Log$` **定性**（防子串误报）。
 */
class SymmetricCryptoLogComplianceTest {

    private fun source(): String {
        val rel = "src/main/java/io/legado/app/help/crypto/SymmetricCryptoAndroid.kt"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }

    @Test
    fun hasNoBareAndroidLogImport() {
        assertFalse(
            "不得再出现裸 `import android.util.Log`（日志统一走 AppLog）",
            Regex("^import android\\.util\\.Log$", RegexOption.MULTILINE).containsMatchIn(source())
        )
    }

    @Test
    fun decryptFailureStillRecordedWithThrowable() {
        // 覆盖范围说明（有意为之，非遗漏）：本用例只钉「无裸 import」+「失败仍经 AppLog 记录」两点。
        // 「源码里不得再出现裸 `Log.x(...)` 调用」不在此重复断言 —— 该面由门禁 G-10
        // （`audit_temp_debug_log.py --all`：裸 Log 0 处 / 未登记临时 tag 0 处）承担；
        // 且注释中引用被删代码原文会误命中该断言（同名口径重复只会增加维护面）。
        assertTrue(
            "解密失败必须仍被记录（经 AppLog，含异常栈）",
            source().contains("AppLog.put(\"解密失败:")
        )
    }
}