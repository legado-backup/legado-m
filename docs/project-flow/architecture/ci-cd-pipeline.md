# 构建与发布流程（本地 CI/CD）

> 本项目**未启用 GitHub Actions CI/CD**，构建、签名、发布、清场全部在本地完成。本文描述当前实际使用的本地构建与发布流程（2026-08 按仓库实际文件核验）。

---

## 1. 上游 CI 遗产说明

`.github/workflows/` 目录现存 5 个上游（legado-E）遗留 workflow，**本项目交付流程不依赖它们**（构建与发布走本地流程，见 §2/§4）。各文件触发器现状（2026-08 逐文件实测）：

| Workflow | 触发器现状 |
|----------|-----------|
| `release.yml` | push 触发已注释，仅 `workflow_dispatch` 手动触发 |
| `test.yml` | `push(main)` / `pull_request` / `workflow_run`（等 "Build Web" 完成）/ `workflow_dispatch` 触发器**仍激活**（上游遗留定义未注释） |
| `web.yml` | `push(main, paths: modules/web/**)` / `pull_request` / `workflow_dispatch` 触发器**仍激活** |
| `cronet.yml` | `schedule`（每周一）+ `workflow_dispatch`；job 带 `github.repository == 'Luoyacheng/legado'` 守卫，在本私仓不会实际执行 |
| `stale.yml` | `schedule`（每 5 天）+ `workflow_dispatch`（上游 Issue 过期清理） |

> ⚠️ 注意：`test.yml` / `web.yml` 的 push 触发定义**并未注释**。若 GitHub 仓库开启了 Actions，push 到 main 会触发上游构建流程（其签名/分发依赖 GitHub Secrets，私仓未配置必然失败但会产生失败记录）。如需彻底禁用，可注释这两个文件的 `push:` 段或在仓库设置中停用 Actions。

- `.github/scripts/`（cronet.sh / lzy_web.py / tg_bot.py）与 `.github/ISSUE_TEMPLATE/` 同为上游遗产。
- 原版 CI 的发布渠道矩阵（蓝奏云/Telegram/Gitee 镜像/Google Play）、Secrets 清单、版本号自动生成等描述已从本文移除——本项目发布走 §4 的本地脚本。

---

## 2. 本地构建流程（build-legado.bat 三包）

入口脚本为项目根 `build-legado.bat`（**硬编码本机环境**：`JAVA_HOME`、`ANDROID_HOME`、`GRADLE_USER_HOME`、`PROJECT_DIR`，换机器先改脚本头部）：

| 命令 | 产物 | 包名 |
|------|------|------|
| `build-legado.bat` | 测试包（App Debug） | `io.legado.miss.app.debug` |
| `build-legado.bat release` | 正式包（App Release） | `io.legado.miss.app.release` |
| `build-legado.bat debug io.legado.app` | 共存包（与原版共存） | `io.legado.app.debug` |

底层 Gradle 任务（productFlavors 仅 `app`，**App 首字母大写**，禁止 `assembleDebug`）：

```
./gradlew assembleAppDebug
./gradlew assembleAppRelease
```

APK 输出目录：`output/apk/{test,release,coexist}`（发布脚本按此扫描，见 §4）。

改签名/strings.xml 后需强制重打：`./gradlew assembleAppRelease --rerun-tasks`。

### 2.1 构建前门禁（版本交付同步）

任何代码变更编译前，必须基于 `git diff` 更新 `app/src/main/assets/updateLog.md`（发布脚本会从该文件提取 Release 说明，见 §4.3）。

---

## 3. 构建后清场门禁（强制）

构建会产生残留 `Gradle daemon` + `Kotlin daemon`（实测各 2.6~4.2GB，空闲默认 2~3 小时才自退），频繁打包会打爆内存。

| 构建方式 | 清场要求 |
|----------|----------|
| `build-legado.bat` | 脚本已内置 `:STOP_DAEMON` 自动清场，无需额外操作 |
| 直接 `gradlew assembleAppDebug/assembleAppRelease`（无 `--no-daemon`）或 IDE/Run | **构建结束后必须执行根目录 `stop-daemons.bat` 补一次清场**，禁止直接结束不管 |

