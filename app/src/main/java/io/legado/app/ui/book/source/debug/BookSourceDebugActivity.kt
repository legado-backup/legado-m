package io.legado.app.ui.book.source.debug

import android.content.Intent
import android.os.Bundle
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Column
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.ui.Modifier
import androidx.core.content.FileProvider
import androidx.viewbinding.ViewBinding
import io.legado.app.R
import io.legado.app.base.VMBaseActivity
import io.legado.app.base.attachComposeContent
import io.legado.app.base.composeShell
import io.legado.app.help.source.SourceHelp
import io.legado.app.model.Debug
import io.legado.app.ui.qrcode.QrCodeResult
import io.legado.app.ui.widget.components.GlassTopAppBar
import io.legado.app.ui.widget.components.MenuAction
import io.legado.app.ui.widget.components.TopBarActionRow
import io.legado.app.ui.theme.LegadoTheme
import io.legado.app.ui.widget.compose.showComposeChoiceListDialog
import io.legado.app.ui.widget.dialog.TextDialog
import io.legado.app.utils.sendToClip
import io.legado.app.utils.showDialogFragment
import io.legado.app.utils.toastOnUi
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * debug-page-redesign：书源调试页宿主（UI 全量 Compose，原 SearchView/help/recyclerView 移除）。
 * 保留能力：intent 传源 key、扫码选关键字（QrCodeResult，扫码即按搜索调试——与旧版行为一致）、
 * 弹框全文（TextDialog TEXT 模式）、导出日志（log-compliance-cleanup 批次E 成果并入顶栏菜单）。
 */
class BookSourceDebugActivity : VMBaseActivity<ViewBinding, BookSourceDebugModel>() {

    // M7 清壳：原 activity_source_debug.xml 仅含两个 ComposeView（无 View 语义）
    override val binding: ViewBinding by lazy { composeShell(this) }
    override val viewModel by viewModels<BookSourceDebugModel>()

    private val qrCodeResult = registerForActivityResult(QrCodeResult()) {
        // 扫码结果 = 搜索关键字，直接按搜索目标启动调试（旧版 startSearch 行为对齐）
        it?.let { key -> viewModel.startDebug(key) { toastOnUi("未获取到书源") } }
    }

    override fun onActivityCreated(savedInstanceState: Bundle?) {
        initComposeContent()
        viewModel.init(intent.getStringExtra("key")) {}
    }

    /**
     * M7 清壳（2026-09-22）：原 `activity_source_debug.xml` 是「ConstraintLayout + compose_top_bar(wrap)
     * + compose_host(0dp 占满剩余)」两个 ComposeView ⇒ 合并为**单一 Compose 树**
     * `Column { GlassTopAppBar(); Screen(weight(1f)) }`，与旧布局逐项等价
     * （顶栏 wrap_content；Screen 根为 `Box(fillMaxSize)` ⇒ 加 weight(1f) 即"占满剩余高度"）。
     * 换装后代码侧不再引用 R.layout，壳布局成为死资源。
     */
    private fun initComposeContent() {
        binding.root.attachComposeContent {
            LegadoTheme {
                Column {
                    GlassTopAppBar(
                        title = getString(R.string.debug_source),
                        navIcon = Icons.AutoMirrored.Filled.ArrowBack,
                        onNavClick = { finish() },
                        actions = {
                            TopBarActionRow(
                                listOf(
                                    MenuAction(title = "清空日志") { viewModel.clearLogs() },
                                    MenuAction(title = getString(R.string.log_export_logs)) { exportDebugLog() },
                                )
                            )
                        },
                    )
                    BookSourceDebugScreen(
                        sourceName = viewModel.sourceName,
                        examples = viewModel.examples,
                        onStart = { key -> viewModel.startDebug(key) { toastOnUi("未获取到书源") } },
                        onCancel = { viewModel.stopDebug() },
                        onShowFull = { title, content ->
                            showDialogFragment(TextDialog(title, content, TextDialog.Mode.TEXT))
                        },
                        // A-5：复用**线上播放器**入口试播调试得到的地址（不新建播放实现）
                        onTryPlay = { url -> tryPlayInOnlinePlayer(url) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }

    /**
     * A-5：把调试得到的地址交给**线上播放器**试播（复用 `SourceHelp.openVideoPlayer`）。
     *
     * 为什么必须有这一步：调试链路说「取流成功」只代表规则拿到了地址，
     * 不代表播放器能播（可能需要 Referer/Cookie/页面环境）。
     * 用与线上完全相同的入口试播，才能把「调试结论」与「真机表现」对齐。
     */
    private fun tryPlayInOnlinePlayer(url: String) {
        val source = viewModel.bookSource
        if (source == null) {
            toastOnUi("未获取到书源")
            return
        }
        runCatching {
            SourceHelp.openVideoPlayer(source, url, "调试试播", false)
        }.onFailure {
            toastOnUi(it.localizedMessage ?: "打开播放器失败")
        }
    }

    /** 导出当前调试会话日志（批次E）：复制全文 / 分享 txt 文件（FileProvider 复用 LogActivity 模式） */
    private fun exportDebugLog() {
        val logs = Debug.getSessionLogs()
        if (logs.isBlank()) {
            toastOnUi("暂无调试日志")
            return
        }
        showComposeChoiceListDialog(
            title = getString(R.string.log_export_logs),
            labels = listOf("复制到剪贴板", "分享 txt 文件")
        ) { index ->
            when (index) {
                0 -> sendToClip(logs)
                1 -> shareDebugLog(logs)
            }
        }
    }

    private fun shareDebugLog(content: String) {
        kotlin.runCatching {
            val fileName = "sourceDebug_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())}.txt"
            val file = File(cacheDir, fileName)
            file.writeText(content)
            val uri = FileProvider.getUriForFile(this, "${packageName}.fileProvider", file)
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, getString(R.string.log_export_logs)))
        }.onFailure {
            toastOnUi(it.localizedMessage)
        }
    }

    /**
     * launchMode=singleTop：从书源列表/外部 Intent 再次打开调试页时会复用本实例，
     * 只走 onNewIntent。必须按新 key 重新绑定源，否则页面一直调试上一个源。
     */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val key = rebindKey(intent) ?: return
        viewModel.stopDebug()
        viewModel.clearLogs()
        viewModel.init(key) { toastOnUi("未获取到书源") }
    }

    companion object {
        /** 复用实例时是否应重新绑定源：仅接受非空白 key（空 Intent 不改动当前调试会话）。 */
        internal fun rebindKey(intent: Intent): String? =
            intent.getStringExtra("key")?.takeIf { it.isNotBlank() }
    }
}
