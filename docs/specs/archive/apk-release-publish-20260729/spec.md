# spec: apk-release-publish-20260729

> APK 发布集成方案：将本地构建的三个 APK 包（测试/正式/共存）自动上传至 Gitee 与 GitHub 的 Release，使 App 内"检查更新"功能能下载到新版本。

---

## 1. Intent（意图）

当前用户已能通过 `gradlew` 本地构建三个 APK 包：

| 包类型 | 文件名格式 | 输出路径 | applicationId |
|--------|-----------|---------|---------------|
| 测试包 | `legado_miss_app_{version}.apk` | `output/apk/test/` | `io.legado.miss.app.debug` |
| 正式包 | `legado_miss_app_{version}.apk` | `output/apk/release/` | `io.legado.miss.app.release` |
| 共存包 | `legado_legacy_app_{version}.apk` | `output/apk/coexist/` | `io.legado.app`（debug 构建） |

其中 `version = 3.{yy}.{MMddHH}`，例如 `3.26.072912`。

App 内"检查更新"功能（`AboutFragment.checkUpdate()` → `AppUpdate.giteeUpdate.check()`）当前实际走 Gitee 源 `gitee.com/api/v5/repos/lyc486/legado/releases`，但 APK 发布仍需手动操作（构建后手动登录平台、手动创建 Release、手动上传 APK），三包 × 双平台 = 6 次重复手工操作，效率低且易错。

**本方案意图**：通过本地 Python 脚本一键将本地构建产物上传至 Gitee 与 GitHub 的 Release，消除手工发布环节，确保 App 内"检查更新"功能能立即拉到新版本 APK。

---

## 2. Scope（范围）

### 2.1 In Scope（包含）

- 编写 `scripts/publish_release.py` 发布脚本，调用 Gitee API v5 与 GitHub API v3 上传 APK 到指定 Release。
- 编写 `scripts/publish_config.json` 配置模板（含仓库 owner/repo、token 占位符、版本规则、APK 路径映射），并加入 `.gitignore` 防止 token 泄露。
- 自动按 `version` 规则（`3.{yy}.{MMddHH}`）生成或复用同名 Release（tag = version）。
- 三包路径自动识别：从 `output/apk/{test|release|coexist}/` 读取最新匹配 APK。
- Release body 自动从 `assets/updateLog.md` 提取当前版本对应日期的变更条目。
- 上传失败重试机制（网络抖动、5xx、超时）。
- 上传结果汇总输出（每包 × 每平台 成功/失败 + 下载链接）。
- 复用 `ai_tests/venv/Scripts/python.exe` 虚拟环境，避免污染公共 Python。

### 2.2 Out of Scope（不包含）

- **改造 AppUpdate 源地址到用户仓库**：本次不做，是后续独立任务（用户已明确"改造源地址是后续任务，本次不做"）。发布脚本上传目标仓库为 Gitee `Chinashitou/legado` + GitHub `syq17496152/legado`；注意：App 当前"检查更新"仍查询 Gitee `lyc486/legado`（与发布目标不一致），需后续改造 AppUpdateGitee.kt 的 URL 才能让用户检查更新下载到新版本。
- **修改 gradlew 构建流程**：构建仍由用户手动执行 `gradlew assembleDebug/assembleRelease`，脚本只负责"上传发布"环节。
- **修改 AppVariant 识别逻辑**：APK 文件名仍按现有 `releaseA/releaseS/release/legacy` 关键字识别，本次不改动。
- **CI/CD 改造**：不引入 GitHub Actions 自动构建发布，用户明确要求"本地打的包"。
- **修改 `assets/updateLog.md` 内容**：脚本只读取，不写入。
- **修改 `.gitignore` 之外的任何源码**：本次只新增脚本与配置，不改 Kotlin 源码。

---

## 3. Approach（方案）

### 3.1 Selected Approach（选定方案）

**Python 脚本调用 Gitee API + GitHub API 上传 APK 到 Release**

#### 理由

1. **复用现有 Python 环境**：`ai_tests/venv/Scripts/python.exe` 已配置好，与项目既有自动化测试体系一致，不引入新运行时。
2. **API 调用便利**：Python `requests` 库对 multipart 上传、分页查询、JSON 处理原生友好，比 PowerShell/Shell 更适合。
3. **跨平台一致**：脚本可在 Windows/Linux/macOS 运行，未来若改 CI 也无需重写。
4. **与项目其他脚本同构**：`ai_tests/scripts/` 下已有多个 Python 脚本，统一风格便于维护。
5. **本地执行可控**：用户明确"本地打的包"，Python 脚本在本地直接读 `output/apk/` 即可，无需产物传输。

#### 脚本设计要点

