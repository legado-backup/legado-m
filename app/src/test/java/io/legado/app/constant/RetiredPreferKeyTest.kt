package io.legado.app.constant

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 已删配置键的**退役不变量**（2026-09-27 用户裁决：删除底栏悬浮搜索按钮）。
 *
 * 删除一个 pref 键涉及三处，漏任一处都会留下隐患：
 * ① `PreferKey` 声明（漏删 ⇒ 死键）
 * ② `BackupConfig.ignorePrefKeys`（漏删 ⇒ **旧备份把已删键写回**）
 * ③ 消费点（漏删 ⇒ 编译期报错，属可见错误）
 */
class RetiredPreferKeyTest {

    private fun read(rel: String): String =
        listOf(File(rel), File("../app/$rel"), File("app/$rel")).first { it.isFile }.readText()

    private val preferKey by lazy { read("src/main/java/io/legado/app/constant/PreferKey.kt") }
    private val backupConfig by lazy {
        read("src/main/java/io/legado/app/help/storage/BackupConfig.kt")
    }

    @Test
    fun removedKeyIsNoLongerDeclared() {
        assertFalse(
            "已删键仍声明在 PreferKey（成为死键）",
            preferKey.contains("const val floatingBottomBarHideSearch")
        )
    }

    @Test
    fun removedKeyIsIgnoredOnRestore() {
        assertTrue(
            "旧备份中的已删键必须纳入 ignorePrefKeys（防写回）",
            backupConfig.contains("\"floatingBottomBarHideSearch\"")
        )
    }

