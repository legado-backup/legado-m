# 构建与发布流程（本地 CI/CD）

> 本项目**未启用 GitHub Actions CI/CD**，构建、签名、发布、清场全部在本地完成。本文描述当前实际使用的本地构建与发布流程（2026-08 按仓库实际文件核验）。

---

## 1. 上游 CI 遗产说明

`.github/workflows/` 目录现存 5 个上游（legado-E）遗留 workflow，**本项目交付流程不依赖它们**（构建与发布走本地流程，见 §2/§4）。各文件触发器现状（2026-08-30 更新）：

| Workflow | 触发器现状 |
|----------|-----------|
| `release.yml` | push 触发已注释，仅 `workflow_dispatch` 手动触发 |
| `test.yml` | `push(main)` 与 `workflow_run`（连带注释）触发器**已注释**；保留 `pull_request` / `workflow_dispatch` |
| `web.yml` | `push(main, paths: modules/web/**)` 触发器**已注释**；保留 `pull_request` / `workflow_dispatch` |
| `cronet.yml` | `schedule`（每周一）+ `workflow_dispatch`；job 带 `github.repository == 'Luoyacheng/legado'` 守卫，在本私仓不会实际执行 |
| `stale.yml` | `schedule`（每 5 天）+ `workflow_dispatch`（上游 Issue 过期清理） |

> ✅ 幽灵 CI 已清零（2026-08-30）：`test.yml` / `web.yml` 的 push 触发器已注释（test.yml 的 `workflow_run` 依赖 "Build Web" 完成而连带注释），push 到主分支不会再触发上游构建流程产生失败记录。仅手动 `workflow_dispatch` 或 PR 会运行。

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

任何代码变更编译前，必须基于 `git diff` 更新 `app/src/main/assets/updateLog.md`（发布编排器 Stage3 会校验该文件当日条目，缺条目 fail-fast 拦截，见 §4.4）。

---

## 3. 构建后清场门禁（强制）

构建会产生残留 `Gradle daemon` + `Kotlin daemon`（实测各 2.6~4.2GB，空闲默认 2~3 小时才自退），频繁打包会打爆内存。

| 构建方式 | 清场要求 |
|----------|----------|
| `build-legado.bat` | 脚本已内置 `:STOP_DAEMON` 自动清场，无需额外操作 |
| `publish.bat` / 一键编排器（Stage2 三包构建） | 每包均经 build-legado.bat 构建，bat 内嵌清场，无需额外操作 |
| 直接 `gradlew assembleAppDebug/assembleAppRelease`（无 `--no-daemon`）或 IDE/Run | **构建结束后必须执行根目录 `stop-daemons.bat` 补一次清场**，禁止直接结束不管 |

配套 `gradle.properties` 已限制 `-Xmx3g` + `kotlin.daemon.jvmargs` + `daemon.idletimeout=600000`。完整说明见 `docs/project-flow/build-apk-guide.md` §4.10。

---

## 4. 一键发布编排器（publish.bat / scripts/publish_release.py）

单命令五阶段：**版本确认 → 三包构建 → 校验强化 → Release 发布 → git tag**。**必须使用项目 venv Python**：`ai_tests\venv\Scripts\python.exe`，或直接用项目根 `publish.bat`（薄壳入口，双击/命令行，透传全部参数）。

### 4.1 五阶段概览

| 阶段 | 内容 | 关键点 |
|------|------|--------|
| Stage1 版本确认 | `--version` 显式传入，否则按公式 bump（3.yyMMddHH 型 6 位） | 与 build.gradle releaseTime() 同构 |
| Stage2 三包构建 | subprocess 依次调 build-legado.bat（test/release/coexist），显式版本第 3 参保证三包同版本 | 每包后 bat 内嵌 daemon 清场 |
| Stage3 校验强化 | 三包齐全 / libcronet.so / apksigner 验签 / aapt2 包名版本一致性 / updateLog 当日条目 | 全部 fail-fast exit；缺包 exit；updateLog 缺当日条目拦截（无回退文案） |
| Stage4 Release 发布 | GitHub 层 gh CLI 上传 release + coexist（test 包仅本地归档，包名禁令）；Gitee 层走 requests | L2 真机门禁交互确认默认 N |
| Stage5 git tag | tag = 版本号，push 前人工确认 | 版本回滚锚点（`git checkout <版本号>`） |

