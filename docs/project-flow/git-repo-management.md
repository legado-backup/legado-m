# Git 仓库管理规范

> 本文档定义 Legado 项目的 Git 仓库配置、.gitignore 规则、提交流程和推送策略。

---

## 1. 仓库信息

| 项目 | 值 |
|------|-----|
| 远程仓库 | `https://github.com/syq17496152/legado.git` |
| 可见性 | 私有（private） |
| 主分支 | `master` |
| 首次提交 | 2497 个文件，2879 个 Git 对象，8.73 MiB |

---

## 2. 目录分类与提交策略

### 2.1 必须提交（核心源码）

| 目录/文件 | 内容 | 估算文件数 |
|-----------|------|-----------|
| `app/src/` | Android 主应用 Kotlin 源码、资源、清单 | 300+ |
| `app/build.gradle` | 应用构建配置 | 1 |
| `app/proguard-rules.pro` | ProGuard 混淆规则 | 1 |
| `app/google-services.json` | Google Services 配置 | 1 |
| `modules/book/` | EPUB/UMD 书籍解析模块 | 60+ |
| `modules/rhino/` | Rhino JS 引擎模块（含 JAR） | 20+ |
| `modules/web/` | Vue3 Web 管理前端源码 | 30+ |
| `build.gradle` / `settings.gradle` / `gradle.properties` | 根构建配置 | 3 |
| `gradle/wrapper/` | Gradle Wrapper | 3 |
| `docs/` | 项目文档（架构、规范、功能设计） | 100+ |
| `.github/` | CI/CD 工作流、Issue 模板 | 10 |
| `.trae/skills/` | AI Skill 配置和参考文档 | 150+ |
| `AGENTS.md` / `README.md` / `LICENSE` | 项目入口文档 | 3+ |

### 2.2 禁止提交（已加入 .gitignore）

| 目录/文件 | 原因 | 预估大小 |
|-----------|------|---------|
| `temp/` | 含完整 Android SDK（数百 MB）、Gradle 缓存、社区书源 JSON 缓存 | >500 MB |
| `output/` | 书源/订阅源测试输出和报告 | 数十 MB |
| `__pycache__/` / `*.pyc` | Python 编译缓存 | 小 |
| `build/` / `.gradle/` | 构建产物 | 数百 MB |
| `.idea/` / `.vscode/` | IDE 配置 | 小 |
| `nul` | Windows 特殊设备名异常文件 | 0 |
| `.trae/skills/*/output/` | Skill 运行时输出 | 数 MB |
| `.trae/skills/*/scripts/reports/` | Python 测试报告 | 数 MB |
| `.trae/skills/*/data/*.db` | SQLite 数据库 | 数 MB |
| `*.log` | 日志文件 | 不定 |

---

## 3. .gitignore 完整规则

```gitignore
# Android / Gradle
*.iml
.gradle
local.properties
.DS_Store
/build
build/
/captures
.externalNativeBuild
/release
/tmp
node_modules/
/app/app
/app/google
/app/gradle.properties
package-lock.json
.idea/
.kotlin/
.cxx
.vscode

# Python
__pycache__/
*.pyc
*.pyo
.venv/

# legado-jvm 构建产物
tools/legado-jvm/build/
tools/legado-jvm/.gradle/

# 临时目录和输出
temp/
output/

# 异常文件
nul

# Skill 运行时产物
.trae/skills/*/output/
.trae/skills/*/scripts/reports/
.trae/skills/*/scripts/.coverage
.trae/skills/*/data/*.db
.trae/skills/*/scripts/*.log

# 通用日志
*.log
```

---

## 4. 提交流程

### 4.1 首次初始化（已完成）

```bash
# 1. 初始化仓库（如已存在则跳过）
git init

# 2. 确认 .gitignore 已包含上述规则

# 3. 添加远程仓库
git remote add origin https://github.com/syq17496152/legado.git

# 4. 暂存所有必要文件（.gitignore 自动过滤）
git add -A

# 5. 提交
git commit -m "Initial commit: Legado阅读App完整源码及Skill工具链"

# 6. 重命名分支为 master 并推送
git branch -M master
git push -u origin master
```

