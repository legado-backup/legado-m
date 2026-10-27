package io.legado.app.ui.source.debug

import android.widget.Toast
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.colorResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.google.gson.GsonBuilder
import com.google.gson.JsonParser
import io.legado.app.R
import io.legado.app.help.CacheManager
import io.legado.app.model.Debug
import io.legado.app.service.kernel.SourceStepTracer
import io.legado.app.ui.code.CodeEditActivity
import io.legado.app.ui.widget.dialog.TextDialog
import io.legado.app.ui.widget.compose.rememberAppSettingPalette
import io.legado.app.utils.showDialogFragment
import io.legado.app.utils.startActivity
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import androidx.fragment.app.FragmentActivity
import androidx.appcompat.app.AppCompatActivity

/**
 * debug-page-redesign：书源/订阅源调试页共享 UI 模型与组件。
 *
 * 2026-10-27 产品化改造：
 * - 共享 [DebugPhase]（两页不再各写一份状态机）；
 * - 控制卡/日志工具条/空态/事件卡片抽出共用；
 * - 事件带阶段徽标、响应类等宽、错误左边条、长按复制；
 * - 调试全文改走只读代码页（不截断 + JSON/HTML 可格式化）。
 */

/** 日志过滤维度（学 MD3 全部/过程/响应/错误四档） */
enum class DebugFilter(val title: String) {
    ALL("全部"),
    MESSAGES("过程"),
    RESPONSES("响应"),
    ERRORS("错误");

    fun matches(kind: Int): Boolean = when (this) {
        ALL -> true
        MESSAGES -> kind == 1 || kind == 1000
        RESPONSES -> kind == 10 || kind == 20 || kind == 30 || kind == 40
        ERRORS -> kind == -1
    }
}

/** 调试状态机（书源/订阅源共享，避免两套枚举漂移） */
enum class DebugPhase { IDLE, RUNNING, FAILED, SUCCESS, CANCELLED }

/** 列表条目 UI 模型（kind 语义见 [Debug.DebugEvent]） */
data class DebugEntryUi(
    val id: Long,
    val kind: Int,
    val message: String,
    val timestamp: Long,
    val elapsedMillis: Long,
    val stage: String?,
)

fun Debug.DebugEvent.toEntryUi(id: Long): DebugEntryUi = DebugEntryUi(
    id = id,
    kind = kind,
    message = message,
    timestamp = timestamp,
    elapsedMillis = elapsedMillis,
    stage = stage,
)

/** 阶段中文名（未知/空回退「准备」）。 */
fun stageLabel(stage: String?): String = when (stage) {
    SourceStepTracer.STEP_SOURCE -> "准备"
    SourceStepTracer.STEP_SEARCH -> "搜索"
    SourceStepTracer.STEP_EXPLORE -> "发现"
    SourceStepTracer.STEP_INFO -> "详情"
    SourceStepTracer.STEP_TOC -> "目录"
    SourceStepTracer.STEP_CONTENT -> "正文"
    SourceStepTracer.STEP_RSS -> "列表"
    else -> "准备"
}

/** 顶栏副标题状态文案（纯函数，便于单测）。 */
fun debugStatusText(phase: DebugPhase, stage: String?): String = when (phase) {
    DebugPhase.IDLE -> "就绪"
    DebugPhase.RUNNING -> "运行中 · ${stageLabel(stage)}"
    DebugPhase.FAILED -> "失败于 ${stageLabel(stage)}"
    DebugPhase.SUCCESS -> "完成"
    DebugPhase.CANCELLED -> "已取消"
}

/** 导出文本渲染：类型标题 + 相对耗时 + 绝对时间戳 + 消息全文（供复制/分享） */
fun List<DebugEntryUi>.buildExportText(kindTitle: (Int) -> String): String =
    joinToString("\n\n") { entry ->
        buildString {
            append("== ${kindTitle(entry.kind)}")
            append(" (+%.3fs)".format(entry.elapsedMillis / 1000.0))
            append(" ")
            append(SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(entry.timestamp)))
            append(" ==\n")
            append(entry.message)
        }
    }

/** JSON 内容自动缩进；非 JSON 原样返回（解析失败不报错）。 */
fun prettyJsonOrOriginal(text: String): String {
    val trimmed = text.trimStart()
    if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return text
    return runCatching {
        val element = JsonParser.parseString(text)
        GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(element)
    }.getOrDefault(text)
}