- **入口**：`scripts/publish_release.py`
- **配置**：`scripts/publish_config.json`（含 Gitee owner/repo、GitHub owner/repo、token 字段、version 规则、APK 路径映射）
- **依赖**：`requests`（venv 已含）
- **执行命令**：`ai_tests\venv\Scripts\python.exe scripts\publish_release.py [--version <ver>] [--dry-run]`
- **执行流程**：
  1. 读取 `publish_config.json`
  2. 计算或读取 version，匹配 `output/apk/{test|release|coexist}/` 下最新 APK
  3. 从 `assets/updateLog.md` 提取 version 对应日期的变更条目作为 Release body
  4. Gitee：调用 `POST /api/v5/repos/{owner}/{repo}/releases` 创建 Release，再 `POST .../attachments` 上传 APK
  5. GitHub：调用 `POST /repos/{owner}/{repo}/releases` 创建 Release，再 `POST .../assets` 上传 APK（需先构建 upload_url）
  6. 每步失败重试 3 次，间隔 2s 指数退避
  7. 输出汇总表（每包 × 每平台 成功/失败 + 浏览器可访问的下载链接）

### 3.2 Alternatives Considered（否决的替代方案）

| 替代方案 | 否决理由 |
|---------|---------|
| PowerShell 脚本 | 跨平台性差；multipart 文件上传在 PS 中代码冗长且易错；与项目既有 Python 脚本体系不一致 |
| GitHub Actions CI/CD | 用户明确"本地打的包"场景；引入 CI 需配置 secrets、产物上传、触发器，复杂度高于本地脚本；当前无 CI 仓库基础 |
| 手动发布 | 三包 × 双平台 = 6 次手工操作；易遗漏/上传错版本；不可重复；与项目自动化方向相悖 |
| Shell 脚本（bash） | Windows 下需 gitbash 兼容；curl multipart 在 Windows 下路径转义麻烦；错误处理不如 Python try/except 直观 |
| Gradle 任务内嵌发布 | 与构建耦合，违反"构建/发布分离"原则；调试困难；增量构建会反复触发发布 |

### 3.3 Drawbacks（已知缺点与接受理由）

| 缺点 | 接受理由 |
|------|---------|
| 需配置 Gitee + GitHub 各一个 API token | 一次性配置，写入 `publish_config.json` 并 `.gitignore`；token 仅本机持有，安全可控 |
| Gitee Release 附件可能有文件大小限制（需实测确认，传闻 100MB） | APK 通常 30-60MB，预期可达；脚本对超限错误明确报错并提示改用其他托管 |
| 依赖 Python 环境与 `requests` 库 | venv 已固化依赖，且与既有 ai_tests 同源，无新增依赖负担 |
| 网络异常需重试机制 | 脚本内置 3 次重试 + 指数退避，并区分可重试错误（5xx/超时）与不可重试错误（4xx 鉴权失败） |
| Release 创建与上传分两步，可能创建成功但上传失败产生空 Release | 脚本检测到空 Release 时支持 idempotent 重跑（同 tag 已存在则复用，已上传附件去重） |

### 3.4 Prior Art（参考先例）

- 项目既有 Python 自动化脚本目录：`ai_tests/scripts/`（如 `quick_build_install.py`、`import_rss_source.py`），同构参考其结构与错误处理风格。
- Gitee API v5 文档：`gitee.com/api/v5/swagger`，Release 接口与 GitHub 高度相似。
- GitHub API v3 文档：`docs.github.com/rest/releases`，标准 Release + Assets 上传流程。

---

## 4. Requirements（需求列表）

### 4.1 功能需求

| # | 需求 | 验收标准 |
|---|------|---------|
| F1 | 读取三包最新 APK | 按 version 模式从 `output/apk/{test,release,coexist}/` 匹配，找不到时报错并列出实际存在文件 |
| F2 | 创建/复用 Release | 按 tag=version 在 Gitee 与 GitHub 各创建一个 Release；同名 Release 已存在则复用 |
| F3 | 上传 APK 附件 | 三包各上传到 Gitee 与 GitHub 共 6 个附件；同附件已存在则跳过并提示 |
| F4 | Release body 自动生成 | 从 `assets/updateLog.md` 提取 version 对应 `**YYYY/MM/DD**` 段落作为 body；无对应条目时用默认模板"自动发布 version" |
| F5 | 失败重试 | 网络错误/5xx/超时重试 3 次，间隔 2s 指数退避；4xx 鉴权错误立即终止 |
| F6 | 结果汇总输出 | 控制台打印表格：包类型 × 平台 → 成功/失败 + 下载链接（路径模式化，不展示完整 URL 业务部分） |
| F7 | dry-run 模式 | `--dry-run` 参数：只列出待上传 APK 与目标 Release，不实际调用 API |
| F8 | 指定 version | `--version <ver>` 参数：手动指定 version；缺省时按 `3.{yy}.{MMddHH}` 自动生成（HH 取当前小时） |
| F9 | 配置文件加载 | 读取 `scripts/publish_config.json`；文件缺失时给出明确指引；token 字段为空时报错并提示如何获取 |
| F10 | token 安全 | `publish_config.json` 必须加入 `.gitignore`；脚本输出日志中 token 全部隐藏为 `***` |
| F11 | 路径安全 | 脚本日志输出中 APK 完整 URL 仅展示路径模式（`/path/{id}`），不展示业务 URL 部分 |
| F12 | 退出码 | 全部成功 → 0；部分失败 → 1；配置错误 → 2 |

