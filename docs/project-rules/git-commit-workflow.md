# Git多远程仓库提交规范

> 本规范定义了私仓（全量代码）与公仓（脱敏开源版本）的Git提交流程，确保AI相关文档和敏感信息不被推送到公开仓库。

## 核心原则

1. **私仓为常规分支**：日常开发、AI辅助、文档编写均在私仓分支（`master-private`）进行
2. **公仓仅AI可提交**：公仓分支（`master-public`）的提交必须由AI执行，用户不得直接操作
3. **AI主动切换机制**：AI负责完整的公仓提交流程（私仓→公仓→提交→切回私仓），防止用户误操作
4. **审查后提交**：AI提交公仓前必须先审查私仓代码合规性，确保无敏感文件

## Git远程仓库配置

| 远程名称 | 地址 | 用途 |
|---------|------|------|
| `private` | `git@github.com:syq17496152/legado.git` | 私有仓库，全量代码 |
| `public` | `git@github.com:LaoDengGTQ/legado-M.git` | 公开仓库，脱敏开源版本 |

## 分支策略

| 分支名称 | 用途 | 允许推送的远程 |
|---------|------|---------------|
| `master-private` | 私仓开发分支，含AI文档和敏感配置 | `private` |
| `master-public` | 公仓分支，仅含源码+必要文档 | `public` |

**强制规则**：
- `master-private` 分支禁止推送到 `public` 远程
- `master-public` 分支禁止推送到 `private` 远程
- 本地默认分支必须为 `master-private`

## AI公仓提交流程（强制）

### 步骤1：审查私仓代码合规性

AI在提交公仓前，必须先审查当前私仓分支的代码：

```bash
# 1. 确保在私仓分支
git checkout master-private

# 2. 检查是否有未提交的变更
git status

# 3. 检查最近提交是否包含敏感文件
git log -5 --name-only
```

**审查清单**：
- ✅ 检查是否包含AI文档（`.trae/`、`ai_tests/`、`AGENTS.md`）
- ✅ 检查是否包含敏感配置（`google-services.json`、`*.jks`、`*.keystore`）
- ✅ 检查是否包含私有化脚本（`逍遥-开源阅读1122.bat`）
- ✅ 检查`updateLog.md`是否含私有化信息（如公众号二维码）

**如果发现敏感文件**：
- 立即提醒用户，询问是否需要处理后再提交公仓
- 用户明确要求提交时，AI必须在提交前删除这些文件

### 步骤2：切换到公仓分支

```bash
# 切换到公仓分支
git checkout master-public
```

### 步骤3：合并私仓更新并删除敏感文件

```bash
# 合并私仓分支的最新更新
git merge master-private

# 如果合并成功但有冲突，手动解决冲突
# 删除合并带来的敏感文件
rm -rf .trae ai_tests
rm AGENTS.md
rm app/google-services.json
rm .github/workflows/legado.jks
rm app/逍遥-开源阅读1122.bat
rm .github/scripts/tg_bot.py

# 检查其他敏感文件（见下方清单）
# ...

git add .
git commit -m "sync: 合并私仓更新并删除敏感文件"
```

### 步骤4：推送公仓分支

```bash
# 推送到公仓远程（pre-push Hook会自动检测敏感文件）
git push public master-public
```

**如果Hook拦截**：
- Hook会输出错误提示，列出检测到的敏感文件
- AI必须删除敏感文件后重新提交
- 重新执行步骤3和步骤4

### 步骤5：切回私仓分支（强制）

```bash
# 提交完成后，立即切回私仓分支
git checkout master-private
```

**目的**：防止用户误操作，确保下次开发在私仓分支进行。

## 用户私仓提交流程

用户在日常开发中，直接在私仓分支提交即可：

```bash
# 1. 确保在私仓分支（默认分支）
git checkout master-private

# 2. 添加变更文件
git add <files>

# 3. 提交
git commit -m "feat: XXX"

# 4. 推送到私仓远程
git push private master-private
```

**用户无需关心公仓提交**，公仓提交由AI负责。

## 敏感文件完整清单

### A类：AI相关文档（必须隔离）

| 文件/目录 | 原因 |
|-----------|------|
| `.trae/` | AI Skill、参考文档、脚本、报告、测试数据 |
| `ai_tests/` | AI自动化测试系统（cases、lib、scripts、reports等） |
| `AGENTS.md` | AI主规范文件（含项目规则、约束、工作流程） |

