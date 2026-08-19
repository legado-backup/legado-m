package io.legado.app.ui.config

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddAlert
import androidx.compose.material.icons.filled.BugReport
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.Category
import androidx.compose.material.icons.filled.ClearAll
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.DeleteForever
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.Explore
import androidx.compose.material.icons.filled.FactCheck
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.GppGood
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.NetworkCheck
import androidx.compose.material.icons.filled.Phishing
import androidx.compose.material.icons.filled.PlayCircle
import androidx.compose.material.icons.filled.Public
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Report
import androidx.compose.material.icons.filled.RestoreFromTrash
import androidx.compose.material.icons.filled.RssFeed
import androidx.compose.material.icons.filled.Rule
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.SettingsInputHdmi
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.TextFields
import androidx.compose.material.icons.filled.Upload
import androidx.compose.material.icons.filled.Update
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import io.legado.app.R
import io.legado.app.ui.widget.components.AppSelectDialog
import io.legado.app.ui.widget.components.SelectOption
import io.legado.app.ui.widget.components.SettingsCard
import io.legado.app.ui.widget.components.SettingsClickRow
import io.legado.app.ui.widget.components.SettingsSection
import io.legado.app.ui.widget.components.SettingsToggleRow

/**
 * 其他设置（P3-2 配置子页 Compose 化，对齐 ThemeConfigScreen/CoverConfigScreen 范式）。
 *
 * 内容区全 Compose：Main Activity 组 + 其他设置组，全部设置项零裁剪迁移
 * （复用 SettingsSection/SettingsCard/SettingsToggleRow/SettingsClickRow）。
 * 语言 / 默认首页 / 更新渠道三项 NameListPreference 用 AppSelectDialog（单选）呈现，
 * 其余点击项（数字选择/编辑框/文件选择等副作用）由 Fragment 处理，此处仅上抛 key。
 */