### 4.2 日常提交流程

```bash
# 1. 查看变更
git status
git diff

# 2. 暂存指定文件（避免 git add -A 误加敏感文件）
git add <具体文件路径>

# 3. 提交（遵循 Conventional Commits 格式）
git commit -m "feat: 添加XXX功能"
git commit -m "fix: 修复XXX问题"
git commit -m "docs: 更新XXX文档"
git commit -m "refactor: 重构XXX模块"

# 4. 推送
git push
```

### 4.3 Commit 消息规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 添加TTS语音选择功能` |
| `fix:` | Bug 修复 | `fix: 修复搜索结果分页异常` |
| `docs:` | 文档变更 | `docs: 更新规则引擎文档` |
| `refactor:` | 代码重构 | `refactor: 提取书源解析公共逻辑` |
| `style:` | 格式调整 | `style: 统一Kotlin缩进为4空格` |
| `test:` | 测试相关 | `test: 添加AnalyzeRule单元测试` |
| `chore:` | 构建/工具 | `chore: 升级Gradle到8.5` |
| `skill:` | Skill 变更 | `skill: 新增反爬陷阱检查规则` |

---

## 5. 分支策略

| 分支 | 用途 | 保护 |
|------|------|------|
| `master` | 生产分支，始终可编译 | 是（禁止 force push） |
| `feat/*` | 功能开发分支 | 否 |
| `fix/*` | Bug 修复分支 | 否 |
| `skill/*` | Skill 优化分支 | 否 |

### 工作流

```
feat/xxx → PR → master
fix/xxx  → PR → master
```

---

## 6. 仓库可见性管理

### 切换为私有仓库

```bash
gh repo edit syq17496152/legado --visibility private --accept-visibility-change-consequences
```

### 切换为公开仓库

```bash
gh repo edit syq17496152/legado --visibility public --accept-visibility-change-consequences
```

### 注意事项

- 私有仓库 GitHub Actions 免费额度：2000 分钟/月
- 私有仓库 Fork 关系会断开
- 已 clone 的用户在切换可见性后需重新配置远程访问权限

---

## 7. 大文件管理

以下二进制文件已直接提交到仓库（体积可控，无需 Git LFS）：

| 文件 | 大小 | 说明 |
|------|------|------|
| `modules/rhino/lib/rhino-1.7.14.jar` | ~1.5 MB | Rhino JS 引擎（锁定版本，不变更） |
| `app/cronetlib/*.jar` | ~数 MB | Cronet 网络库（锁定版本） |
| `.trae/skills/legado-source-creator/tools/legado-jvm.jar` | ~数 MB | JVM 仿真器 |

如未来需提交超过 50 MB 的文件，应使用 Git LFS：

```bash
git lfs install
git lfs track "*.apk"
git lfs track "*.aab"
```

---

## 8. 常见问题

### Q: `temp/` 或 `output/` 下的文件被意外跟踪？

```bash
# 从 Git 索引中移除（不删除本地文件）
git rm -r --cached temp/
git rm -r --cached output/
git commit -m "chore: 从跟踪中移除temp/和output/"
```

### Q: Windows `nul` 文件无法删除？

```bash
# 使用 UNC 路径删除
del "\\?\f:\myself\github\WeAgentChat\temp\legado\nul"
# 或在 Git Bash 中
rm -f '/f/myself/github/WeAgentChat/temp/legado/nul'
```

### Q: 推送时 LF/CRLF 警告过多？

```bash
# 配置自动转换（推荐）
git config core.autocrlf input
```

### Q: 需要撤销上次提交（尚未推送）？

```bash
git reset --soft HEAD~1  # 保留暂存区
git reset --mixed HEAD~1 # 保留工作区但不暂存
```
