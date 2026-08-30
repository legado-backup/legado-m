# APK 发布流程规范

> **本规范定义 Legado 项目 APK 包一键发布（版本确认→三包构建→校验强化→Release 发布→git tag）的完整流程、脚本使用方法、已知问题与安全要求。**
> **何时必须加载**：APK 发布/版本发布/token 配置/发布脚本维护时。

---

## 1. 概述

### 1.1 发布目标

单命令完成从源码到可回滚版本交付的全流程：本地构建三包（test/release/coexist）→ 自动化校验 → 发布到 Gitee 和 GitHub 的 Release → 打 git tag 形成回滚锚点，让 App 内"检查更新"功能能下载到新版本。

### 1.2 平台仓库配置

| 平台 | 仓库 | 默认分支 | 状态 |
|------|------|---------|------|
| Gitee | Chinashitou/legado | main | 私有，代码已强推，分支已清理 |
| GitHub | syq17496152/legado | master | 私有，代码已同步 |

### 1.3 三包说明与包名禁用场景

| 包类型 | 包名 | 文件名规则 | 用途 |
|--------|------|-----------|------|
| 测试包 | io.legado.miss.app.debug | legado_miss_app_debug_{version}.apk | 代码优化开发测试（debug构建，含调试日志，未混淆） |
| 正式包 | io.legado.miss.app.release | legado_miss_app_{version}.apk | 生产环境发布（release构建，含ProGuard混淆+正式签名） |
| 共存包 | io.legado.app.debug | legado_legacy_app_{version}.apk | 与原版legado共存场景 |

**包名禁用场景（强制）**：

- 🟡 **test 包上传带 `_debug` 后缀**：一键编排器 Stage4 三包全上传，test 包经 get_upload_name 重命名为 `legado_miss_app_debug_{version}.apk` 防与正式包同名覆盖（2026-08-30 用户裁决恢复上传）；上传前逐包包名断言防混发
- 🔴 test 包仅用于代码优化开发测试；书源/订阅源 Skill 真机测试必须用**正式包**；与原版共存场景用**共存包**
- 🔴 禁止同一模拟器实例同时操作多个包（Activity 抢占）

### 1.4 版本号规则

- 格式：`3.{yy}.{MMddHH}`（如 3.26.083020 = 2026年8月30日20点构建），6 位日期时段与 `build.gradle` 的 `releaseTime()` 及 `version_pattern` 同构
- Stage1 显式传 `--version` 或按公式自动 bump
- Stage5 生成 git tag = 版本号

---

## 2. 单命令一键发布（主线）

### 2.1 发布入口

```powershell
# 方式一：项目根薄壳入口（双击或命令行，透传全部参数）
publish.bat

# 方式二：直接调编排器
ai_tests\venv\Scripts\python.exe scripts\publish_release.py
```

### 2.2 五阶段流程

| 阶段 | 内容 | 关键点 |
|------|------|--------|
| Stage1 版本确认 | `--version` 显式传入，否则按公式 bump（3.yyMMddHH 型 6 位） | 与 build.gradle releaseTime() 同构 |
| Stage2 三包构建 | subprocess 依次调 build-legado.bat（test/release/coexist），**显式版本第 3 参保证三包同版本** | 每包后 bat 内嵌 daemon 清场 |
| Stage3 校验强化 | 三包齐全 / libcronet.so 内置 / apksigner 验签 / aapt2 包名版本一致性 / updateLog 当日条目 | **全部 fail-fast exit**；缺包从 WARN 升级为 exit；updateLog 缺当日条目直接拦截（无回退文案） |
| Stage4 Release 发布 | GitHub 层走 gh CLI 上传三包（test 包带 `_debug` 后缀防同名冲突）；Gitee 层仍走 requests | **L2 真机门禁**：交互确认默认 N |
| Stage5 git tag | tag = 版本号，push 前人工确认 | 版本回滚锚点 |

### 2.3 人工确认点

| 确认点 | 交互行为 | 非交互（AI 代答）方式 |
|--------|---------|---------------------|
| Stage4 前 L2 真机门禁 | 交互确认，**默认 N**（不确认则中止） | `--l2-evidence <路径>` 绑定当日 L2 报告（校验文件存在 + 当日 mtime） |
| Stage5 tag push 前 | 人工确认 | `--confirm-stage tag` |
| Stage2 构建确认 | 交互确认 | `--confirm-stage build` |