### 4.2 用法与参数

```
publish.bat [--version <ver>] [--dry-run] [--platform gitee|github|both] [--config <path>]
            [--confirm-stage build|tag] [--l2-evidence <路径>]
```

| 参数 | 说明 |
|------|------|
| `--version <ver>` | 指定版本号（如 3.26.083020）；缺省时**按公式 bump** |
| `--dry-run` | 全流程模拟预览，无任何副作用（配置文件缺失时可退回 example 配置） |
| `--platform` | `gitee` / `github` / `both`，默认 `both` |
| `--config` | 配置文件路径，默认 `scripts/publish_config.json`（从 `publish_config.example.json` 复制并填入 token） |
| `--confirm-stage build\|tag` | 非交互确认续跑（可重复），AI 代答场景；**L2 门禁不适用此参数** |
| `--l2-evidence <路径>` | AI 代答 L2 真机门禁时必传；校验文件存在 + 当日 mtime |

### 4.3 APK 扫描与上传规则

配置键：`apk_dirs` / `apk_patterns` / `version_pattern`（`3\.\d{2}\.\d{6}`）。

| 包类型 | 扫描目录 | 文件模式 | 处置 |
|--------|----------|----------|------|
| test（测试包） | `output/apk/test` | `legado_miss_app_*.apk` | **仅本地归档，不上传 Release**（包名禁令） |
| release（正式包） | `output/apk/release` | `legado_miss_app_*.apk` | 上传 GitHub（gh CLI）+ Gitee（requests），保持原文件名 |
| coexist（共存包） | `output/apk/coexist` | `legado_legacy_app_*.apk` | 同上，保持原文件名 |

- 同类型同版本多个文件时取修改时间较新者；**缺包为致命错误（fail-fast exit）**（旧版"仅 WARN 不阻断"已升级）。
- 幂等：Release 已存在则复用；同名 asset 已存在则跳过。

### 4.4 Release 说明提取

从 `app/src/main/assets/updateLog.md` 中按版本号反推日期（`3.26.083020` → `2026/08/30`），提取对应 `**YYYY/MM/DD**` 标题条目作为 Release body；**未找到当日条目时 Stage3 直接 fail-fast 拦截**（旧版"回退为'自动发布 {version}'文案"机制已废除，禁止手动构造回退文案）。

### 4.5 网络与重试（gh CLI + requests 双层）

- **GitHub 层**：gh CLI 上传 Release，规避 uploads.github.com SSL 证书链验证失败与 51MB+ 大文件 SSLEOFError 双坑。
- **Gitee 层**：仍走 requests（`api/v5`），token 脱敏日志（`hide_token`）；Windows 环境 Gitee 偶发 SSL 证书链验证失败，临时禁用验证 + 过滤警告（源码内 TODO 恢复严格验证）。
- requests 重试策略：网络错误/5xx 重试（默认 3 次，指数退避 base 2），4xx 鉴权错误立即终止；请求超时 300s。

### 4.6 退出码

`0` 全部成功；`1` 存在失败（含 Stage3 校验 fail-fast / 某平台异常）；`2` 配置缺失/未填 token。

> 验证状态：编排器已建立，L1 `--dry-run` 全流程通过 + R2 负向测试通过；L2 真机演练与 L3 真实发版演练进行中。详见 `docs/project-rules/apk-publish-workflow.md` 与 `docs/specs/build-release-automation/design.md`（AD-01~AD-07）。

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
| 一键发布（五阶段：构建→校验→Release→tag） | `publish.bat` 或 `ai_tests\venv\Scripts\python.exe scripts\publish_release.py` |
| 发布预览（全流程模拟） | `publish.bat --dry-run` |
| 版本回滚 | `git checkout <版本号>`（tag = 版本号） |
| 前端构建 | `npm run build`（modules/web/ 下） |
