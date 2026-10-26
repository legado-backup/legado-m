package io.legado.app.ui.book.source.debug

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.legado.app.model.Debug
import io.legado.app.ui.source.debug.DebugEntryCard
import io.legado.app.ui.source.debug.DebugFilter
import io.legado.app.ui.source.debug.DebugFilterChips
import io.legado.app.ui.source.debug.DebugSummaryBar
import io.legado.app.ui.source.debug.DebugChipRow
import io.legado.app.ui.source.debug.toEntryUi
import io.legado.app.ui.widget.components.EmptyStatePlaceholder
import io.legado.app.ui.widget.compose.rememberAppSettingPalette

/**
 * debug-page-redesign：书源调试页 Compose Screen（对标 MD3阅读）。
 * 目标 Chips 替代魔法前缀（++/--/::），过滤 Chips + 着色卡片 + 耗时/时间戳 + 点击全文 + FAB 启停。
 * 状态机：Idle → Running →(错误 -1) Failed / (完成 1000) Success / (用户停止) Cancelled。
 */

/** 调试目标（key 拼装规则见 [buildKey]；魔法前缀只出现在此边界，AD-04） */
enum class BookDebugTarget(val title: String, val hint: String) {
    SEARCH("搜索", "搜索关键字"),
    EXPLORE("发现", "发现 URL"),
    INFO("详情", "详情页 URL"),
    TOC("目录", "目录页 URL"),
    CONTENT("正文", "正文页 URL"),
}

/** 示例快捷项（checkKeyWord/我的/系统/发现分类） */
data class DebugExample(val label: String, val target: BookDebugTarget, val value: String)

private enum class DebugPhase { IDLE, RUNNING, FAILED, SUCCESS, CANCELLED }

private fun BookDebugTarget.buildKey(query: String): String = when (this) {
    BookDebugTarget.SEARCH -> query
    // Debug.startDebug 约定：contains("::") → 发现页（name::url），name 仅用于展示
    BookDebugTarget.EXPLORE -> "发现::${query.removePrefix("发现::")}"
    BookDebugTarget.INFO -> query
    BookDebugTarget.TOC -> "++${query.removePrefix("++")}"
    BookDebugTarget.CONTENT -> "--${query.removePrefix("--")}"
}

/**
 * 「一键跑全链」的键（A-4 / AD-02）：串跑 search/explore → 详情 → 目录 → 正文。
 *
 * 与逐链的差别只在**起点**：目录/正文档若直接从该链跑，只会跑一段；
 * 全链一律从**最上游**开始（URL 走详情 = 详情→目录→正文；关键字走搜索）⇒ 一次点完即全链。
 * 纯函数，便于单测锁定。
 */
internal fun fullChainKey(target: BookDebugTarget, query: String): String {
    val raw = query.removePrefix("发现::").removePrefix("++").removePrefix("--")
    return when (target) {
        BookDebugTarget.SEARCH -> query
        BookDebugTarget.EXPLORE -> "发现::$raw"
        // 详情/目录/正文都从详情起点跑（Debug 会自动依次进入 详情→目录→正文）
        BookDebugTarget.INFO, BookDebugTarget.TOC, BookDebugTarget.CONTENT -> raw
    }
}

/**
 * 从调试事件里取出「可试播的正文地址」（A-5）。
 *
 * 口径：取**最后一条**正文响应（kind=40）文本中的首个 http(s) 地址；
 * 取不到返回 `null`（此时不显示试播入口，避免点了没反应）。
 * 纯函数，便于单测锁定。
 */
internal fun extractTryPlayUrl(entries: List<Pair<Int, String>>): String? {
    val text = entries.lastOrNull { it.first == 40 }?.second ?: return null
    val match = Regex("""https?://[^\s"'<>\\]+""").find(text) ?: return null
    // 同时清理半角与全角句读（日志里地址常紧跟中文标点，带标点会让播放器拿到坏地址）
    return match.value.trimEnd('.', ',', ';', ')', ']', '。', '，', '；', '）', '】', '、')
}

private fun kindTitle(kind: Int): String = when (kind) {
    -1 -> "错误"
    10 -> "搜索/发现响应"
    20 -> "详情响应"
    30 -> "目录响应"
    40 -> "正文响应"
    1000 -> "完成"
    else -> "过程"
}