> **注意**：`--confirm-stage` 仅覆盖构建/tag 确认点，**L2 真机门禁不适用此参数**——无任何 flag 可跳过 L2 门禁，AI 代答只能通过 `--l2-evidence` 提交当日真机验证报告。

### 2.4 参数表

| 参数 | 说明 |
|------|------|
| `publish.bat` | 项目根薄壳入口，双击/命令行，透传全部参数 |
| `--version <ver>` | 指定版本号（如 3.26.083020）；缺省按公式 bump |
| `--dry-run` | 全流程模拟预览，无任何副作用（配置缺失时可退回 example 配置） |
| `--platform gitee\|github\|both` | 发布平台，默认 `both` |
| `--config <path>` | 配置文件路径，默认 `scripts/publish_config.json` |
| `--confirm-stage build\|tag` | 非交互确认续跑（可重复），AI 代答场景；L2 门禁不适用此参数 |
| `--l2-evidence <路径>` | AI 代答 L2 门禁时必传；要求文件存在且修改时间为当日 |

### 2.5 tag 回滚方式

```powershell
# tag 即版本号，任意版本可一键回滚
git checkout <版本号>    # 如 git checkout 3.26.083020
```

### 2.6 Release body 自动提取

脚本从 `app/src/main/assets/updateLog.md` 自动提取对应日期的日志条目作为 Release body：
- 版本号 `3.26.083020` → 日期 `2026/08/30`
- 查找 `**2026/08/30**` 标题，提取到下一个日期标题前的内容
- **未找到当日条目时在 Stage3 直接 fail-fast 拦截**（旧版"回退为自动发布文案"机制已废除）

### 2.7 验证状态

一键编排器**已建立**：L1 `--dry-run` 全流程通过 + R2 负向测试通过；L2 真机演练与 L3 真实发版演练**进行中**（未完成，勿视为已验证闭环）。

---

## 3. 脚本与配置

### 3.1 文件清单

| 文件 | 路径 | 是否入git | 说明 |
|------|------|----------|------|
| 发布编排器 | `scripts/publish_release.py` | ✅ 是 | 一键五阶段主脚本：版本确认→三包构建→校验强化→gh release→git tag |
| 薄壳入口 | `publish.bat` | ✅ 是 | 项目根，双击/命令行，透传全部参数 |
| 配置模板 | `scripts/publish_config.example.json` | ✅ 是 | 示例配置，不含真实token |
| 实际配置 | `scripts/publish_config.json` | ❌ 否 | 含真实token，被.gitignore排除 |

### 3.2 配置文件结构

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

### 3.3 token 安全要求（强制）

- 🔴 **publish_config.json 禁止提交到 git**（已被 .gitignore 第86行排除）
- 🔴 **token 不写入项目记忆文件**（仅记录"用户提供token"）
- 🔴 **token 不在输出中显示**（脚本用 hide_token 脱敏，输出格式 `ghp_***M9oc`）
- 🔴 **提交前必须验证**：`git ls-files scripts/publish_config.json` 应无输出

---

## 4. 已知问题与解决方案

### 4.1 SSL 证书验证失败（uploads.github.com）→ GitHub 层已规避

- **现象**：`SSLError(SSLCertVerificationError: certificate verify failed)`（uploads.github.com 证书链验证失败，api.github.com 正常，疑似网络代理拦截）
- **现状**：**GitHub 层上传已改走 gh CLI，不再直连 uploads.github.com，此坑在 GitHub 层已规避**
- **残留 TODO**：Gitee 层仍走 requests（Windows 环境 Gitee 偶发同类问题，临时禁用 SSL 验证 + 过滤 InsecureRequestWarning，见 `scripts/publish_release.py` SESSION 初始化注释），后续排查网络环境（代理/防火墙）根因后恢复严格验证

### 4.2 大文件上传 SSLEOFError → gh CLI 已规避

