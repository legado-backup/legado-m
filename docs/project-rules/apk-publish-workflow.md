# APK 发布流程规范

> **本规范定义 Legado 项目 APK 包发布到 Gitee/GitHub Release 的完整流程、脚本使用方法、已知问题与安全要求。**
> **何时必须加载**：APK 发布/版本发布/token 配置/发布脚本维护时。

---

## 1. 概述

### 1.1 发布目标

将本地构建的三包（test/release/coexist）APK 发布到 Gitee 和 GitHub 的 Release，让 App 内"检查更新"功能能下载到新版本。

### 1.2 平台仓库配置

| 平台 | 仓库 | 默认分支 | 状态 |
|------|------|---------|------|
| Gitee | Chinashitou/legado | main | 私有，代码已强推，分支已清理 |
| GitHub | syq17496152/legado | master | 私有，代码已同步 |

### 1.3 三包说明

| 包类型 | 包名 | 文件名规则 | 用途 |
|--------|------|-----------|------|
| 测试包 | io.legado.miss.app.debug | legado_miss_app_debug_{version}.apk | 代码优化开发测试（debug构建，含调试日志，未混淆） |
| 正式包 | io.legado.miss.app.release | legado_miss_app_{version}.apk | 生产环境发布（release构建，含ProGuard混淆+正式签名） |
| 共存包 | io.legado.app.debug | legado_legacy_app_{version}.apk | 与原版legado共存场景 |

> **注意**：test包和release包原始文件名相同（都是 legado_miss_app_{version}.apk），上传到Release时test包会加 `_debug` 后缀避免冲突。

### 1.4 版本号规则

- 格式：`3.{yy}.{MMddHH}`（如 3.26.072917 = 2026年7月29日17点构建）
- 三包取最大版本号作为 Release tag

---

## 2. 脚本与配置

### 2.1 文件清单

| 文件 | 路径 | 是否入git | 说明 |
|------|------|----------|------|
| 发布脚本 | `scripts/publish_release.py` | ✅ 是 | 主脚本，调用Gitee/GitHub API |
| 配置模板 | `scripts/publish_config.example.json` | ✅ 是 | 示例配置，不含真实token |
| 实际配置 | `scripts/publish_config.json` | ❌ 否 | 含真实token，被.gitignore排除 |

### 2.2 配置文件结构

```json
{
  "gitee": {
    "owner": "Chinashitou",
    "repo": "legado",
    "token": "<your-gitee-personal-access-token>",
    "api_base": "https://gitee.com/api/v5",
    "target_commitish": "main"
  },
  "github": {
    "owner": "syq17496152",
    "repo": "legado",
    "token": "<your-github-personal-access-token>",
    "api_base": "https://api.github.com",
    "upload_base": "https://uploads.github.com",
    "target_commitish": "master"
  },
  "apk_dirs": { "test": "...", "release": "...", "coexist": "..." },
  "apk_patterns": { "test": "...", "release": "...", "coexist": "..." },
  "update_log_path": "app/src/main/assets/updateLog.md",
  "version_pattern": "3\\.\\d{2}\\.\\d{6}",
  "retry": { "max_attempts": 3, "backoff_base": 2, "timeout": 300 }
}
```

### 2.3 token 安全要求（强制）

- 🔴 **publish_config.json 禁止提交到 git**（已被 .gitignore 第86行排除）
- 🔴 **token 不写入项目记忆文件**（仅记录"用户提供token"）
- 🔴 **token 不在输出中显示**（脚本用 hide_token 脱敏，输出格式 `ghp_***M9oc`）
- 🔴 **提交前必须验证**：`git ls-files scripts/publish_config.json` 应无输出

---

## 3. 使用方法

### 3.1 环境准备

```powershell
# Python 环境（复用ai_tests虚拟环境）
# 确保 requests + urllib3 已安装
ai_tests\venv\Scripts\python.exe -c "import requests, urllib3; print('OK')"
```

### 3.2 发布命令

```powershell
# dry-run 预览（不实际调用API）
ai_tests\venv\Scripts\python.exe scripts\publish_release.py --dry-run

# 只发布到 GitHub
ai_tests\venv\Scripts\python.exe scripts\publish_release.py --platform github

# 只发布到 Gitee（需配置 Gitee token）
ai_tests\venv\Scripts\python.exe scripts\publish_release.py --platform gitee

# 发布到两个平台
ai_tests\venv\Scripts\python.exe scripts\publish_release.py --platform both

# 指定版本号
ai_tests\venv\Scripts\python.exe scripts\publish_release.py --version 3.26.072917 --platform github
```

### 3.3 gh CLI 备选方案（大文件上传）

当 Python requests 上传大文件（51MB+）遇到 SSLEOFError 时，使用 gh CLI 替代：

```powershell
# 检查 gh 认证状态
gh auth status

# 上传指定文件（--clobber 覆盖已存在）
gh release upload <tag> "file1.apk" "file2.apk" --clobber -R syq17496152/legado

# 查看 Release
gh release view <tag> -R syq17496152/legado --json assets,name,tagName,url

# 删除指定 asset
gh release delete-asset <tag> <asset_name> -R syq17496152/legado --yes
```