### B类：敏感配置（必须隔离）

| 文件/目录 | 原因 |
|-----------|------|
| `app/google-services.json` | Firebase配置（含项目ID、API Key） |
| `.github/workflows/legado.jks` | Android签名密钥 |
| `app/逍遥-开源阅读1122.bat` | 可能含本地路径或敏感信息 |
| `.github/scripts/tg_bot.py` | Telegram Bot脚本，可能含Token |
| `local.properties` | 本地配置（已在.gitignore） |
| `.env` | 环境变量文件（如存在） |

### C类：个人信息（需检查）

| 文件/目录 | 原因 |
|-----------|------|
| `app/src/main/assets/updateLog.md` | 更新日志，父项目已公开但内容可能含私有化信息（如公众号二维码），需检查 |

### D类：技术细节文件（可选隔离）

| 文件/目录 | 原因 |
|-----------|------|
| `app/schemas/*.json` | 数据库Schema文件，技术细节，非用户必要 |
| `modules/web/package.json` | 前端构建依赖，可能暴露依赖版本 |
| `modules/web/package-lock.json` | 前端构建依赖锁定文件 |

### E类：临时文件/构建产物（已在.gitignore）

| 文件/目录 | 原因 |
|-----------|------|
| `temp/` | 临时文件目录 |
| `output/` | 测试输出目录 |
| `*.log` | 日志文件 |
| `build/`、`.gradle/`、`.idea/` | 构建产物 |

### F类：可选隔离（根据开源策略）

| 文件/目录 | 建议 |
|-----------|------|
| `docs/` 目录 | 大部分为AI生成文档，可仅保留`INDEX.md`、`README.md` |

## Git pre-push Hook规范

AI在首次配置公仓时，必须创建 `.git/hooks/pre-push` 文件：

```bash
#!/bin/bash
# pre-push Hook：拦截敏感文件推送到公仓

# 获取推送的目标远程
remote="$1"
url="$2"

# 仅对public远程生效
if [ "$remote" != "public" ]; then
    exit 0
fi

# 敏感文件清单（A-F类，已排除父项目已公开的文件）
SENSITIVE_FILES=(
    ".trae/"
    "ai_tests/"
    "AGENTS.md"
    "app/google-services.json"
    ".github/workflows/legado.jks"
    "app/逍遥-开源阅读1122.bat"
    ".github/scripts/tg_bot.py"
)

# 获取即将推送的文件列表
while read local_ref local_sha remote_ref remote_sha; do
    # 检查每个敏感文件
    for file in "${SENSITIVE_FILES[@]}"; do
        # 检查文件是否存在于即将推送的提交中
        if git ls-tree -r "$local_sha" --name-only | grep -q "^$file"; then
            echo "[ERROR] 检测到敏感文件，禁止推送到公仓："
            echo "  - $file"
            echo ""
            echo "请删除敏感文件或切换到私仓分支（master-private）提交。"
            echo "私仓推送命令：git push private master-private"
            exit 1
        fi
    done
done

exit 0
```

## 反模式（禁止行为）

1. ❌ 用户直接在公仓分支提交代码
2. ❌ AI推送公仓前未审查私仓代码合规性
3. ❌ AI推送公仓后未切回私仓分支
4. ❌ 推送公仓时包含A-F类敏感文件
5. ❌ 删除Git Hook以绕过门禁

## 常见问题

### Q1: 用户不小心在公仓分支做了修改怎么办？

**答**：立即提醒用户，询问是否需要将修改合并到私仓分支。如果用户确认，AI执行：
```bash
git checkout master-private
git merge master-public
git checkout master-public
git reset --hard HEAD~1  # 撤销公仓分支的修改
git checkout master-private
```

### Q2: 公仓需要更新README等文档怎么办？

**答**：AI在私仓分支修改文档后，按照标准流程提交公仓：
1. 在私仓分支修改文档（如`README.md`、`LICENSE`）
2. 提交到私仓分支
3. 执行公仓提交流程（审查→切换→合并→提交→切回）

### Q3: 如何确认当前在哪个分支？

**答**：执行 `git branch` 查看当前分支，本地默认分支应为 `master-private`。

### Q4: 历史提交已包含敏感文件怎么办？

**答**：AI使用BFG Repo-Cleaner清理历史，详见设计文档中的"历史提交清理"章节。

---

## 修订记录

- 2026-07-14：初版，定义私仓/公仓提交流程、敏感文件清单、AI主动切换机制