    @Test
    fun rssAutoVideoKeyNameIsFixedByDesign() {
        // design §9.2#2 明确「键名必须为 rssAutoVideoToPlayer，禁止改键名」⇒ 防重命名漂移
        assertTrue(
            "键名须严格为 rssAutoVideoToPlayer",
            preferKey.contains("""const val rssAutoVideoToPlayer = "rssAutoVideoToPlayer"""")
        )
    }

    @Test
    fun ignorePrefKeysIsAStringArrayOnKeyIsNotIgnorePath() {
        // 结构不变量：忽略清单必须是 keyIsNotIgnore 的首条判定（顺序对才生效）
        val body = backupConfig.substringAfter("fun keyIsNotIgnore")
        assertTrue(
            "ignorePrefKeys 必须是 keyIsNotIgnore 的首条判定",
            body.indexOf("ignorePrefKeys.contains(key)") in 1..200
        )
        assertTrue("忽略清单须为字符串数组", backupConfig.contains("private val ignorePrefKeys = arrayOf("))
    }

    @Test
    fun deadKeysFromSweepAreFullyRetired() {
        // 2026-10-15 死件普查（扩大测试基准第三轮）：两键**全仓零读取**（代码引用与字面量通道皆无）
        // ⇒ 按本测试类 KDoc 的「删键三处」约定处置：删声明 + 纳入 ignorePrefKeys + 无消费点
        listOf(
            "downloadDismissedIds", "highlightRuleBuiltinMergedV2",
            // NEW-52（2026-10-16）：「设置项形同虚设」审计（audit_prefer_key_consumption）命中 ——
            // 两项功能已迁移（清除缓存并入缓存管理 / WebView 清理为缓存管理第 4 分项），旧处理逻辑
            // 与 XML 条目均已删；XML 另一侧由下方 `xmlDeadEntriesStayRemoved` 独立守护。
            "cleanCache", "clearWebViewData"
        ).forEach { key ->
            assertFalse(
                "已删键仍声明在 PreferKey（成为死键）：$key",
                preferKey.contains("const val $key =")
            )
            assertTrue(
                "旧备份中的已删键必须纳入 ignorePrefKeys（防写回）：$key",
                backupConfig.contains("\"$key\"")
            )
        }
    }

    @Test
    fun ghostSettingReplyFollowChainFullyRetired() {
        // NEW-87 第二部分（2026-10-16）：「回复栏跟随圆角」幽灵设置 —— 键有 UI / 有存储 / 有引用，
        // 但开关**无可感效果**（唯一功能消费点 `UiCorner.replyRadius` 零调用、仓内无「回复栏」视图，
        // 上游 Archive 亦零消费）⇒ 按「删键三处」约定整体退役（日/夜两键一并）。
        listOf("uiCornerReplyFollow", "uiCornerReplyFollowNight").forEach { key ->
            assertFalse(
                "已退役的幽灵设置键仍声明在 PreferKey：$key",
                Regex("""const val $key =""").containsMatchIn(preferKey)
            )
            assertTrue(
                "旧备份中的幽灵设置键必须纳入 ignorePrefKeys（防写回）：$key",
                backupConfig.contains("\"$key\"")
            )
        }
    }

    @Test
    fun xmlDeadEntriesStayRemoved() {
        // NEW-52：XML 片段（页面已 Compose 化、不再渲染该 XML）仍被 `MySettingsData` 的
        // `buildPreferenceXmlSearchItems` 解析为**搜索项** ⇒ XML 里残留的已迁移条目会变成
        // 「搜得到、点进去却没有」的**幽灵项**。故退役键必须同时从 XML 移除（本断言防回潮）。
        val xml = read("src/main/res/xml/pref_config_other.xml")
        listOf("cleanCache", "clearWebViewData").forEach { key ->
            assertFalse(
                "已退役键不得残留在 XML 偏好片段（会生成幽灵搜索项）：$key",
                xml.contains("android:key=\"$key\"")
            )
        }
    }

    @Test
    fun deadResourceStringsStayRemoved() {
        // NEW-91（2026-10-16）：`audit_dead_resource.py` 零引用扫描命中 ——
        // `clear_cache_summary` / `clear_webview_data`(+`_summary`) 是 NEW-52 迁移（清除缓存并入缓存管理）
        // 的**字符串残留**（当时只删了 pref 键与 XML 条目）；`folder_view` 属历史遗留。四者全仓零消费 ⇒ 退役。
        // NEW-99（2026-10-17）：`clear_cache_title` 与上者**同族残留**（同一次缓存管理迁移；仅 values-zh 有定义）
        // ⇒ 经 `apply_dead_resource_cleanup.py`（地面真值门通过：名字未在任何未剥离源码中出现）退役。
        listOf(
            "src/main/res/values/strings.xml",
            "src/main/res/values-zh/strings.xml"
        ).forEach { rel ->
            val res = read(rel)
            listOf("clear_cache_summary", "clear_cache_title", "clear_webview_data", "folder_view").forEach { name ->
                assertFalse(
                    "已退役字符串不得回流：$rel / $name",
                    Regex("""name="$name"""").containsMatchIn(res)
                )
            }
        }
    }

    /**
     * 2026-10-17（批 11）：**「与代码标识符 / 更长键撞名」的 6 个死字符串**退役不变量。
     *
     * 这 6 个键的名字被更长的键（如 `rss_source_empty_title`）或 Kotlin 常量
     * （`SourceGroupCover.KEY_TYPE_TEXT = "type_text"`）**包含** ⇒ `apply_dead_resource_cleanup.py`
     * 的**地面真值门**（名字出现在未剥离源码即保守不删）会拦下它们。本轮逐条取证：
     * `@string/<key>` 与 `R.string.<key>` 全仓 **0 命中** ⇒ 以人工确证清单 + `--force` 退役。
     */
    @Test
    fun collisionNamedDeadStringsStayRemoved() {
        val targets = mapOf(
            "src/main/res/values/strings.xml" to listOf(
                "rss_source", "share_note_template", "type_audio", "type_file", "type_text", "video_play"
            ),
            "src/main/res/values-zh/strings.xml" to listOf(
                "type_audio", "type_file", "type_text", "video_play"
            ),
            "src/main/res/values-zh-rTW/strings.xml" to listOf("rss_source"),
            "src/main/res/values-zh-rHK/strings.xml" to listOf("rss_source"),
            "src/main/res/values-es-rES/strings.xml" to listOf("rss_source"),
            "src/main/res/values-ja-rJP/strings.xml" to listOf("rss_source"),
            "src/main/res/values-pt-rBR/strings.xml" to listOf("rss_source"),
            "src/main/res/values-vi/strings.xml" to listOf("rss_source"),
        )
        targets.forEach { (rel, names) ->
            val res = read(rel)
            names.forEach { name ->
                assertFalse("已退役字符串不得回流：$rel / $name", res.contains("name=\"$name\""))
            }
        }
        // 防误删**邻居**：同族更长的键必须健在（地面真值门保守口径的正向价值）
        assertTrue(
            "同族键 rss_source_empty_title 必须保留",
            read("src/main/res/values-zh/strings.xml").contains("name=\"rss_source_empty_title\"")
        )
        assertTrue(
            "同族键 share_note_template_manage 必须保留",
            read("src/main/res/values/strings.xml").contains("name=\"share_note_template_manage\"")
        )
        assertTrue(
            "Kotlin 常量面（SourceGroupCover 键常量）不属资源退役范围，必须保留",
            read("src/main/java/io/legado/app/data/entities/SourceGroupCover.kt")
                .contains("KEY_TYPE_TEXT = \"type_text\"")
        )
    }
}