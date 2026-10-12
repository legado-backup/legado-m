package io.legado.app.testkit

import java.io.File

/**
 * 单测「读源码 / 资源做结构不变量」的**唯一探针单源**（CC-1 提炼，2026-09-24）。
 *
 * 为什么必须提炼：本仓有 **51 个测试文件**各自复写同一段「按候选路径找源文件 + 剥行注释/KDoc 星号行」
 * 的辅助函数（形如 `private fun code(rel: String)` + `listOf(File("src/..."), File("../app/src/..."),
 * File("app/src/...")).firstOrNull { it.isFile }`）。同形态复制会造成两类系统性风险：
 *   ①**路径回退口径漂移**——某个副本漏了 `File("../app/...")` ⇒ 该测试在别的 working dir 下静默抛错/假失败；
 *   ②**剥注释口径漂移**——某个副本只剥 `//` 不剥 `*` ⇒ 注释里的写法制造**假阳性**（本项目已多次实证：
 *   注释里的 `BaseDialogFragment(R.layout.xxx)` / `R.string.xxx` 曾导致误判「在用」）。
 *
 * 登记：`docs/project-flow/ui-standards/component-registry.md` §二（组件名 / 归属 / 取色来源 / 唯一性）。
 * 未迁移的既有副本在 §三「待清偿」逐项登记（**不静默保留**）。
 */
object SourceFileProbe {

    /** Gradle 单测的 working dir 随运行方式变化（module 目录 / 仓库根）⇒ 三候选路径回退。 */
    private fun firstFile(vararg candidates: String): File =
        candidates.map { File(it) }.firstOrNull { it.isFile }
            ?: throw AssertionError(
                "未找到文件（工作目录=${File(".").absolutePath}）：${candidates.joinToString(" | ")}"
            )

    private fun firstDir(vararg candidates: String): File =
        candidates.map { File(it) }.firstOrNull { it.isDirectory }
            ?: throw AssertionError(
                "未找到目录（工作目录=${File(".").absolutePath}）：${candidates.joinToString(" | ")}"
            )

    /** `app/src/main/java` 根目录。 */
    fun mainJavaRoot(): File = firstDir(
        "src/main/java", "../app/src/main/java", "app/src/main/java",
    )

    /** `app/src/main/res/layout` 目录。 */
    fun layoutDir(): File = firstDir(
        "src/main/res/layout", "../app/src/main/res/layout", "app/src/main/res/layout",
    )

    /** 读原始文本（不剥注释）。 */
    fun rawText(relFromMainJava: String): String = firstFile(
        "src/main/java/io/legado/app/$relFromMainJava",
        "../app/src/main/java/io/legado/app/$relFromMainJava",
        "app/src/main/java/io/legado/app/$relFromMainJava",
    ).readText()

    /**
     * `src/main/assets/<relFromAssets>` 原始文本（如 `md/template-runtime.js`）。
     *
     * 为什么单列：被**内联进 HTML 的资产**（如沙箱 `<script>` 里的 JS）必须用**真资产**做
     * 结构不变量断言——合成样例曾掩盖真实缺陷（样例里没有 `<` + `!--` 序列，真资产里有）。
     */
    fun assetRawText(relFromAssets: String): String = firstFile(
        "src/main/assets/$relFromAssets",
        "../app/src/main/assets/$relFromAssets",
        "app/src/main/assets/$relFromAssets",
    ).readText()

    /** `res/values/<name>`（如 `dimens.xml`）原始文本（同上三候选路径回退）。 */
    fun resValuesRawText(name: String): String = firstFile(
        "src/main/res/values/$name",
        "../app/src/main/res/values/$name",
        "app/src/main/res/values/$name",
    ).readText()

    /** `res/values/<name>` 并剥掉 XML 注释（`<!-- -->` 单行形式）。 */
    fun resValuesText(name: String): String =
        resValuesRawText(name).lines().filterNot { it.trimStart().startsWith("<!--") }.joinToString("\n")

    /** 剥掉行注释与 KDoc 星号行（结构不变量测试的强制口径）。 */
    fun stripComments(text: String): String = text.lines()
        .filterNot { it.trimStart().startsWith("//") || it.trimStart().startsWith("*") }
        .joinToString("\n")

    /**
     * 读 `src/main/java/io/legado/app/<relFromMainJava>` 并**剥掉行注释与 KDoc 星号行**。
     *
     * 剥注释是结构不变量测试的**强制口径**：注释里的历史写法（如已注释的 `R.string.xxx`、
     * `ComposeView(...)`）会制造假阳性/假阴性（本项目已多次实证）。
     */
    fun sourceText(relFromMainJava: String): String = stripComments(rawText(relFromMainJava))

    /** 同 [sourceText] 但对任意相对路径（含 `app/src/...` 前缀的自由形式）。 */
    fun sourceTextByPath(relPath: String): String =
        stripComments(firstFile(relPath, "../app/$relPath", "app/$relPath").readText())

    /**
     * `app/build.gradle` 原始文本（不剥注释 —— Groovy 注释与代码同样有意义，且本文件用 `//` 注释）。
     *
     * 为什么单列：构建期契约（如 S9「tiny 档」的资产排除项）落在 `build.gradle`，而该文件**不在**
     * `src/main/java` 下 ⇒ 既有三个入口（`rawText`/`sourceTextByPath` 的 `app/` 前缀回退）都不适配，
     * 各用例再各写一套路径回退又是同形态复制（见本文件头部的 CC-1 教训）。
     */
    fun appBuildGradleText(): String {
        // ⚠️ 不能只按路径回退：仓库根也有 `build.gradle` ⇒ 工作目录=仓库根时 `File("build.gradle")`
        // 会读到**根**构建脚本（内容不符却"找到了文件"，比抛错更隐蔽）⇒ 必须按**内容特征**认。
        val marker = "namespace = 'io.legado.app'"
        return listOf("build.gradle", "../app/build.gradle", "app/build.gradle")
            .map { File(it) }
            .firstOrNull { it.isFile && it.readText().contains(marker) }
            ?.readText()
            ?: throw AssertionError(
                "未找到 app/build.gradle（工作目录=${File(".").absolutePath}）"
            )
    }
}