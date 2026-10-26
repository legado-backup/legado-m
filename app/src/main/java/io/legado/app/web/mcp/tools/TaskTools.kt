package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_DIAG
import io.legado.app.web.mcp.McpArgs
import io.legado.app.web.mcp.McpJsonSchema
import io.legado.app.web.mcp.McpTaskRegistry
import io.legado.app.web.mcp.McpTool

/**
 * 长任务查询工具（design AD-11 / spec Requirement A-6）。
 *
 * 用途：长工具（五链调试 / 取流验证 / 质量报告）可用 `async=true` 提交为后台任务，
 * 本工具按 `taskId` **轮询**取结果 ⇒ 不再让调用方在同步超时上反复失败。
 *
 * 级别 `MANAGE`（与长工具同级：能看到长任务结果就等于能看到这些工具的输出）。
 * **`readOnlyHint` 显式 false**：工具本身无副作用，但按本项目「宁严不宽」口径，
 * 只有 `READONLY` 级工具才向 AI 声明只读安全（`McpToolCatalogTest` 已把该不变量锁死）。
 */
object TaskTools {

    val tools: List<McpTool> = listOf(
        McpTool(
            name = "task_result",
            title = "查询长任务结果",
            description = "按 taskId 查询异步长任务的状态与结果。" +
                "state=running 表示仍在执行（稍后重试）；done=成功；failed 时 result 内含 error/errorKind。" +
                "taskId 来自以 async=true 调用长工具时返回的 data.taskId。",
            domain = MCP_DOMAIN_DIAG,
            level = TokenManager.Level.MANAGE,
            readOnlyHint = false,
            inputSchema = McpJsonSchema.singleRequiredString(
                "taskId", "异步任务 id（形如 task-xxxxxxxx，来自长工具 async=true 的返回）"
            ),
            invoke = { args: McpArgs ->
                val id = args.requireStr("taskId")
                val entry = McpTaskRegistry.status(id)
                if (entry == null) {
                    mapOf(
                        "taskId" to id,
                        "state" to "unknown",
                        "hint" to "任务不存在或已被淘汰（最多保留最近 ${McpTaskRegistry.MAX_ENTRIES} 条）",
                    )
                } else {
                    mapOf(
                        "taskId" to entry.id,
                        "tool" to entry.tool,
                        "state" to entry.state.name.lowercase(),
                        "startedAt" to entry.startedAt,
                        "finishedAt" to entry.finishedAt,
                        "result" to entry.result,
                    )
                }
            },
        ),
    )
}