/**
 * 调试全文查看：打开只读代码页（cacheKey 通道天然 `writable=false`）。
 *
 * - 不应用 `TextDialog` 的 32KB 截断；
 * - JSON 先自动 pretty-print，HTML 可在编辑器菜单里「格式化」；
 * - 缓存未命中/启动失败时回落弹框并提示。
 */
fun openDebugFullContent(activity: AppCompatActivity, title: String, content: String) {
    val formatted = prettyJsonOrOriginal(content)
    val key = "debug_content_${System.currentTimeMillis()}"
    CacheManager.putMemory(key, formatted)
    if (CacheManager.getFromMemory(key) == null) {
        Toast.makeText(activity, "内容过大，已回落弹框显示", Toast.LENGTH_SHORT).show()
        activity.showDialogFragment(TextDialog(title, content, TextDialog.Mode.TEXT))
        return
    }
    runCatching {
        val isHtml = formatted.trimStart().startsWith("<")
        activity.startActivity<CodeEditActivity> {
            putExtra("cacheKey", key)
            putExtra("title", title)
            putExtra("languageName", if (isHtml) "text.html.basic" else "source.js")
        }
    }.onFailure {
        Toast.makeText(activity, it.localizedMessage ?: "打开全文失败", Toast.LENGTH_SHORT).show()
        activity.showDialogFragment(TextDialog(title, content, TextDialog.Mode.TEXT))
    }
}

/** 横滑 Chips 行（fadingEdge 由使用方按需叠加，先保持简单） */
@Composable
fun DebugChipRow(
    content: LazyListScope.() -> Unit
) {
    val state = rememberLazyListState()
    LazyRow(
        state = state,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        content = content,
    )
}

@Composable
fun DebugFilterChips(
    selected: DebugFilter,
    onSelect: (DebugFilter) -> Unit,
) {
    val settings = rememberAppSettingPalette()
    DebugChipRow {
        items(DebugFilter.entries, key = { it.name }) { filter ->
            FilterChip(
                selected = selected == filter,
                onClick = { onSelect(filter) },
                label = { Text(filter.title) },
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = Color(settings.row),
                    labelColor = settings.secondaryText,
                    selectedContainerColor = settings.accent,
                    selectedLabelColor = settings.onAccent
                )
            )
        }
    }
}

/**
 * 调试控制卡：目标 / 输入 / 示例 / 动作。
 *
 * 参数化目标标题是为了让书源（搜索/发现/详情/目录/正文）与订阅源（分类/搜索/内容）
 * 共用同一实现，避免两页复制粘贴。
 */
@Composable
fun DebugControlPanel(
    targets: List<String>,
    selectedTarget: Int,
    onSelectTarget: (Int) -> Unit,
    query: String,
    onQueryChange: (String) -> Unit,
    inputHint: String,
    enabled: Boolean,
    running: Boolean,
    examples: List<Pair<String, String>>,
    onExampleClick: (String) -> Unit,
    onScan: (() -> Unit)?,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onFullChain: () -> Unit,
    tryPlayUrl: String?,
    onTryPlay: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val settings = rememberAppSettingPalette()
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color(settings.row)),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            SectionLabel("调试目标")
            DebugChipRow {
                items(targets.size, key = { it }) { index ->
                    FilterChip(
                        selected = selectedTarget == index,
                        enabled = enabled,
                        onClick = { onSelectTarget(index) },
                        label = { Text(targets[index]) },
                        colors = FilterChipDefaults.filterChipColors(
                            containerColor = Color(settings.row),
                            labelColor = settings.secondaryText,
                            selectedContainerColor = settings.accent,
                            selectedLabelColor = settings.onAccent
                        )
                    )
                }
            }
            SectionLabel("输入")
            OutlinedTextField(
                value = query,
                onValueChange = onQueryChange,
                label = { Text(inputHint) },
                modifier = Modifier.fillMaxWidth(),
                enabled = enabled,
                maxLines = 3,
                trailingIcon = {
                    Row {
                        if (query.isNotEmpty() && enabled) {
                            IconButton(onClick = { onQueryChange("") }) {
                                Icon(Icons.Default.Clear, contentDescription = "清空输入")
                            }
                        }
                        if (onScan != null && enabled) {
                            IconButton(onClick = onScan) {
                                Icon(Icons.Default.QrCodeScanner, contentDescription = "扫码")
                            }
                        }
                    }
                },
            )
            if (examples.isNotEmpty()) {
                SectionLabel("示例")
                DebugChipRow {
                    items(examples, key = { it.first + ":" + it.second }) { example ->
                        FilterChip(
                            selected = query == example.second,
                            enabled = enabled,
                            onClick = { onExampleClick(example.second) },
                            label = { Text(example.first) },
                        )
                    }
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(
                    onClick = { if (running) onStop() else onStart() },
                    enabled = running || query.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (running) settings.danger else settings.accent,
                        contentColor = settings.onAccent,
                    ),
                ) {
                    Icon(
                        imageVector = if (running) Icons.Default.Stop else Icons.Default.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(if (running) "停止" else "开始调试")
                }
                if (!running) {
                    TextButton(onClick = onFullChain, enabled = query.isNotBlank()) {
                        Text("跑全链")
                    }
                }
                if (tryPlayUrl != null && !running) {
                    TextButton(onClick = { onTryPlay(tryPlayUrl) }) {
                        Text("试播")
                    }
                }
                Spacer(Modifier.weight(1f))
                if (running) {
                    Text(
                        "解析中…",
                        style = MaterialTheme.typography.labelSmall,
                        color = settings.secondaryText,
                    )
                }
            }
        }
    }
}

