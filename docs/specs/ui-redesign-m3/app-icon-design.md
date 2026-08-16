# App 图标改版设计依据（D-4）

> **文档性质**：审计偏差 D-4 的收尾文档——为「正式包图标已替换为 `ic_launcher_foreground`」补齐设计依据。关联：`audit-code-vs-design.md` 偏差项 1 + D-4 / D-14③。

## 0. 决策记录

- **改动事实**：`mipmap-anydpi-v26/ic_launcher.xml` foreground 由 `@drawable/ic_launcher0` 改为 `@mipmap/ic_launcher_foreground`，并新增 5 个 `ic_launcher_foreground.png`（mdpi~xxxhdpi）。
- **审查发现**：2026-08-15 审查时，设计文档体系无任何图标改版记录，登记为偏差项 1（无设计依据）。
- **用户决策**：**✅ 已授权（2026-08-15）：保留新图标 `ic_launcher_foreground`**，本窗口补齐设计依据 + D-14③ launcherIcon 代码侧残留一并收尾。

## 1. 设计依据（Why）

1. **Adaptive Icon 现代化**：Android 8.0+（API 26）要求应用适配 `adaptive-icon`（前景 + 背景分离，系统裁剪成圆/方/水滴等不同蒙版）。旧实现直接用 `@drawable/ic_launcher0`（108dp vector，含整图渐变背景）作为 foreground——前景中自带背景色块，被系统蒙版裁剪后无法与 `launcher_background` 背景正确融合，且不同启动器蒙版下呈现不完整。
2. **M3 设计语言对齐**：本 spec（README）目标为 Material 3 柔和护眼体系。新前景位图按「透明底 + 前景图形」规范制作，配合纯色 `launcher_background`（`#FF1A2F5A`），保证各蒙版下视觉完整。
3. **Monochrome 主题图标支持**：`<monochrome android:drawable="@drawable/ic_launcher4" />` 复用既有 monochrome 图形，支持 Android 13+ Themed Icons（跟随系统主题单色着色）。
4. **多密度位图替代超大 vector 前景**：旧 `ic_launcher0` 为 108dp 复杂 path vector，作为 adaptive foreground 需在运行时栅格化；新方案按标准 5 密度（mdpi~xxxhdpi）位图交付，与项目其余 mipmap 资源交付方式一致。

## 2. 资源清单与引用链

| 资源 | 类型 | 用途 |
|------|------|------|
| `AndroidManifest.xml:28` | — | 应用图标 `android:icon="@mipmap/ic_launcher"` |
| `mipmap-anydpi-v26/ic_launcher.xml` | adaptive-icon | Android 8.0+：background `@color/launcher_background` + foreground `@mipmap/ic_launcher_foreground` + monochrome `@drawable/ic_launcher4` |
| `mipmap-{m,h,x,xx,xxx}hdpi/ic_launcher.png` | 位图 | Android <8.0 fallback 图标（存量保留） |
| `mipmap-{m,h,x,xx,xxx}hdpi/ic_launcher_foreground.png` | 位图 | 新 adaptive 前景（本次新增） |
| `values/colors.xml` `launcher_background` | 颜色 | `#FF1A2F5A` adaptive 背景 |
| `mipmap-{mdpi..xxxhdpi}/launcher{1..7}` | 位图 | 7 个 Activity 自定义图标（AndroidManifest:50-122，存量保留，不属本次改版） |
| `drawable/ic_launcher0~7*.xml` | vector | 旧图标图形（`ic_launcher4` 仍被 monochrome 引用；`ic_launcher0` 不再被 foreground 引用） |

## 3. D-14③ 收尾（launcherIcon 代码侧残留清理）

`pref_config_theme.xml` 已删除 `launcherIcon` 偏好项后，代码侧残留两处，本窗口已清理：

- `constant/PreferKey.kt`：删除 `const val launcherIcon = "launcherIcon"`（无任何读取点）。
- `help/storage/BackupConfig.kt`：`ignorePrefKeys` 数组删除 `PreferKey.launcherIcon` 引用。

Grep 确认 `launcherIcon` 全仓零残留（`app/src/main` 下仅 manifest 资源 `@mipmap/ic_launcher` 与图标资源命名，无业务偏好键残留）。

## 4. 遗留说明

- `drawable/ic_launcher0.xml` 等旧 vector 仍存在于资源目录。`ic_launcher0` 已无引用，是否删除属死资源清理范畴（D-14 其余项），本窗口不扩大范围。
- 新前景位图 `ic_launcher_foreground.png` 由另一 AI 生成，视觉设计稿存档于其产出记录；本文档仅固化技术性设计依据与决策记录。

## 5. 变更记录

- 2026-08-15：用户授权保留新图标（audit 偏差项 1 → D-4）。
- 2026-08-16：本窗口补齐设计依据文档；完成 D-14③ launcherIcon 代码侧残留清理（PreferKey/BackupConfig 两处）。
