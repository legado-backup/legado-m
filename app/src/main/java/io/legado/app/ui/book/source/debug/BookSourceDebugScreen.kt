package io.legado.app.ui.book.source.debug

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.legado.app.model.Debug
import io.legado.app.ui.source.debug.DebugControlPanel
import io.legado.app.ui.source.debug.DebugEmptyState
import io.legado.app.ui.source.debug.DebugEntryCard
import io.legado.app.ui.source.debug.DebugFilter
import io.legado.app.ui.source.debug.DebugLogToolbar
import io.legado.app.ui.source.debug.DebugPhase
import io.legado.app.ui.source.debug.DebugSummaryBar
import io.legado.app.ui.source.debug.debugStatusText
import io.legado.app.ui.source.debug.rememberCopyEntry
import io.legado.app.ui.source.debug.stageLabel
import io.legado.app.ui.source.debug.toEntryUi
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive

/**
 * debug-page-redesign：书源调试页 Compose Screen（对标 MD3阅读）。
 *
 * 2026-10-27 产品化：三段式（控制卡 / 日志工具条 / 卡片列表）+ 阶段徽标 + 摘要置顶 +
 * 失败阶段/建议 + 长按复制 + 全文只读代码页；移除重复 FAB 入口。
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
    onScan: (() -> Unit)? = null,
    onStatusChange: ((DebugPhase, String?) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val events by Debug.events.collectAsState()
    var query by remember { mutableStateOf("") }
    var target by remember { mutableStateOf(BookDebugTarget.SEARCH) }
    var filter by remember { mutableStateOf(DebugFilter.ALL) }
    var phase by remember { mutableStateOf(DebugPhase.IDLE) }
    var elapsedMillis by remember { mutableLongStateOf(0L) }
    val copyEntry = rememberCopyEntry()

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
    // 运行中计时（200ms 刷新，只在工具条显示，避免顶栏高频重组）
    LaunchedEffect(phase) {
        if (phase == DebugPhase.RUNNING) {
            val start = System.currentTimeMillis()
            while (isActive) {
                elapsedMillis = System.currentTimeMillis() - start
                delay(200)
            }
        } else {
            elapsedMillis = entries.lastOrNull()?.elapsedMillis ?: elapsedMillis
        }
    }
    // 顶栏副标题状态上抛（只在阶段/状态变化时触发）
    LaunchedEffect(phase, entries.lastOrNull()?.stage) {
        onStatusChange?.invoke(phase, entries.lastOrNull()?.stage)
    }
    // 自动滚动：只在接近底部时跟随，用户回看历史时不抢滚动
    val listState = rememberLazyListState()
    LaunchedEffect(visibleEntries.size, phase) {
        if (phase == DebugPhase.RUNNING && visibleEntries.isNotEmpty()) {
            val layout = listState.layoutInfo
            val lastVisible = layout.visibleItemsInfo.lastOrNull()?.index ?: -1
            val nearBottom = lastVisible >= layout.totalItemsCount - 2
            if (nearBottom) {
                listState.animateScrollToItem(visibleEntries.lastIndex)
            }
        }
    }

    val running = phase == DebugPhase.RUNNING
    val errorEntry = entries.lastOrNull { it.kind == -1 }
    val currentStage = entries.lastOrNull()?.stage
    val tryPlayUrl = remember(entries) {
        extractTryPlayUrl(entries.map { it.kind to it.message })
    }

    Column(modifier = modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            DebugControlPanel(
                targets = BookDebugTarget.entries.map { it.title },
                selectedTarget = target.ordinal,
                onSelectTarget = { target = BookDebugTarget.entries[it] },
                query = query,
                onQueryChange = { query = it },
                inputHint = target.hint,
                enabled = !running,
                running = running,
                examples = examples.map { it.label to it.value },
                onExampleClick = { value ->
                    examples.firstOrNull { it.value == value }?.let {
                        target = it.target
                        query = it.value
                    }
                },
                onScan = onScan,
                onStart = {
                    if (query.isNotBlank()) {
                        phase = DebugPhase.RUNNING
                        elapsedMillis = 0L
                        onStart(target.buildKey(query))
                    }
                },
                onStop = {
                    phase = DebugPhase.CANCELLED
                    onCancel()
                },
                onFullChain = {
                    if (query.isNotBlank()) {
                        phase = DebugPhase.RUNNING
                        elapsedMillis = 0L
                        onStart(fullChainKey(target, query))
                    }
                },
                tryPlayUrl = tryPlayUrl,
                onTryPlay = { url -> onTryPlay?.invoke(url) },
            )
            DebugLogToolbar(
                visibleCount = visibleEntries.size,
                totalCount = entries.size,
                filter = filter,
                onSelectFilter = { filter = it },
                running = running,
                elapsedMillis = elapsedMillis,
            )
        }
        if (visibleEntries.isEmpty()) {
            DebugEmptyState(running = running, modifier = Modifier.fillMaxSize())
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 12.dp, end = 12.dp, top = 4.dp, bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (phase == DebugPhase.SUCCESS || phase == DebugPhase.FAILED || phase == DebugPhase.CANCELLED) {
                    item(key = "summary") {
                        DebugSummaryBar(
                            phaseKind = when (phase) {
                                DebugPhase.SUCCESS -> 1000
                                DebugPhase.FAILED -> -1
                                else -> 0
                            },
                            stage = currentStage,
                            errorMessage = errorEntry?.message,
                            hint = errorEntry?.stage?.let { stageHint(it) },
                            totalElapsedMillis = entries.lastOrNull()?.elapsedMillis ?: 0L,
                            onShowError = errorEntry?.let {
                                { onShowFull("错误 · ${stageLabel(it.stage)}", it.message) }
                            },
                        )
                    }
                }
                items(visibleEntries, key = { it.id }) { entry ->
                    DebugEntryCard(
                        entry = entry,
                        kindTitle = kindTitle(entry.kind),
                        onClick = { onShowFull(kindTitle(entry.kind), entry.message) },
                        onLongClick = { copyEntry(entry.message) },
                    )
                }
            }
        }
    }
}

/** App 摘要建议：与 MCP 失败信封共用同一份阶段建议。 */
private fun stageHint(stage: String): String =
    io.legado.app.service.kernel.SourceStepTracer.hintForStep(stage)

@Suppress("unused")
private val unusedSourceNameHint = "源名由顶栏显示"