/** 日志工具条：标题 + 条数 + 过滤 + 运行进度/已用时。 */
@Composable
fun DebugLogToolbar(
    visibleCount: Int,
    totalCount: Int,
    filter: DebugFilter,
    onSelectFilter: (DebugFilter) -> Unit,
    running: Boolean,
    elapsedMillis: Long,
    modifier: Modifier = Modifier,
) {
    val settings = rememberAppSettingPalette()
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("日志", style = MaterialTheme.typography.titleSmall, color = settings.primaryText)
            Spacer(Modifier.width(8.dp))
            Text(
                "$visibleCount / $totalCount",
                style = MaterialTheme.typography.labelSmall,
                color = settings.secondaryText,
            )
            Spacer(Modifier.weight(1f))
            if (running) {
                Text(
                    "已用时 %.1fs".format(elapsedMillis / 1000.0),
                    style = MaterialTheme.typography.labelSmall,
                    color = settings.accent,
                )
            }
        }
        DebugFilterChips(selected = filter, onSelect = onSelectFilter)
        if (running) {
            LinearProgressIndicator(
                modifier = Modifier.fillMaxWidth().height(2.dp),
                color = settings.accent,
            )
        }
    }
}

/** 空态：三步引导（无日志时显示）。 */
@Composable
fun DebugEmptyState(
    running: Boolean,
    modifier: Modifier = Modifier,
) {
    val settings = rememberAppSettingPalette()
    Column(
        modifier = modifier.fillMaxSize().padding(horizontal = 24.dp, vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp, Alignment.CenterVertically),
    ) {
        Text(
            if (running) "等待调试日志…" else "开始一次调试",
            style = MaterialTheme.typography.titleMedium,
            color = settings.primaryText,
        )
        if (!running) {
            Text("① 选调试目标", style = MaterialTheme.typography.bodySmall, color = settings.secondaryText)
            Text("② 填 URL / 关键字", style = MaterialTheme.typography.bodySmall, color = settings.secondaryText)
            Text("③ 点「开始调试」", style = MaterialTheme.typography.bodySmall, color = settings.secondaryText)
        }
    }
}

@Composable
private fun SectionLabel(text: String) {
    val settings = rememberAppSettingPalette()
    Text(
        text,
        style = MaterialTheme.typography.labelMedium,
        color = settings.secondaryText,
    )
}

/**
 * 调试结论条（F65，ui-subpage-optimization；2026-10-27 产品化增强）：
 * - 失败显示阶段 + 完整错误（2 行省略）+ 下一步建议；
 * - 错误区可点击打开全文（[onShowError]）。
 */