---

## 4. 已知问题与解决方案

### 4.1 SSL 证书验证失败（uploads.github.com）

- **现象**：`SSLError(SSLCertVerificationError: certificate verify failed: unable to get local issuer certificate)`
- **根因**：Windows 环境 uploads.github.com 证书链验证失败（api.github.com 正常，疑似网络代理拦截）
- **临时方案**：脚本已禁用 SSL 验证（`SESSION.verify = False`）+ 过滤 InsecureRequestWarning
- **TODO**：排查网络环境（代理/防火墙）根因，恢复严格 SSL 验证

### 4.2 大文件上传 SSLEOFError

- **现象**：`SSLError(SSLEOFError(8, 'EOF occurred in violation of protocol'))`，51MB+ 文件上传失败，20MB 文件正常
- **根因**：网络不稳定，大文件传输过程中连接被中断
- **方案**：使用 gh CLI 替代 Python requests 上传大文件（gh CLI 网络容错更好）

### 4.3 test 包与 release 包文件名冲突

- **现象**：test 包和 release 包原始文件名都是 `legado_miss_app_{version}.apk`，上传到同一 Release 会互相覆盖
- **方案**：脚本新增 `get_upload_name` 函数，test 包上传时加 `_debug` 后缀
  - test → `legado_miss_app_debug_{version}.apk`
  - release → `legado_miss_app_{version}.apk`（保持原名）
  - coexist → `legado_legacy_app_{version}.apk`（保持原名）

### 4.4 read_config 校验所有平台 token

- **现象**：`--platform github` 时仍校验 gitee token，未配置则退出
- **方案**：read_config 接受 platform 参数，只校验指定平台的 token

---

## 5. 发布流程

### 5.1 标准发布流程

1. **构建三包**：`gradlew assembleDebug` + `gradlew assembleRelease` + `gradlew assembleCoexist`
2. **更新日志**：编译前更新 `app/src/main/assets/updateLog.md`
3. **libcronet.so 动态下载验证（强制）**：每包构建后必须验证 APK 不含 libcronet.so（动态下载模式），含 so 则禁止发布
   ```powershell
   # 验证脚本（每个 APK 都需验证）
   Add-Type -AssemblyName System.IO.Compression.FileSystem
   $tmpZip = "$env:TEMP\check_apk.zip"
   Copy-Item "<APK路径>" $tmpZip -Force
   $zip = [System.IO.Compression.ZipFile]::OpenRead($tmpZip)
   $so = $zip.Entries | Where-Object { $_.FullName -like "lib/arm64-v8a/libcronet*" }
   if ($so) { Write-Host "[FAIL] libcronet.so found in APK!"; exit 1 } else { Write-Host "[OK] No libcronet.so (dynamic download mode)" }
   $zip.Dispose(); Remove-Item $tmpZip -Force
   ```
   > 🔴 **强制要求**：三包（test/release/coexist）都必须不含 libcronet.so（动态下载模式），so 在运行时从远程下载到应用私有目录。详见 [package-naming.md "libcronet.so 动态下载规范"](./package-naming.md)
4. **dry-run 预览**：`python scripts/publish_release.py --dry-run`
5. **实际发布**：
   - GitHub：`python scripts/publish_release.py --platform github`
   - 大文件失败时用 gh CLI 补传：`gh release upload <tag> <files> --clobber -R syq17496152/legado`
6. **验证**：`gh release view <tag> -R syq17496152/legado --json assets`
7. **Gitee 发布**：配置 Gitee token 后 `python scripts/publish_release.py --platform gitee`

### 5.2 Release body 自动提取

脚本从 `app/src/main/assets/updateLog.md` 自动提取对应日期的日志条目作为 Release body：
- 版本号 `3.26.072917` → 日期 `2026/07/29`
- 查找 `**2026/07/29**` 标题，提取到下一个日期标题前的内容

---

## 6. 后续优化点

1. **AppVariant 识别缺陷**：当前 APK 文件名不含 releaseA/releaseS/release 标识，无法从文件名区分正式包变体
2. **检查更新源地址不一致**：发布脚本上传到 Gitee `Chinashitou/legado`，但 App 当前"检查更新"仍查询 Gitee `lyc486/legado`，需改造 AppUpdateGitee.kt
3. **SSL 验证根因排查**：uploads.github.com 证书链验证失败的根因（网络代理/防火墙）
4. **脚本集成 gh CLI**：大文件上传自动 fallback 到 gh CLI，无需手动操作
5. **GitHub Actions CI/CD**：未来可集成到 CI/CD 自动发布

---

## 7. 反模式

- ❌ 将 publish_config.json（含token）提交到 git
- ❌ 在输出/日志/记忆文件中明文记录 token
- ❌ 用 Python requests 强行上传大文件（SSLEOFError）而不切换 gh CLI
- ❌ test 包和 release 包用相同文件名上传到同一 Release（互相覆盖）
- ❌ `--platform github` 时校验 gitee token 导致无法发布
- ❌ 发布前不更新 updateLog.md（Release body 会回退到默认文案）
