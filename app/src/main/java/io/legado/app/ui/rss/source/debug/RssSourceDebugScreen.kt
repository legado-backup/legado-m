package io.legado.app.ui.rss.source.debug

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
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
import io.legado.app.ui.source.debug.rememberCopyEntry
import io.legado.app.ui.source.debug.stageLabel
import io.legado.app.ui.source.debug.toEntryUi
import io.legado.app.service.kernel.SourceStepTracer
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive

/**
 * debug-page-redesign：订阅源调试页 Compose Screen（与书源调试页同构）。
 *
 * 2026-10-27 产品化：与书源页共用控制卡/日志工具条/事件卡片/摘要条；移除重复 FAB。
 */

enum class RssDebugTarget(val title: String, val hint: String) {
    CLASSIFY("分类", "分类 key（名称::URL）"),
    SEARCH("搜索", "搜索关键字"),
    CONTENT("内容", "文章 URL"),
}

/** 示例快捷项（分类列表来自 sortUrls） */
data class RssDebugExample(val label: String, val target: RssDebugTarget, val value: String)

private fun RssDebugTarget.buildKey(query: String): String = when (this) {
    // Debug.startDebug(rss) 约定：contains("::") → 分类页；isAbsUrl → 内容页；否则 → 搜索关键字
    RssDebugTarget.CLASSIFY -> query
    RssDebugTarget.SEARCH -> query
    RssDebugTarget.CONTENT -> query
}

private fun kindTitle(kind: Int): String = when (kind) {
    -1 -> "错误"
    10 -> "列表响应"
    20 -> "内容响应"
    1000 -> "完成"
    else -> "过程"
}

@Composable
fun RssSourceDebugScreen(
    sourceName: String,
    examples: List<RssDebugExample>,
    onStart: (String) -> Unit,
    onCancel: () -> Unit,
    onShowFull: (String, String) -> Unit,
    onStatusChange: ((DebugPhase, String?) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val events by Debug.events.collectAsState()
    var query by remember { mutableStateOf("") }
    var target by remember { mutableStateOf(RssDebugTarget.CLASSIFY) }
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

    LaunchedEffect(events.size) {
        val last = events.lastOrNull() ?: return@LaunchedEffect
        if (phase == DebugPhase.RUNNING) {
            when (last.kind) {
                -1 -> phase = DebugPhase.FAILED
                1000 -> phase = DebugPhase.SUCCESS
            }
        }
    }
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
    LaunchedEffect(phase, entries.lastOrNull()?.stage) {
        onStatusChange?.invoke(phase, entries.lastOrNull()?.stage)
    }
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

    Column(modifier = modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            DebugControlPanel(
                targets = RssDebugTarget.entries.map { it.title },
                selectedTarget = target.ordinal,
                onSelectTarget = { target = RssDebugTarget.entries[it] },
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
                onScan = null,
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
                        onStart(target.buildKey(query))
                    }
                },
                tryPlayUrl = null,
                onTryPlay = {},
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
                            hint = errorEntry?.stage?.let { SourceStepTracer.hintForStep(it) },
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
