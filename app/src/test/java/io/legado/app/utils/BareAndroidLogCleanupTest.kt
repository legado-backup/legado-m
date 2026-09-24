package io.legado.app.utils

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * G-10 存量清偿（2026-09-24）的配对不变量：**裸 `android.util.Log` 在业务代码里必须为 0**。
 *
 * 背景（`logging_rules.md` 条款六）：日志载体（`AppLog` / `DebugLog` / `LogUtils` / `Debug`）
 * 是唯一允许携带 `android.util.Log` 的位置；业务代码一律经 `AppLog.put` /
 * `AppLog.putDebugWithTag`（后者可指定登记 TAG 以保留 logcat 采集 tag）。
 *
 * 本文件覆盖 `utils/` 域（`ImageUtils`）：裸 `Log.e("ImgDecrypt", …)`
 * → `AppLog.putDebugWithTag(TAG_IMG_DECRYPT, …)`（**logcat tag 逐字不变**，
 * `TAG_IMG_DECRYPT` 值即 `"ImgDecrypt"`，被真机异常分析文档引用）。
 * `help/crypto/` 域的对应断言见 `help/crypto/SymmetricCryptoLogComplianceTest`（同批清偿）。
 *
 * 判定方式对齐门禁口径：以 `^import android.util.Log$` **定性**（防 `DebugLog`/`LogUtils` 子串误报）。
 */
class BareAndroidLogCleanupTest {

    private fun mainJava(relFromMainJava: String): String {
        val rel = "src/main/java/io/legado/app/$relFromMainJava"
        val file = listOf(File(rel), File("../app/$rel"), File("app/$rel")).firstOrNull { it.isFile }
            ?: throw AssertionError("未找到源文件（工作目录=${File(".").absolutePath}）：$rel")
        return file.readText()
    }

    @Test
    fun imageUtils_hasNoBareAndroidLog_andKeepsImgDecryptTag() {
        val src = mainJava("utils/ImageUtils.kt")
        assertFalse(
            "不得再出现裸 `import android.util.Log`",
            Regex("^import android\\.util\\.Log$", RegexOption.MULTILINE).containsMatchIn(src)
        )
        assertFalse("删除裸 Log 后不得残留无引用私有 TAG 常量", src.contains("private const val TAG ="))
        assertTrue(
            "图片解密失败必须保留 ImgDecrypt 采集 tag（经登记 TAG 常量，非字面量）",
            src.contains("AppLog.putDebugWithTag(") && src.contains("AppLog.TAG_IMG_DECRYPT")
        )
        assertFalse(
            "不得回退为字面量 tag（登记常量单源口径）",
            src.contains("putDebugWithTag(\"ImgDecrypt\"")
        )
    }

    /** 采集 tag 值不得被改（真机分析文档按 `ImgDecrypt` 过滤）。 */
    @Test
    fun imgDecryptTagConstantValueIsStable() {
        val appLog = mainJava("constant/AppLog.kt")
        assertTrue(
            "TAG_IMG_DECRYPT 的值必须仍为 \"ImgDecrypt\"（采集口径不可变）",
            Regex("""TAG_IMG_DECRYPT\s*=\s*"ImgDecrypt"""").containsMatchIn(appLog)
        )
    }
}