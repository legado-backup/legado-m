package io.legado.app.web.mcp.tools

import io.legado.app.service.kernel.JsSourceKernel
import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_SOURCE
import io.legado.app.web.mcp.McpJsonSchema
import io.legado.app.web.mcp.McpJsonSchema.TYPE_INTEGER
import io.legado.app.web.mcp.McpJsonSchema.TYPE_STRING
import io.legado.app.web.mcp.McpTool

/**
 * 单文件 JS 书源域工具（ng-js-source-port）。
 *
 * 与声明式书源工具的边界：脚本正文属**凭据级内容**，统一要求 MANAGE；
 * 落库走 [JsSourceKernel.save]（串行锁 + 1 MiB 门禁）并触发端侧确认闸门；
 * 调试的覆盖脚本只本次生效，不落库。
 */
object JsSourceTools {

    val tools: List<McpTool> = listOf(
        McpTool(
            name = "js_source_validate",
            title = "校验 JS 书源脚本",
            description = "校验单文件 JS 书源脚本：执行脚本读取顶层 config，检查必备函数与外置库，返回结构化摘要" +
                "（url/name/type/hasExplore/hasLogin/scriptLength/jsLibKind）。**不落库**。",
            domain = MCP_DOMAIN_SOURCE,
            level = TokenManager.Level.MANAGE,
            inputSchema = McpJsonSchema.of(
                required = mapOf("script" to TYPE_STRING),
                optional = mapOf("jsLib" to TYPE_STRING),
                descriptions = mapOf(
                    "script" to "完整 JS 脚本正文（≤1 MiB）",
                    "jsLib" to "外部 jsLib 资源包（可选；原书源已有 jsLib 时用于解析引用）",
                )
            ),
        ) { args ->
            JsSourceKernel.validate(args.requireStr("script"), args.str("jsLib"))
        },

        McpTool(
            name = "js_source_save",
            title = "保存 JS 书源",
            description = "校验并**落库**单文件 JS 书源（同 URL 覆盖）。写操作需端侧确认；返回书源摘要。",
            domain = MCP_DOMAIN_SOURCE,
            level = TokenManager.Level.MANAGE,
            dangerous = true,
            inputSchema = McpJsonSchema.of(
                required = mapOf("script" to TYPE_STRING),
                optional = mapOf("openedSourceUrl" to TYPE_STRING),
                descriptions = mapOf(
                    "script" to "完整 JS 脚本正文（≤1 MiB）",
                    "openedSourceUrl" to "编辑中的原书源 URL（改名保存时用于清理旧源）",
                )
            ),
        ) { args ->
            JsSourceKernel.save(args.requireStr("script"), args.str("openedSourceUrl"))
        },

        McpTool(
            name = "js_source_export",
            title = "导出 JS 书源脚本",
            description = "导出书源脚本正文预览（超 20000 字符截断并给出 truncated）。要求 MANAGE（脚本属凭据级内容）。需要完整脚本时请用书源备份或 Web 控制台的脚本编辑入口。",
            domain = MCP_DOMAIN_SOURCE,
            level = TokenManager.Level.MANAGE,
            inputSchema = McpJsonSchema.of(
                required = mapOf("url" to TYPE_STRING),
                descriptions = mapOf("url" to "书源地址（bookSourceUrl）")
            ),
        ) { args ->
            JsSourceKernel.export(args.requireStr("url"))
        },

        McpTool(
            name = "js_source_debug",
            title = "调试 JS 书源链路",
            description = "按链路调试 JS 书源：chain=search/explore/info/toc/content。" +
                "可传 script 覆盖本次脚本（不落库）。返回链路结果 JSON（超 20000 字符截断）。" +
                "长链路可用 async=true 转为异步任务（返回 taskId，用 task_result 轮询）。",
            domain = MCP_DOMAIN_SOURCE,
            level = TokenManager.Level.MANAGE,
            // AD-11：链路调试要做多次网络往返，站点抗压时单请求可达 20s ⇒ 必须覆盖 15s 默认
            timeoutMs = 90_000L,
            asyncEligible = true,
            inputSchema = McpJsonSchema.of(
                required = mapOf("url" to TYPE_STRING, "chain" to TYPE_STRING),
                optional = mapOf(
                    "key" to TYPE_STRING,
                    "page" to TYPE_INTEGER,
                    "exploreUrl" to TYPE_STRING,
                    "bookUrl" to TYPE_STRING,
                    "tocUrl" to TYPE_STRING,
                    "chapterUrl" to TYPE_STRING,
                    "chapterTitle" to TYPE_STRING,
                    "nextChapterUrl" to TYPE_STRING,
                    "script" to TYPE_STRING,
                ),
                descriptions = mapOf(
                    "url" to "书源地址（bookSourceUrl）",
                    "chain" to "search / explore / info / toc / content",
                    "key" to "search 关键字",
                    "page" to "页码（默认 1）",
                    "exploreUrl" to "explore 分类页地址",
                    "bookUrl" to "书籍详情/目录/正文所需的书籍地址",
                    "tocUrl" to "目录地址（缺省用 bookUrl）",
                    "chapterUrl" to "content 章节地址",
                    "chapterTitle" to "content 章节标题",
                    "nextChapterUrl" to "content 下一章地址（可选）",
                    "script" to "本次调试覆盖脚本（不落库）",
                )
            ),
        ) { args ->
            JsSourceKernel.debug(
                sourceUrl = args.requireStr("url"),
                chain = args.requireStr("chain"),
                params = mapOf(
                    "key" to args.str("key").orEmpty(),
                    "page" to args.int("page", 1).toString(),
                    "url" to args.str("exploreUrl").orEmpty(),
                    "bookUrl" to args.str("bookUrl").orEmpty(),
                    "tocUrl" to args.str("tocUrl").orEmpty(),
                    "chapterUrl" to args.str("chapterUrl").orEmpty(),
                    "chapterTitle" to args.str("chapterTitle").orEmpty(),
                    "nextChapterUrl" to args.str("nextChapterUrl").orEmpty(),
                ),
                scriptOverride = args.str("script"),
            )
        },
    )
}
