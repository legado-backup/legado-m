# Design: APK 集成发布到 Gitee/GitHub Release

## 1. Technical Approach

### 1.1 总体方案

采用 Python 脚本作为发布工具,调用 Gitee API v5 和 GitHub API v3,将本地构建产出的三个 APK 包(test / release / coexist)上传到对应仓库的 Release 资产中,使 App 内"检查更新"功能能够拉取到最新版本。

### 1.2 运行环境与依赖

- **Python 解释器**:复用项目已有虚拟环境 `ai_tests/venv/Scripts/python.exe`,不引入新的全局 Python 依赖。
- **第三方库**:仅使用 Python 标准库(`os` / `sys` / `json` / `re` / `requests` / `pathlib`)。若 `requests` 未在 venv 中安装,需在脚本首次运行前通过 `ai_tests/venv/Scripts/pip.exe install requests` 安装。
- **配置文件**:`scripts/publish_config.json`,存储 Gitee access_token 和 GitHub personal access token,该文件加入 `.gitignore` 防止泄露。

### 1.3 APK 命名与定位

APK 命名规则:`legado_{miss|legacy}_app_{version}.apk`,其中 version 格式为 `3.{yy}.{MMddHH}`(示例:`3.26.072912`)。

三个包的输出位置:
- 测试包(debug):`output/apk/test/legado_miss_app_{version}.apk`
- 正式包(release):`output/apk/release/legado_miss_app_{version}.apk`
- 共存包(legacy):`output/apk/coexist/legado_legacy_app_{version}.apk`

脚本通过扫描上述三个目录,按文件名匹配 `legado_*_app_*.apk` 模式,选取每个目录下版本号最大的文件作为待发布产物,并从文件名正则提取版本号作为 Release 的 tag 与 title。

### 1.4 更新日志读取

更新日志来源于 `assets/updateLog.md`,文件格式为以 `**YYYY/MM/DD**` 作为日期标题、下方跟若干条目。脚本读取该文件,提取最新一个日期标题及其下方所有条目(直到下一个日期标题或文件结束),作为 Release 的 body 文本。

### 1.5 API 调用流程

**Gitee API v5**(发布脚本上传目标仓库;注意:App 当前"检查更新"仍走 lyc486/legado,改造源地址是后续任务):
1. 创建 Release:`POST https://gitee.com/api/v5/repos/{owner}/{repo}/releases`,body 含 `access_token`、`tag_name`、`name`、`body`、`target_commitish`(Gitee 默认分支为 main)。
2. 上传 Asset:`POST https://gitee.com/api/v5/repos/{owner}/{repo}/releases/{release_id}/attach_files`,multipart/form-data 上传文件,需带 `access_token`。
3. 仓库标识:owner=`Chinashitou`,repo=`legado`。

**GitHub API v3**:
1. 创建 Release:`POST https://api.github.com/repos/{owner}/{repo}/releases`,Header `Authorization: token {pat}`,body 含 `tag_name`、`name`、`body`、`target_commitish`(GitHub 默认分支为 master)。
2. 上传 Asset:`POST https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets?name={name}`,Header `Authorization: token {pat}`、`Content-Type: application/octet-stream`,body 为 APK 二进制。
3. 仓库标识:owner=`syq17496152`,repo=`legado`。

### 1.6 已存在 Release 的处理

脚本在创建 Release 前先调用 GET 接口查询目标 tag 是否已存在:
- 不存在 → 正常创建 Release,再上传三包。
- 已存在 → 复用已有 release_id,检查已有 asset 列表,跳过同名 asset,仅上传缺失的包,避免重复上传报错。

### 1.7 错误处理与输出

- 任意一步 API 调用失败(非 2xx)即打印 HTTP 状态码、响应体片段(截断避免泄露 token)、失败阶段,并以非零退出码结束。
- 全部成功后输出:Gitee Release URL、GitHub Release URL、三个 APK 在两端的下载链接。
- token 仅在内存中使用,不写入日志、不打印到控制台。

## 2. Architecture Decisions

### AD-01: 使用 Python 脚本(非 PowerShell/Shell)
- **Context**: 项目已存在 `ai_tests/venv` Python 虚拟环境,且 `ai_tests/scripts/` 下已有多个 Python 自动化脚本;Windows 为主要开发环境,但脚本需可移植。
- **Concern**: 跨平台兼容性、与现有自动化体系一致性、HTTP 多部分上传实现复杂度。
- **Decision**: 选用 Python 实现 `scripts/publish_release.py`,复用 `ai_tests/venv` 解释器。
- **Goal**: 与项目现有 Python 自动化栈统一,跨平台可运行,HTTP 上传用 `requests` 简化实现。
- **Tradeoff**: 需确保 venv 中已安装 `requests`;相比纯 PowerShell 多一层依赖,但可读性与可维护性显著更优。
- **Status**: Accepted

### AD-02: 配置文件存储 API token(非环境变量)
- **Context**: 需要 Gitee access_token 与 GitHub PAT 两个凭证;脚本由本机用户手动触发,非 CI 环境。
- **Concern**: 凭证安全、使用便捷、防止误提交到 git。
- **Decision**: 使用 `scripts/publish_config.json` 存储 token,并将该文件加入 `.gitignore`。
- **Goal**: 用户一次配置长期复用,避免每次发布重复输入;防止凭证进入版本库。
- **Tradeoff**: 配置文件丢失需重新填写;相比环境变量方式略不安全(明文文件),但通过 `.gitignore` 与本地存储控制风险,换取使用便利。
- **Status**: Accepted

