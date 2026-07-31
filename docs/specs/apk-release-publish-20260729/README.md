# APK 发布到 Gitee + GitHub Release

> 状态：🔄 设计中
> 创建时间：2026-07-29
> 任务来源：用户需求"如何将本地打的包集成发布到 gitee 和 github 上面"

## 功能概述

用户本地通过 gradlew 构建三包（测试包/正式包/共存包）后，通过 Python 脚本自动化发布到 Gitee 和 GitHub 的 Release，让 App 内"检查更新"功能能下载到新版本。

## 核心能力

1. **一键发布三包**：脚本自动读取 output/apk/{test,release,coexist}/ 下的 APK 文件
2. **双平台发布**：同时发布到 Gitee（Chinashitou/legado）和 GitHub（syq17496152/legado）
3. **版本号自动提取**：从 APK 文件名解析版本号作为 Release tag
4. **Release 管理**：自动创建 Release（已存在则追加 asset）
5. **Token 安全**：API token 存配置文件，不入 git
6. **更新日志自动读取**：从 assets/updateLog.md 读取最新日期的日志作为 Release body

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格（Intent/Scope/Approach/Requirements/Scenarios） |
| [design.md](./design.md) | 技术设计（架构决策/数据流/文件变更） |
| [tasks.md](./tasks.md) | 任务清单 |

## 背景

### 当前检查更新逻辑

- 入口：`AboutFragment.checkUpdate()` 调用 `AppUpdate.giteeUpdate.check()`
- 实际使用 Gitee 源：`gitee.com/api/v5/repos/lyc486/legado/releases`
- AppUpdateGitHub 未被使用，URL 还指向原版 `gedoor/legado`
- AppVariant 识别基于 APK 文件名（releaseA/releaseS/release 关键字）

### 当前 APK 命名规则

- 格式：`legado_{miss|legacy}_app_{version}.apk`
- version = `3.{yy}.{MMddHH}`，如 `3.26.072912`
- 三包输出位置：
  - 测试包：`output/apk/test/legado_miss_app_{version}.apk`
  - 正式包：`output/apk/release/legado_miss_app_{version}.apk`
  - 共存包：`output/apk/coexist/legado_legacy_app_{version}.apk`

### 已知问题

1. **AppVariant 识别缺陷**：当前 APK 文件名不含 releaseA/releaseS/release 标识，所有包都会被识别为 OFFICIAL，检查更新时无法区分包类型
2. **contributors_url BUG**：AboutFragment 引用 `R.string.contributors_url` 但 strings.xml 未定义，点击"贡献者"会崩溃（本任务不修复，记录待后续处理）

## 范围边界

### 包含

- Python 发布脚本（读取 APK + 调用 API + 上传）
- 配置文件模板（token 配置，不入 git）
- 使用说明文档

### 不包含

- 检查更新源地址改造（用户明确说"然后再说改造源地址到我的地方"，后续任务）
- 构建流程修改（用户已能打三包）
- GitHub Actions CI/CD（用户说"本地打的包"，是本地脚本）
- AppVariant 识别逻辑修复（后续任务）
- contributors_url BUG 修复（后续任务）

## 后续优化点

> 以下问题不在本次实施范围，但已识别，待后续优化：

1. **AppVariant 识别缺陷**：当前 APK 文件名 `legado_{miss|legacy}_app_{version}.apk` 不含 releaseA/releaseS/release 标识，AppReleaseInfo.kt 的 assetToAppReleaseInfo 会把所有包识别为 OFFICIAL，检查更新时无法区分包类型（测试包/正式包/共存包）。后续需修改 APK 命名规则或 AppVariant 识别逻辑。

2. **检查更新源地址与发布目标不一致**：发布脚本上传到 Gitee `Chinashitou/legado`，但 App 当前"检查更新"仍查询 Gitee `lyc486/legado`（AppUpdateGitee.kt L31-33）。后续需改造 AppUpdateGitee.kt 的 URL 为 `Chinashitou/legado`，用户检查更新才能下载到新版本。

3. **contributors_url BUG**：AboutFragment.kt L58 引用 `R.string.contributors_url`，但 strings.xml 未定义此字符串，点击"贡献者"项会崩溃（资源找不到）。后续需添加字符串定义或移除引用。

4. **GitHub Actions CI/CD**：后续可考虑用 GitHub Actions 自动构建+发布，减少本地构建+手动运行脚本的操作。

5. **Gitee 默认分支 main / GitHub 默认分支 master**：发布脚本需区分两个平台的 target_commitish（Gitee 用 main，GitHub 用 master），已在 design.md 中说明。

## 平台仓库配置

| 平台 | 仓库 | 默认分支 | 状态 |
|------|------|---------|------|
| Gitee | Chinashitou/legado | main | 已改私有，代码已强推，分支已清理（只剩main） |
| GitHub | syq17496152/legado | master | 已有 remote（origin），代码已同步 |