配套 `gradle.properties` 已限制 `-Xmx3g` + `kotlin.daemon.jvmargs` + `daemon.idletimeout=600000`。完整说明见 `docs/project-flow/build-apk-guide.md` §4.10。

---

## 4. 发布流程（scripts/publish_release.py）

将本地构建的 APK 发布到 Gitee 与 GitHub Release。**必须使用项目 venv Python**：`ai_tests\venv\Scripts\python.exe`。

### 4.1 用法与参数

```
ai_tests\venv\Scripts\python.exe scripts\publish_release.py [--version <ver>] [--dry-run] [--platform gitee|github|both] [--config <path>]
```

| 参数 | 说明 |
|------|------|
| `--version <ver>` | 指定版本号（如 3.26.072912）；缺省时**自动取扫描到的最大版本号** |
| `--dry-run` | 只预览不实际调用 API（配置文件缺失时可退回 example 配置） |
| `--platform` | `gitee` / `github` / `both`，默认 `both` |
| `--config` | 配置文件路径，默认 `scripts/publish_config.json`（从 `publish_config.example.json` 复制并填入 token） |

### 4.2 APK 扫描与上传命名

配置键：`apk_dirs` / `apk_patterns` / `version_pattern`（`3\.\d{2}\.\d{6}`）。

| 包类型 | 扫描目录 | 文件模式 | 上传到 Release 的文件名 |
|--------|----------|----------|------------------------|
| test（测试包） | `output/apk/test` | `legado_miss_app_*.apk` | `legado_miss_app_debug_{version}.apk`（重命名，避免与正式包同名冲突） |
| release（正式包） | `output/apk/release` | `legado_miss_app_*.apk` | 保持原文件名 |
| coexist（共存包） | `output/apk/coexist` | `legado_legacy_app_*.apk` | 保持原文件名 |

- 同类型同版本多个文件时取修改时间较新者；缺包仅 WARN 不阻断。
- 幂等：Release 已存在则复用；同名 asset 已存在则跳过。

### 4.3 Release 说明提取

从 `app/src/main/assets/updateLog.md` 中按版本号反推日期（`3.26.072912` → `2026/07/29`），提取对应 `**YYYY/MM/DD**` 标题条目作为 Release body；未找到时回退为"自动发布 {version}"。

### 4.4 网络与重试

- Gitee API（`api/v5`）+ GitHub API（`api.github.com` / `uploads.github.com`），token 脱敏日志（`hide_token`）。
- 重试策略：网络错误/5xx 重试（默认 3 次，指数退避 base 2），4xx 鉴权错误立即终止；请求超时 300s。
- 已知环境问题：`uploads.github.com` SSL 证书链验证失败（疑似代理拦截），脚本临时禁用 SSL 验证并过滤警告（源码内有 TODO 恢复严格验证）。

### 4.5 退出码

`0` 全部成功；`1` 存在失败（含某平台异常）；`2` 配置缺失/未填 token。

---

## 5. 前端构建（modules/web）

```
cd modules/web
npm run build    # type-check + vite build + sync.js（产物同步进 app assets）
```

本地 `npm run build` 即含 `sync.js` 同步，无需手动复制。

---

## 6. 命令速查

| 场景 | 命令 |
|------|------|
| 测试包 | `build-legado.bat` |
| 正式包 | `build-legado.bat release` |
| 共存包 | `build-legado.bat debug io.legado.app` |
| 直连 Gradle 后清场 | `./gradlew assembleAppRelease` → `stop-daemons.bat` |
| 发布预览 | `ai_tests\venv\Scripts\python.exe scripts\publish_release.py --dry-run` |
| 实际发布（双平台） | `ai_tests\venv\Scripts\python.exe scripts\publish_release.py --platform both` |
| 前端构建 | `npm run build`（modules/web/ 下） |