@Composable
fun OtherConfigScreen(
    state: OtherConfigState,
    onToggleChange: (key: String, value: Boolean) -> Unit,
    onItemClick: (key: String) -> Unit,
    onLanguageSelect: (String) -> Unit,
    onHomePageSelect: (String) -> Unit,
    onVariantSelect: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var selectDialog by remember { mutableStateOf<String?>(null) }

    // NameListPreference 选项（entries/value 数组资源）
    val languageLabels = stringArrayResource(R.array.language)
    val languageValues = stringArrayResource(R.array.language_value)
    val homePageLabels = stringArrayResource(R.array.default_home_page)
    val homePageValues = stringArrayResource(R.array.default_home_page_value)
    val variantLabels = stringArrayResource(R.array.default_app_variant)
    val variantValues = stringArrayResource(R.array.default_app_variant_value)

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .verticalScroll(rememberScrollState())
    ) {
        // ============ Main Activity ============
        SettingsSection(title = stringResource(R.string.main_activity), modifier = Modifier.fillMaxWidth()) {
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Language,
                    title = stringResource(R.string.language),
                    value = state.languageLabel,
                    onClick = { selectDialog = "language" }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Refresh,
                    title = stringResource(R.string.pt_auto_refresh),
                    subtitle = stringResource(R.string.ps_auto_refresh),
                    checked = state.autoRefresh,
                    onCheckedChange = { onToggleChange("auto_refresh", it) }
                )
                if (state.autoRefresh) {
                    SettingsToggleRow(
                        icon = Icons.Default.Update,
                        title = stringResource(R.string.only_update_read),
                        subtitle = stringResource(R.string.ps_only_update_read),
                        checked = state.onlyUpdateRead,
                        onCheckedChange = { onToggleChange("onlyUpdateRead", it) }
                    )
                }
                SettingsToggleRow(
                    icon = Icons.Default.PlayCircle,
                    title = stringResource(R.string.pt_default_read),
                    subtitle = stringResource(R.string.ps_default_read),
                    checked = state.defaultToRead,
                    onCheckedChange = { onToggleChange("defaultToRead", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Explore,
                    title = stringResource(R.string.show_discovery),
                    checked = state.showDiscovery,
                    onCheckedChange = { onToggleChange("showDiscovery", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.RssFeed,
                    title = stringResource(R.string.show_rss),
                    checked = state.showRss,
                    onCheckedChange = { onToggleChange("showRss", it) }
                )
                SettingsClickRow(
                    icon = Icons.Default.Home,
                    title = stringResource(R.string.default_home_page),
                    value = state.defaultHomePageLabel,
                    onClick = { selectDialog = "defaultHomePage" }
                )
            }
        }

        // ============ 其他设置 ============
        SettingsSection(title = stringResource(R.string.other_setting), modifier = Modifier.fillMaxWidth()) {
            // 网络与安全
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Lock,
                    title = stringResource(R.string.set_local_password),
                    subtitle = stringResource(R.string.set_local_password_summary),
                    onClick = { onItemClick("localPassword") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Public,
                    title = stringResource(R.string.user_agent),
                    onClick = { onItemClick("userAgent") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Dns,
                    title = stringResource(R.string.custom_hosts),
                    subtitle = stringResource(R.string.custom_hosts_summary),
                    onClick = { onItemClick("customHosts") }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Security,
                    title = stringResource(R.string.web_service_wake_lock),
                    subtitle = stringResource(R.string.web_service_wake_lock_summary),
                    checked = state.webServiceWakeLock,
                    onCheckedChange = { onToggleChange("webServiceWakeLock", it) }
                )
                SettingsClickRow(
                    icon = Icons.Default.Folder,
                    title = stringResource(R.string.book_tree_uri_t),
                    value = state.defaultBookTreeUri,
                    onClick = { onItemClick("defaultBookTreeUri") }
                )
            }
            // 连接
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsToggleRow(
                    icon = Icons.Default.NetworkCheck,
                    title = "Cronet",
                    subtitle = stringResource(R.string.pref_cronet_summary),
                    checked = state.cronet,
                    onCheckedChange = { onToggleChange("Cronet", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Image,
                    title = stringResource(R.string.anti_alias),
                    subtitle = stringResource(R.string.pref_anti_alias_summary),
                    checked = state.antiAlias,
                    onCheckedChange = { onToggleChange("antiAlias", it) }
                )
                SettingsClickRow(
                    icon = Icons.Default.SettingsInputHdmi,
                    title = stringResource(R.string.web_port_title),
                    value = state.webPort.toString(),
                    onClick = { onItemClick("webPort") }
                )
            }
            // 缓存与存储
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Storage,
                    title = stringResource(R.string.bitmap_cache_size),
                    value = state.bitmapCacheSize.toString(),
                    onClick = { onItemClick("bitmapCacheSize") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Image,
                    title = stringResource(R.string.image_retain_number),
                    value = state.imageRetainNum.toString(),
                    onClick = { onItemClick("imageRetainNum") }
                )
                SettingsClickRow(
                    icon = Icons.Default.FileDownload,
                    title = stringResource(R.string.pre_download),
                    value = state.preDownloadNum.toString(),
                    onClick = { onItemClick("preDownloadNum") }
                )
                SettingsClickRow(
                    icon = Icons.Default.ClearAll,
                    title = stringResource(R.string.clear_cache),
                    subtitle = stringResource(R.string.clear_cache_summary),
                    onClick = { onItemClick("cleanCache") }
                )
                SettingsClickRow(
                    icon = Icons.Default.DeleteForever,
                    title = stringResource(R.string.clear_webview_data),
                    subtitle = stringResource(R.string.clear_webview_data_summary),
                    onClick = { onItemClick("clearWebViewData") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Memory,
                    title = stringResource(R.string.shrink_database),
                    subtitle = stringResource(R.string.shrink_database_summary),
                    onClick = { onItemClick("shrinkDatabase") }
                )
            }
            // 并发
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Speed,
                    title = stringResource(R.string.search_thread_count_title),
                    value = state.searchThreadCount.toString(),
                    onClick = { onItemClick("searchThreadCount") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Sync,
                    title = stringResource(R.string.update_cache_thread_count_title),
                    value = state.updateCacheThreadCount.toString(),
                    onClick = { onItemClick("updateCacheThreadCount") }
                )
                SettingsClickRow(
                    icon = Icons.Default.RssFeed,
                    title = stringResource(R.string.rss_parse_concurrency),
                    value = state.rssParseConcurrency.toString(),
                    onClick = { onItemClick("rssParseConcurrency") }
                )
                SettingsClickRow(
                    icon = Icons.Default.NetworkCheck,
                    title = stringResource(R.string.image_load_concurrency),
                    value = state.imageLoadConcurrency.toString(),
                    onClick = { onItemClick("imageLoadConcurrency") }
                )
            }
            // 阅读与替换
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsToggleRow(
                    icon = Icons.Default.Rule,
                    title = stringResource(R.string.replace_enable_default_t),
                    subtitle = stringResource(R.string.replace_enable_default_s),
                    checked = state.replaceEnableDefault,
                    onCheckedChange = { onToggleChange("replaceEnableDefault", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.VolumeUp,
                    title = stringResource(R.string.media_button_on_exit_title),
                    subtitle = stringResource(R.string.media_button_on_exit_summary),
                    checked = state.mediaButtonOnExit,
                    onCheckedChange = { onToggleChange("mediaButtonOnExit", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.VolumeUp,
                    title = stringResource(R.string.read_aloud_by_media_button_title),
                    subtitle = stringResource(R.string.read_aloud_by_media_button_summary),
                    checked = state.readAloudByMediaButton,
                    onCheckedChange = { onToggleChange("readAloudByMediaButton", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Security,
                    title = stringResource(R.string.ignore_audio_focus_title),
                    subtitle = stringResource(R.string.ignore_audio_focus_summary),
                    checked = state.ignoreAudioFocus,
                    onCheckedChange = { onToggleChange("ignoreAudioFocus", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Cached,
                    title = stringResource(R.string.auto_clear_expired),
                    subtitle = stringResource(R.string.auto_clear_expired_summary),
                    checked = state.autoClearExpired,
                    onCheckedChange = { onToggleChange("autoClearExpired", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.AddAlert,
                    title = stringResource(R.string.show_add_to_shelf_alert_title),
                    subtitle = stringResource(R.string.show_add_to_shelf_alert_summary),
                    checked = state.showAddToShelfAlert,
                    onCheckedChange = { onToggleChange("showAddToShelfAlert", it) }
                )
            }
            // 更新与其他
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Update,
                    title = stringResource(R.string.update_to_variant_title),
                    subtitle = stringResource(R.string.update_to_variant_summary),
                    value = state.updateToVariantLabel,
                    onClick = { selectDialog = "updateToVariant" }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Sync,
                    title = stringResource(R.string.auto_update),
                    subtitle = stringResource(R.string.auto_update_summary),
                    checked = state.autoUpdateVariant,
                    onCheckedChange = { onToggleChange("autoUpdateVariant", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Phishing,
                    title = stringResource(R.string.show_manga_ui),
                    checked = state.showMangaUi,
                    onCheckedChange = { onToggleChange("showMangaUi", it) }
                )
                SettingsClickRow(
                    icon = Icons.Default.PlayCircle,
                    title = stringResource(R.string.video_setting),
                    subtitle = stringResource(R.string.video_setting_summary),
                    onClick = { onItemClick("videoSetting") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Code,
                    title = stringResource(R.string.source_edit_text_max_line),
                    value = state.sourceEditMaxLine.toString(),
                    onClick = { onItemClick("sourceEditMaxLine") }
                )
                SettingsClickRow(
                    icon = Icons.Default.FactCheck,
                    title = stringResource(R.string.check_source_config),
                    value = state.checkSourceSummary,
                    onClick = { onItemClick("checkSource") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Upload,
                    title = stringResource(R.string.direct_link_upload_rule),
                    subtitle = stringResource(R.string.direct_link_upload_rule_summary),
                    onClick = { onItemClick("uploadRule") }
                )
            }
            // 调试
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsToggleRow(
                    icon = Icons.Default.TextFields,
                    title = stringResource(R.string.add_to_text_context_menu_t),
                    subtitle = stringResource(R.string.add_to_text_context_menu_s),
                    checked = state.processText,
                    onCheckedChange = { onToggleChange("process_text", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Report,
                    title = stringResource(R.string.record_log),
                    subtitle = stringResource(R.string.record_debug_log),
                    checked = state.recordLog,
                    onCheckedChange = { onToggleChange("recordLog", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Wifi,
                    title = stringResource(R.string.debug_log_floating_ball),
                    subtitle = stringResource(R.string.debug_log_floating_ball_s),
                    checked = state.debugLogFloatingBall,
                    onCheckedChange = { onToggleChange("debugLogFloatingBall", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.RestoreFromTrash,
                    title = stringResource(R.string.source_recycle_bin_enabled),
                    subtitle = stringResource(R.string.source_recycle_bin_enabled_s),
                    checked = state.sourceRecycleBinEnabled,
                    onCheckedChange = { onToggleChange("sourceRecycleBinEnabled", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Report,
                    title = stringResource(R.string.record_heap_dump_t),
                    subtitle = stringResource(R.string.record_heap_dump_s),
                    checked = state.recordHeapDump,
                    onCheckedChange = { onToggleChange("recordHeapDump", it) }
                )
                SettingsClickRow(
                    icon = Icons.Default.BugReport,
                    title = stringResource(R.string.debug_tools),
                    subtitle = stringResource(R.string.debug_tools_desc),
                    onClick = { onItemClick("debug_tools") }
                )
            }
        }
    }

    // ============ NameListPreference 单选对话框 ============
    when (selectDialog) {
        "language" -> AppSelectDialog(
            title = stringResource(R.string.language),
            options = languageLabels.mapIndexed { i, label -> SelectOption(label, languageValues[i]) },
            selected = state.language,
            confirmText = stringResource(R.string.ok),
            cancelText = stringResource(R.string.cancel),
            onSelect = { option ->
                selectDialog = null
                onLanguageSelect(option.value)
            },
            onDismiss = { selectDialog = null }
        )

        "defaultHomePage" -> AppSelectDialog(
            title = stringResource(R.string.default_home_page),
            options = homePageLabels.mapIndexed { i, label -> SelectOption(label, homePageValues[i]) },
            selected = state.defaultHomePage,
            confirmText = stringResource(R.string.ok),
            cancelText = stringResource(R.string.cancel),
            onSelect = { option ->
                selectDialog = null
                onHomePageSelect(option.value)
            },
            onDismiss = { selectDialog = null }
        )

        "updateToVariant" -> AppSelectDialog(
            title = stringResource(R.string.update_to_variant_title),
            options = variantLabels.mapIndexed { i, label -> SelectOption(label, variantValues[i]) },
            selected = state.updateToVariant,
            confirmText = stringResource(R.string.ok),
            cancelText = stringResource(R.string.cancel),
            onSelect = { option ->
                selectDialog = null
                onVariantSelect(option.value)
            },
            onDismiss = { selectDialog = null }
        )
    }
}

/**
 * 其他设置 UI 状态（Fragment 桥接，值为页面当前展示值）。
 */
data class OtherConfigState(
    val language: String = "auto",
    val languageLabel: String = "",
    val autoRefresh: Boolean = false,
    val onlyUpdateRead: Boolean = false,
    val defaultToRead: Boolean = false,
    val showDiscovery: Boolean = true,
    val showRss: Boolean = true,
    val defaultHomePage: String = "bookshelf",
    val defaultHomePageLabel: String = "",
    val webServiceWakeLock: Boolean = false,
    val defaultBookTreeUri: String = "",
    val sourceEditMaxLine: Int = Int.MAX_VALUE,
    val checkSourceSummary: String = "",
    val cronet: Boolean = false,
    val antiAlias: Boolean = false,
    val bitmapCacheSize: Int = 50,
    val imageRetainNum: Int = 0,
    val preDownloadNum: Int = 2,
    val replaceEnableDefault: Boolean = true,
    val mediaButtonOnExit: Boolean = true,
    val readAloudByMediaButton: Boolean = false,
    val ignoreAudioFocus: Boolean = false,
    val autoClearExpired: Boolean = true,
    val showAddToShelfAlert: Boolean = true,
    val updateToVariant: String = "default_version",
    val updateToVariantLabel: String = "",
    val autoUpdateVariant: Boolean = true,
    val showMangaUi: Boolean = true,
    val webPort: Int = 1122,
    val searchThreadCount: Int = 32,
    val updateCacheThreadCount: Int = 16,
    val rssParseConcurrency: Int = 3,
    val imageLoadConcurrency: Int = 5,
    val processText: Boolean = true,
    val recordLog: Boolean = false,
    val debugLogFloatingBall: Boolean = false,
    val sourceRecycleBinEnabled: Boolean = false,
    val recordHeapDump: Boolean = false
)