- **现象**：`SSLEOFError(8, 'EOF occurred in violation of protocol')`，51MB+ 文件上传失败，20MB 文件正常（根因：网络不稳定，大文件传输连接被中断）
- **现状**：**GitHub 层已内化 gh CLI 上传**（网络容错更好），无需手动补传；Gitee 层仍走 requests

### 4.3 检查更新源地址不一致 → 已修复

- **历史问题**：发布脚本上传到 Gitee `Chinashitou/legado`，但 App"检查更新"查询的是 Gitee `lyc486/legado`
- **现状**：**已修复**，`AppUpdateGitee.kt` 检查更新源已修正为 `Chinashitou/legado`，与发布目标一致，检查更新 bug 闭环

### 4.4 test 包与 release 包文件名冲突 → 已消除

- **历史问题**：test 包和 release 包原始文件名都是 `legado_miss_app_{version}.apk`，上传同一 Release 互相覆盖（历史上传方案为 `get_upload_name` 给 test 包加 `_debug` 后缀）
- **现状**：test 包恢复上传（2026-08-30 用户裁决），经 get_upload_name 加 `_debug` 后缀重命名（`legado_miss_app_debug_{version}.apk`），与正式包不同名，冲突消除

### 4.5 read_config 平台 token 校验

- `--platform github` 时只校验 GitHub token，不强制要求 Gitee token（read_config 接受 platform 参数）

### 4.6 build-legado.bat 延迟扩展缺失（已修复）

- **历史问题**：`EnableDelayedExpansion` 缺失导致 libcronet.so 校验为死代码，从未真正执行
- **现状**：**已修复**，校验真正生效（cronet-bundled 内置模式：APK 必须含 libcronet.so，详见 `gradle/libs.versions.toml` cronetBundled 注释）；构建成功时输出 `[ARTIFACT] <产物绝对路径>` 机器可读行供编排器解析

### 4.7 后续优化点

1. **AppVariant 识别**：APK 文件名不含 releaseA/releaseS/release 标识，无法从文件名区分正式包变体
2. **Gitee 层 SSL 根因排查**：网络代理/防火墙根因确认后恢复严格 SSL 验证
3. **CI/CD 集成**：未来可评估 GitHub Actions 自动发布（当前交付链路为本地一键编排）

---

## 5. 历史沿革（旧七步标准发布）

2026-08 一键编排器上线前，发布为手动七步流程：

1. 手动依次构建三包（`build-legado.bat debug` / `release` / `debug io.legado.app`，共存包靠 `-PcustomAppId` 实现）
2. 编译前更新 updateLog.md
3. 手动 PowerShell 脚本校验每包 libcronet.so（cronet-bundled 内置模式：APK 必须含 so，Cronet 150 时代"动态下载模式"已翻转）
4. `--dry-run` 预览
5. requests 上传 GitHub（大文件 51MB+ 失败时手动 gh CLI 补传：`gh release upload <tag> <files> --clobber`）
6. `gh release view` 验证
7. 配置 Gitee token 后单独发布 Gitee

该流程已被一键编排器（§2）取代：libcronet.so 校验、apksigner 验签、包名版本一致性校验均已内化为 Stage3 自动校验；gh CLI 由手动备选转正为 GitHub 层主通道；三包同版本由显式版本参数保证；test 包不再上传 Release。此节仅作历史沿革保留。

---

## 6. 反模式

- ❌ 将 publish_config.json（含token）提交到 git
- ❌ 在输出/日志/记忆文件中明文记录 token
- ❌ 用 Python requests 强行上传 GitHub 大文件（SSLEOFError）——GitHub 层必须走 gh CLI
- ❌ test 包和 release 包用相同文件名上传到同一 Release（互相覆盖）——test 包禁止上传 Release
- ❌ `--platform github` 时校验 gitee token 导致无法发布
- ❌ 发布前不更新 updateLog.md——**缺当日条目会被 Stage3 fail-fast 拦截，禁止手动构造"自动发布"回退文案**
- ❌ **禁止绕过 L2 真机门禁（无任何 flag 可跳过；AI 代答只能用 `--l2-evidence` 绑定当日真机验证报告）**
- ❌ **禁止上传 test 包到 Release（包名禁令，Stage4 仅接受 release + coexist 产物）**