@Composable
fun BookSourceDebugScreen(
    sourceName: String,
    examples: List<DebugExample>,
    onStart: (String) -> Unit,
    onCancel: () -> Unit,
    onShowFull: (String, String) -> Unit,
    onTryPlay: ((String) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val events by Debug.events.collectAsState()
    var query by remember { mutableStateOf("") }
    var target by remember { mutableStateOf(BookDebugTarget.SEARCH) }
    var filter by remember { mutableStateOf(DebugFilter.ALL) }
    var phase by remember { mutableStateOf(DebugPhase.IDLE) }

    val entries = remember(events) {
        events.mapIndexed { index, event -> event.toEntryUi(index.toLong()) }
    }
    val visibleEntries = remember(entries, filter) {
        entries.filter { filter.matches(it.kind) }
    }

    // 终态驱动：错误/完成事件到达时收敛状态机
    LaunchedEffect(events.size) {
        val last = events.lastOrNull() ?: return@LaunchedEffect
        if (phase == DebugPhase.RUNNING) {
            when (last.kind) {
                -1 -> phase = DebugPhase.FAILED
                1000 -> phase = DebugPhase.SUCCESS
            }
        }
    }
    // 自动滚动到底（仅 Running，学 MD3）
    val listState = rememberLazyListState()
    LaunchedEffect(visibleEntries.size, phase) {
        if (phase == DebugPhase.RUNNING && visibleEntries.isNotEmpty()) {
            listState.animateScrollToItem(visibleEntries.lastIndex)
        }
    }

    Box(modifier = modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            // 控件卡：源名 + 目标 Chips + 输入 + 示例 Chips + 过滤 Chips
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    sourceName,
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                )
                DebugChipRow {
                    items(BookDebugTarget.entries, key = { it.name }) { t ->
                        FilterChip(
                            selected = target == t,
                            onClick = { target = t },
                            label = { Text(t.title) },
                        )
                    }
                }
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    label = { Text(target.hint) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = phase != DebugPhase.RUNNING,
                    maxLines = 3,
                )
                if (examples.isNotEmpty()) {
                    DebugChipRow {
                        items(examples, key = { "${it.target.name}:${it.value}" }) { example ->
                            FilterChip(
                                selected = target == example.target && query == example.value,
                                onClick = {
                                    target = example.target
                                    query = example.value
                                },
                                label = { Text(example.label) },
                            )
                        }
                    }
                }
                DebugFilterChips(selected = filter, onSelect = { filter = it })
                // A-4：一键跑全链（与逐链共用同一套 Debug 实现，只是从最上游起点串跑）
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    if (onTryPlay != null) {
                        val tryPlayUrl = remember(entries) {
                            extractTryPlayUrl(entries.map { it.kind to it.message })
                        }
                        if (tryPlayUrl != null) {
                            // A-5：调试结论旁提供试播，把「调试说成功」与「真机能不能播」对齐
                            TextButton(onClick = { onTryPlay(tryPlayUrl) }) {
                                Text("在播放器中试播该集")
                            }
                        }
                    }
                    Spacer(Modifier.weight(1f))
                    TextButton(
                        enabled = phase != DebugPhase.RUNNING && query.isNotBlank(),
                        onClick = {
                            if (query.isBlank()) return@TextButton
                            phase = DebugPhase.RUNNING
                            onStart(fullChainKey(target, query))
                        },
                    ) {
                        Text("一键跑全链")
                    }
                }
            }

            if (visibleEntries.isEmpty()) {
                EmptyStatePlaceholder(
                    icon = Icons.AutoMirrored.Filled.MenuBook,
                    title = if (phase == DebugPhase.RUNNING) "等待调试日志…" else "输入内容并开始调试",
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(
                        start = 16.dp, end = 16.dp,
                        top = 4.dp, bottom = 96.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    // F65 调试结论条：把「判断是否通过」从读完所有日志降为看一行结论，
                    // 总耗时 = 末事件相对耗时（数据现成，纯展示层）
                    if (phase == DebugPhase.SUCCESS || phase == DebugPhase.FAILED || phase == DebugPhase.CANCELLED) {
                        item(key = "summary") {
                            DebugSummaryBar(
                                // 复用事件 kind 语义：1000=完成 / -1=失败 / 其余=取消
                                phaseKind = when (phase) {
                                    DebugPhase.SUCCESS -> 1000
                                    DebugPhase.FAILED -> -1
                                    else -> 0
                                },
                                errorMessage = entries.firstOrNull { it.kind == -1 }?.message,
                                totalElapsedMillis = entries.lastOrNull()?.elapsedMillis ?: 0L,
                            )
                        }
                    }
                    items(visibleEntries, key = { it.id }) { entry ->
                        DebugEntryCard(
                            entry = entry,
                            kindTitle = kindTitle(entry.kind),
                            onClick = { onShowFull(kindTitle(entry.kind), entry.message) },
                        )
                    }
                }
            }
        }

        // FAB：开始/停止（学 MD3；Running 时可中途取消，已产出日志保留可导出）
        // 取色基线归位（2026-09-13）：accent 底 + onAccent 图标；运行中停止=语义红
        val fabPalette = rememberAppSettingPalette()
        FloatingActionButton(
            onClick = {
                when (phase) {
                    DebugPhase.RUNNING -> {
                        phase = DebugPhase.CANCELLED
                        onCancel()
                    }
                    else -> {
                        if (query.isBlank()) return@FloatingActionButton
                        phase = DebugPhase.RUNNING
                        onStart(target.buildKey(query))
                    }
                }
            },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(16.dp),
            containerColor = if (phase == DebugPhase.RUNNING) fabPalette.danger else fabPalette.accent,
            contentColor = fabPalette.onAccent,
        ) {
            Icon(
                imageVector = if (phase == DebugPhase.RUNNING) Icons.Default.Stop else Icons.Default.PlayArrow,
                contentDescription = if (phase == DebugPhase.RUNNING) "停止" else "开始调试",
            )
        }
    }
}
