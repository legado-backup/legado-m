package io.legado.app.ui

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 回归防线（2026-09-28，用户报障「书源编辑页 基本/搜索/发现… 下的编辑项全部没有了」）。
 *
 * **失效模式**：程序化创建 `RecyclerView` 却漏装 `layoutManager` ⇒ 列表项**全部不渲染**，
 * 且无异常、无日志（静默失效），编译与既有单测全绿也照样逃逸。
 *
 * **真实根因**：`activity_book_source_edit.xml`（CE-a #12，2026-09-26 退役）的 `RecyclerView`
 * 声明了 `app:layoutManager="androidx.recyclerview.widget.LinearLayoutManager"` 作为**永久兜底**；
 * 程序化重建（[BookSourceEditShellViews]）丢弃了该属性，而宿主只在 `editEntityMaxLine < 999`
 * 分支内装配 ⇒ `AppConfig.sourceEditMaxLine` 默认 `Int.MAX_VALUE`（≥999）时分支不成立 ⇒ 无布局管理器 ⇒ 六 Tab 编辑项全消失。
 *
 * 本测试对**全体程序化 RecyclerView**（源码全量扫描）做单源不变量校验，防同类缺陷再逃逸：
 *  ① 自建 RecyclerView 的文件（非装配壳）必须自行装配 `layoutManager`；
 *  ② 「装配壳」（RecyclerView 由壳创建、宿主装配）登记表中的每个宿主必须装配 `layoutManager`；
 *  ③ 登记表不得过期：登记的壳自身**不得**装配 `layoutManager`（否则登记表失真）。
 */
class ProgrammaticRecyclerViewLayoutManagerGuardTest {

    /** 壳 → 宿主（相对 `io/legado/app/`）。壳只建 RecyclerView，`layoutManager` 由宿主**无条件**装配。新增壳必须登记。 */
    private val shellToHosts = mapOf(
        "ui/book/source/edit/BookSourceEditShellViews.kt" to listOf(
            "ui/book/source/edit/BookSourceEditActivity.kt",
        ),
        "ui/book/read/config/ThemeManageShellViews.kt" to listOf(
            "ui/book/read/config/AiReadAloudUsageRecordActivity.kt",
            "ui/book/read/config/ParagraphRuleManageActivity.kt",
            "ui/book/read/config/ReadAloudBgmManageActivity.kt",
            "ui/book/read/config/ReadMenuButtonManageActivity.kt",
        ),
    )

    /** 扫描全部 `app/src/main/java` 源码，返回「程序化创建 RecyclerView」的文件（相对 `io/legado/app/`）→ 剥注释源码。 */
    private fun programmaticCreatorFiles(): Map<String, String> {
        // 只认构造调用 `RecyclerView(this|context)`：负向后瞻排除 `attachRecyclerView(this)` 之类的子串误报
        val ctor = Regex("""(?<![\w.])RecyclerView\((?:this|context)\)""")
        val root: File = SourceFileProbe.mainJavaRoot()
        return root.walkTopDown()
            .filter { it.isFile && it.extension == "kt" }
            .mapNotNull { file ->
                val relFromApp = file.toRelativeString(root).replace('\\', '/')
                    .removePrefix("io/legado/app/")
                val code = SourceFileProbe.stripComments(file.readText())
                if (ctor.containsMatchIn(code)) relFromApp to code else null
            }
            .toMap()
    }

    @Test
    fun everyProgrammaticRecyclerViewGetsALayoutManager() {
        val creators = programmaticCreatorFiles()
        assertTrue("探针失效：未扫描到任何程序化 RecyclerView 创建点", creators.isNotEmpty())
        // 登记表不得过期：登记的非壳/壳键必须都真在创建点集合内
        assertTrue(
            "登记表过期：登记壳未在创建点集合内（壳=${shellToHosts.keys}，实际=$creators.keys）",
            creators.keys.containsAll(shellToHosts.keys)
        )
        // 非装配壳（自建自用）必须自行装配 layoutManager
        creators.forEach { (rel, code) ->
            if (rel in shellToHosts.keys) return@forEach
            assertTrue(
                "程序化 RecyclerView 文件必须自行装配 layoutManager，否则列表项全部静默不渲染：$rel",
                code.contains("layoutManager")
            )
        }
    }

    @Test
    fun shellsDelegateLayoutManagerToDeclaredHosts() {
        shellToHosts.forEach { (shellRel, hosts) ->
            val shellCode = SourceFileProbe.sourceText(shellRel)
            assertTrue("壳必须确实创建 RecyclerView：$shellRel", shellCode.contains("RecyclerView("))
            assertTrue(
                "壳自身不得装配 layoutManager（否则登记表失真，须从登记表移除）：$shellRel",
                !shellCode.contains("layoutManager")
            )
            hosts.forEach { hostRel ->
                val hostCode = SourceFileProbe.sourceText(hostRel)
                assertTrue(
                    "宿主必须无条件装配 layoutManager（否则默认配置下列表项全部不渲染）：$hostRel",
                    hostCode.contains(".layoutManager =")
                )
            }
        }
    }
}