### AD-03: 支持三包分别上传(非合并上传)
- **Context**: 项目存在测试包、正式包、共存包三种构建产物,对应不同包名与用途;App 内检查更新仅需正式包,但其他包供开发者与多 AI 并发测试使用。
- **Concern**: Release 资产完整性、用户可按需下载、避免包名混淆。
- **Decision**: 三个 APK 分别上传到同一个 Release 下,文件名保留 `test`/`release`/`coexist` 语义(通过 `legado_miss`/`legado_legacy` 前缀与目录区分)。
- **Goal**: 单个 Release 同时承载三包,用户与开发者按需取用。
- **Tradeoff**: 单次发布上传 3 个文件,Release 资产略多;但避免多 Release 维护成本,且与现有打包流程一一对应。
- **Status**: Accepted

### AD-04: 版本号从 APK 文件名提取(非手动输入)
- **Context**: APK 文件名已严格遵循 `legado_{miss|legacy}_app_{version}.apk` 规范,version 格式 `3.{yy}.{MMddHH}` 由打包脚本保证。
- **Concern**: 避免人为输入版本号导致 tag 与实际 APK 不一致;减少发布步骤。
- **Decision**: 脚本扫描 `output/apk/{test,release,coexist}/` 目录,正则匹配文件名提取 version,作为 Release tag 与 title。
- **Goal**: 自动化、零输入发布,tag 与 APK 版本严格一致。
- **Tradeoff**: 强依赖打包脚本的命名规范,若命名异常则脚本报错;但项目打包脚本已固化该规则,风险可控。
- **Status**: Accepted

### AD-05: Release 已存在时追加 asset(非报错退出)
- **Context**: 发布过程中可能因网络抖动导致部分 asset 上传失败需要重试;也可能需要补传遗漏的包。
- **Concern**: 重试友好性、避免重复创建 Release、避免重复上传同名 asset。
- **Decision**: 创建 Release 前先 GET 查询 tag 是否存在;存在则复用 release_id,对比已有 asset 名称跳过同名,仅上传缺失包。
- **Goal**: 支持断点续传与补传,发布失败可安全重跑。
- **Tradeoff**: 查询+对比逻辑增加少量代码复杂度;但显著提升发布鲁棒性,值得。
- **Status**: Accepted

### AD-06: 更新日志从 updateLog.md 自动读取(非手动输入)
- **Context**: 项目已有 `assets/updateLog.md` 作为版本交付同步的权威日志,格式为 `**YYYY/MM/DD**` 标题 + 条目列表;版本交付同步规范要求每次代码变更同步更新该文件。
- **Concern**: Release body 与项目日志一致性、避免重复维护两份变更说明。
- **Decision**: 脚本读取 `assets/updateLog.md`,提取最新日期标题及其下条目作为 Release body。
- **Goal**: Release 说明与项目更新日志单一数据源,零重复维护。
- **Tradeoff**: 强依赖 updateLog.md 格式规范;若格式异常则 body 为空并告警,但不会阻断发布。
- **Status**: Accepted

## 3. Data Flow

1. **启动与配置加载**:脚本启动后读取 `scripts/publish_config.json`,解析出 Gitee access_token 与 GitHub PAT,加载到内存;若文件缺失或字段不完整,立即报错退出。
2. **APK 发现**:扫描 `output/apk/test/`、`output/apk/release/`、`output/apk/coexist/` 三个目录,匹配 `legado_*_app_*.apk`,从文件名正则提取 version;对每个目录选取 version 最大的文件,得到三个待上传 APK 路径与统一版本号。
3. **更新日志提取**:读取 `assets/updateLog.md`,定位最后一个 `**YYYY/MM/DD**` 标题,截取该标题至文件末尾(或下一个日期标题)的内容作为 Release body。
4. **Gitee Release 创建**:用 version 作为 tag_name 与 name、updateLog 作为 body,调用 Gitee 创建 Release 接口;若 tag 已存在则查询获取已有 release_id。
5. **Gitee Asset 上传**:对三个 APK 依次调用 Gitee attach_files 接口上传,跳过已存在同名 asset;记录每个 asset 的浏览器下载 URL。
6. **GitHub Release 创建**:同 tag/name/body,调用 GitHub 创建 Release 接口;若 tag 已存在则查询获取 release_id。
7. **GitHub Asset 上传**:对三个 APK 依次调用 GitHub assets 上传接口(uploads.github.com 域名),跳过已存在同名 asset;记录每个 asset 的 download_url 与 api_url。
8. **结果输出**:打印 Gitee Release URL、GitHub Release URL、三包在两端的下载链接;非零退出码表示失败,零退出码表示全部成功。

## 4. File Changes

### 4.1 新增文件

| 文件路径 | 用途 |
|---------|------|
| `scripts/publish_release.py` | 发布主脚本,实现 APK 扫描、日志提取、双平台 Release 创建与 Asset 上传 |
| `scripts/publish_config.json` | 存储 Gitee access_token 与 GitHub PAT 的本地配置文件(不提交) |
| `scripts/publish_config.example.json` | 配置文件示例(不含真实 token),供新用户参考,可提交到版本库 |

### 4.2 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `.gitignore` | 新增 `scripts/publish_config.json` 规则,防止真实 token 被误提交;不忽略 `publish_config.example.json` |