@Composable
fun DebugSummaryBar(
    phaseKind: Int,
    stage: String?,
    errorMessage: String?,
    hint: String?,
    totalElapsedMillis: Long,
    onShowError: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val settings = rememberAppSettingPalette()
    val isSuccess = phaseKind == 1000
    val isError = phaseKind == -1
    val container = when {
        isError -> settings.danger.copy(alpha = 0.12f)
        isSuccess -> Color(settings.row)
        else -> Color(settings.row)
    }
    val content = when {
        isError -> settings.danger
        isSuccess -> colorResource(R.color.success)
        else -> settings.secondaryText
    }
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = container, contentColor = content),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = when {
                        isSuccess -> Icons.Default.Check
                        isError -> Icons.Default.ErrorOutline
                        else -> Icons.Default.Stop
                    },
                    contentDescription = null,
                    tint = content,
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    text = when {
                        isSuccess -> "调试完成"
                        isError -> "调试失败 · ${stageLabel(stage)}"
                        else -> "已取消"
                    },
                    style = MaterialTheme.typography.labelLarge,
                )
                Spacer(Modifier.weight(1f))
                if (!isError) {
                    Text(
                        "总耗时 %.2fs".format(totalElapsedMillis / 1000.0),
                        style = MaterialTheme.typography.labelMedium,
                        color = content,
                    )
                }
            }
            if (isError && !errorMessage.isNullOrBlank()) {
                Text(
                    text = errorMessage,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable(
                            enabled = onShowError != null,
                            onClick = { onShowError?.invoke() },
                        ),
                )
            }
            if (isError && !hint.isNullOrBlank()) {
                Text(
                    text = "建议：$hint",
                    style = MaterialTheme.typography.labelMedium,
                    color = settings.secondaryText,
                )
            }
        }
    }
}

/**
 * 结构化事件卡片：阶段徽标 + 类型 + 相对耗时 + 绝对时间戳 + 消息预览。
 * 点击看全文；长按复制单条。错误不再整块红底，只保留左侧 3dp 危险条。
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun DebugEntryCard(
    entry: DebugEntryUi,
    kindTitle: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    onLongClick: (() -> Unit)? = null,
) {
    val settings = rememberAppSettingPalette()
    val isError = entry.kind == -1
    val isResponse = entry.kind == 10 || entry.kind == 20 || entry.kind == 30 || entry.kind == 40
    val container = when {
        isError -> settings.danger.copy(alpha = 0.08f)
        isResponse -> settings.accent.copy(alpha = 0.10f)
        else -> Color(settings.row)
    }
    val content = if (isError) settings.danger else settings.primaryText
    val badgeColor: Color = when {
        isError -> settings.danger
        isResponse -> settings.accent
        else -> settings.secondaryText
    }
    Card(
        modifier = modifier
            .fillMaxWidth()
            .drawBehind {
                if (isError) {
                    drawRect(
                        color = settings.danger,
                        size = Size(3.dp.toPx(), size.height),
                    )
                }
            }
            .combinedClickable(onClick = onClick, onLongClick = onLongClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = container, contentColor = content),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(3.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                StageBadge(text = stageLabel(entry.stage), color = badgeColor)
                Spacer(Modifier.width(6.dp))
                Text(kindTitle, style = MaterialTheme.typography.labelMedium)
                Spacer(Modifier.weight(1f))
                Text(
                    "+%.3fs".format(entry.elapsedMillis / 1000.0),
                    style = MaterialTheme.typography.labelSmall,
                    color = settings.secondaryText,
                )
            }
            Text(
                entry.message,
                style = MaterialTheme.typography.bodySmall.copy(
                    fontFamily = if (isResponse) FontFamily.Monospace else FontFamily.Default,
                ),
                maxLines = 4,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(entry.timestamp)),
                style = MaterialTheme.typography.labelSmall,
                color = settings.secondaryText,
            )
        }
    }
}

@Composable
private fun StageBadge(text: String, color: Color) {
    Box(
        modifier = Modifier
            .background(color.copy(alpha = 0.14f), RoundedCornerShape(4.dp))
            .padding(horizontal = 4.dp, vertical = 1.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            color = color,
        )
    }
}

/** 长按复制（Compose 剪贴板 + toast）。 */
@Composable
fun rememberCopyEntry(): (String) -> Unit {
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    return { text ->
        clipboard.setText(AnnotatedString(text))
        Toast.makeText(context, "已复制", Toast.LENGTH_SHORT).show()
    }
}
