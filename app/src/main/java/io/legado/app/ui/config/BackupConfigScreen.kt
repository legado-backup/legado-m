package io.legado.app.ui.config

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Archive
import androidx.compose.material.icons.filled.Backup
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Restore
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Update
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import io.legado.app.R
import io.legado.app.ui.widget.components.SettingsCard
import io.legado.app.ui.widget.components.SettingsClickRow
import io.legado.app.ui.widget.components.SettingsSection
import io.legado.app.ui.widget.components.SettingsToggleRow

/**
 * 备份与恢复（P3-2b 配置子页 Compose 化，对齐 OtherConfigScreen/ThemeConfigScreen 范式）。
 *
 * 内容区全 Compose：WebDAV 设置组 + 备份恢复组，全部设置项零裁剪迁移
 * （复用 SettingsSection/SettingsCard/SettingsClickRow/SettingsToggleRow）。
 * 编辑框/文件选择/备份/恢复/忽略设置等副作用由 Fragment 处理，此处仅上抛 key；
 * 「恢复」行保留原版长按 → 本地恢复（[onRestoreLongClick]）。
 */
@Composable
fun BackupConfigScreen(
    state: BackupConfigState,
    onToggleChange: (key: String, value: Boolean) -> Unit,
    onItemClick: (key: String) -> Unit,
    onRestoreLongClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .verticalScroll(rememberScrollState())
    ) {
        // ============ WebDAV 设置 ============
        SettingsSection(title = stringResource(R.string.web_dav_set), modifier = Modifier.fillMaxWidth()) {
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Cloud,
                    title = stringResource(R.string.web_dav_url),
                    value = state.webDavUrl.ifBlank { null },
                    onClick = { onItemClick("web_dav_url") }
                )
                SettingsClickRow(
                    icon = Icons.Default.AccountCircle,
                    title = stringResource(R.string.web_dav_account),
                    value = state.webDavAccount.ifBlank { null },
                    onClick = { onItemClick("web_dav_account") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Lock,
                    title = stringResource(R.string.web_dav_pw),
                    value = if (state.webDavPassword.isEmpty()) null else "*".repeat(state.webDavPassword.length),
                    onClick = { onItemClick("web_dav_password") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Folder,
                    title = stringResource(R.string.sub_dir),
                    value = state.webDavDir,
                    onClick = { onItemClick("webDavDir") }
                )
                SettingsClickRow(
                    icon = Icons.Default.PhoneAndroid,
                    title = stringResource(R.string.webdav_device_name),
                    value = state.webDavDeviceName,
                    onClick = { onItemClick("webDavDeviceName") }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Sync,
                    title = stringResource(R.string.sync_book_progress_t),
                    subtitle = stringResource(R.string.sync_book_progress_s),
                    checked = state.syncBookProgress,
                    onCheckedChange = { onToggleChange("syncBookProgress", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Update,
                    title = stringResource(R.string.sync_book_progress_plus_t),
                    subtitle = stringResource(R.string.sync_book_progress_plus_s),
                    checked = state.syncBookProgressPlus,
                    enabled = state.syncBookProgress,
                    onCheckedChange = { onToggleChange("syncBookProgressPlus", it) }
                )
            }
        }

        // ============ 备份与恢复 ============
        SettingsSection(title = stringResource(R.string.backup_restore), modifier = Modifier.fillMaxWidth()) {
            SettingsCard(modifier = Modifier.fillMaxWidth()) {
                SettingsClickRow(
                    icon = Icons.Default.Storage,
                    title = stringResource(R.string.backup_path),
                    subtitle = stringResource(R.string.select_backup_path),
                    value = state.backupPath.ifBlank { null },
                    onClick = { onItemClick("backupUri") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Backup,
                    title = stringResource(R.string.backup),
                    subtitle = stringResource(R.string.backup_summary),
                    onClick = { onItemClick("web_dav_backup") }
                )
                SettingsClickRow(
                    icon = Icons.Default.Restore,
                    title = stringResource(R.string.restore),
                    subtitle = stringResource(R.string.restore_summary),
                    onClick = { onItemClick("web_dav_restore") },
                    onLongClick = onRestoreLongClick
                )
                SettingsClickRow(
                    icon = Icons.Default.FilterList,
                    title = stringResource(R.string.restore_ignore),
                    subtitle = stringResource(R.string.restore_ignore_summary),
                    onClick = { onItemClick("restoreIgnore") }
                )
                SettingsClickRow(
                    icon = Icons.Default.FileUpload,
                    title = stringResource(R.string.menu_import_old_version),
                    onClick = { onItemClick("import_old") }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Archive,
                    title = stringResource(R.string.only_latest_backup_t),
                    subtitle = stringResource(R.string.only_latest_backup_s),
                    checked = state.onlyLatestBackup,
                    onCheckedChange = { onToggleChange("onlyLatestBackup", it) }
                )
                SettingsToggleRow(
                    icon = Icons.Default.Notifications,
                    title = stringResource(R.string.auto_check_new_backup_t),
                    subtitle = stringResource(R.string.auto_check_new_backup_s),
                    checked = state.autoCheckNewBackup,
                    onCheckedChange = { onToggleChange("autoCheckNewBackup", it) }
                )
            }
        }
    }
}

/**
 * 备份与恢复 UI 状态（Fragment 桥接，值为页面当前展示值）。
 */
data class BackupConfigState(
    val webDavUrl: String = "",
    val webDavAccount: String = "",
    val webDavPassword: String = "",
    val webDavDir: String = "legado",
    val webDavDeviceName: String = "",
    val syncBookProgress: Boolean = true,
    val syncBookProgressPlus: Boolean = false,
    val backupPath: String = "",
    val onlyLatestBackup: Boolean = true,
    val autoCheckNewBackup: Boolean = true
)