### 4.2 非功能需求

| # | 需求 | 说明 |
|---|------|------|
| NF1 | 可维护性 | 脚本单文件 < 400 行；函数职责单一；关键步骤有日志 |
| NF2 | 可观测性 | 每步打印 `[stage] 描述`；失败时打印 HTTP 状态码 + 错误响应体前 200 字符 |
| NF3 | 幂等性 | 同 version 重跑不产生重复 Release/附件；支持断点续传 |
| NF4 | 安全性 | token 不入 git；不打印到日志；不写入 `ai_memory_main.md`；不通过环境变量泄漏 |
| NF5 | 兼容性 | Windows PowerShell 下可直接 `python.exe scripts\publish_release.py`；无需 bash |
| NF6 | 性能 | 三包 × 双平台串行上传，单包上传超时 300s；总耗时 < 5 分钟 |
| NF7 | 错误隔离 | 单个平台失败不影响另一平台继续上传；单个包失败不影响其他包 |

---

## 5. Scenarios（使用场景）

### 5.1 正常流程

**场景 1：首次发布新版本**

1. 用户执行 `gradlew assembleDebug assembleRelease -PcustomAppId=io.legado.app` 构建三包到 `output/apk/{test,release,coexist}/`
2. 用户在 `assets/updateLog.md` 追加 `**2026/07/29**` 段变更条目
3. 用户执行 `ai_tests\venv\Scripts\python.exe scripts\publish_release.py --version 3.26.072912`
4. 脚本读取 `publish_config.json`，匹配三个 APK，提取 updateLog body
5. 脚本在 Gitee 创建 tag=`3.26.072912` 的 Release，上传三包附件
6. 脚本在 GitHub 创建同 tag Release，上传三包附件
7. 控制台输出汇总表：6 行 全部成功 + 浏览器可访问下载链接
8. 用户在 App 内"关于 → 检查更新"测试，App 能拉到新 Release 并下载新版本 APK

**场景 2：dry-run 预检**

1. 用户执行 `python scripts\publish_release.py --version 3.26.072912 --dry-run`
2. 脚本打印：将上传的 APK 文件路径、目标 Release tag、目标 owner/repo、updateLog body 预览
3. 不发起任何 API 调用，退出码 0
4. 用户确认无误后去掉 `--dry-run` 正式执行

**场景 3：重跑（幂等）**

1. 用户首次发布时 GitHub 上传到一半中断
2. 用户重跑同 `--version`
3. 脚本检测 Gitee Release 已存在 → 复用；检测已上传附件 → 跳过并提示 "exists, skipped"
4. 仅上传 GitHub 缺失的附件
5. 全部完成，退出码 0

### 5.2 异常流程

**场景 4：APK 文件缺失**

1. 用户未执行 gradlew 构建
2. 脚本扫描 `output/apk/release/` 找不到匹配 version 的 APK
3. 打印错误：`APK not found for version=3.26.072912 in output/apk/release/`，并列出目录实际文件
4. 退出码 1，不发起任何 API 调用

**场景 5：token 无效**

1. `publish_config.json` 中 Gitee token 过期
2. 脚本调用 Gitee 创建 Release 返回 401
3. 脚本识别为 4xx 不可重试，立即终止 Gitee 部分，打印"鉴权失败，请检查 gitee token"
4. 继续执行 GitHub 部分（不受影响）
5. 退出码 1，汇总表显示 Gitee 三个失败、GitHub 三个成功

**场景 6：网络超时**

1. 上传大 APK 时网络抖动，单次请求超时 300s
2. 脚本重试，间隔 2s、4s、8s 指数退避
3. 三次重试后仍失败，标记该附件失败
4. 继续上传其他附件
5. 退出码 1，汇总表显示具体哪个附件失败，用户可重跑

**场景 7：Gitee 文件大小超限**

1. Gitee 返回 413 Payload Too Large
2. 脚本识别该错误，打印"Gitee 附件大小超限，请改用 GitHub 或拆分"
3. 跳过 Gitee 上传，继续 GitHub
4. 退出码 1

**场景 8：updateLog 无对应条目**

1. version=`3.26.072912` 但 `assets/updateLog.md` 无 `**2026/07/29**` 段
2. 脚本打印 WARN："no updateLog entry for 2026/07/29, using default body"
3. 使用默认 body："自动发布 3.26.072912"
4. 继续上传，退出码 0

**场景 9：配置文件缺失**

1. 用户首次使用，`scripts/publish_config.json` 不存在
2. 脚本打印：配置文件不存在，给出模板 JSON 示例（token 字段为 `<your-token-here>`）
3. 提示用户："将上述内容保存到 scripts/publish_config.json 并填入 token 后重跑"
4. 退出码 2

---

## 附：版本与日期

- **Spec 版本**：v1.0
- **创建日期**：2026-07-29
- **关联后续任务**：改造 AppUpdate 源地址到用户 Gitee/GitHub 仓库（独立 spec，不在本 spec 范围）
