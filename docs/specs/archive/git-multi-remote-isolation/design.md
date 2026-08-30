# Git多远程仓库隔离方案 - 技术设计

## Technical Approach（技术方案）

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     本地Git仓库                               │
│                                                              │
│  ┌─────────────────────┐       ┌─────────────────────────┐  │
│  │  master-private     │       │  master-public          │  │
│  │  (全量代码)          │       │  (脱敏代码)              │  │
│  │  - .trae/           │       │  - 无 .trae/            │  │
│  │  - ai_tests/        │       │  - 无 ai_tests/         │  │
│  │  - AGENTS.md        │       │  - 无 AGENTS.md         │  │
│  │  - 敏感配置          │       │  - 无敏感配置            │  │
│  └──────────┬──────────┘       └───────────┬─────────────┘  │
│             │                               │                │
│             ▼                               ▼                │
│     ┌───────────────┐              ┌───────────────┐         │
│     │ remote:       │              │ remote:       │         │
│     │ private       │              │ public        │         │
│     │ (私仓)        │              │ (公仓)        │         │
│     └───────────────┘              └───────┬───────┘         │
│                                            │                │
│                                            ▼                │
│                                    ┌───────────────┐         │
│                                    │ pre-push      │         │
│                                    │ Hook门禁      │         │
│                                    └───────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 技术组件

#### 1. Git多远程配置

```bash
# 查看现有远程
git remote -v

# 添加私有仓库远程
git remote add private git@github.com:syq17496152/legado.git

# 添加公开仓库远程
git remote add public git@github.com:LaoDengGTQ/legado-M.git

# 验证
git remote -v
# 输出：
# private  git@github.com:syq17496152/legado.git (fetch)
# private  git@github.com:syq17496152/legado.git (push)
# public   git@github.com:LaoDengGTQ/legado-M.git (fetch)
# public   git@github.com:LaoDengGTQ/legado-M.git (push)
```

#### 2. 分支隔离实现

```bash
# 创建私仓分支（基于当前master）
git checkout -b master-private

# 推送私仓分支到私仓远程
git push private master-private

# 创建公仓分支
git checkout -b master-public

# 在公仓分支创建公仓专用的.gitignore
# 复制预先准备好的.gitignore.public到.gitignore
cp docs/specs/git-multi-remote-isolation/.gitignore.public .gitignore

# 停止跟踪敏感文件（不删除工作区文件）
# 注意：.gitignore只对未跟踪文件生效，已跟踪文件必须先用git rm --cached停止跟踪
git rm -r --cached .trae           # --cached参数确保工作区文件不被删除
git rm -r --cached ai_tests
git rm --cached AGENTS.md
git rm --cached app/google-services.json

# 提交公仓初始化变更（.gitignore更新）
git add .gitignore
git commit -m "公仓初始化：配置.gitignore忽略敏感文件"

# 推送公仓分支到公仓远程
git push public master-public

# 切回私仓分支
git checkout master-private
```

#### 3. Git pre-push Hook实现

**文件位置**：`.git/hooks/pre-push`（Windows环境需确保可执行权限）

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

# 敏感文件清单
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

**Windows环境配置**（确保Hook可执行）：
```bash
# 在Git Bash中执行
chmod +x .git/hooks/pre-push
```

#### 4. 历史提交清理（BFG）

**检测历史敏感文件**：
```bash
# 检查google-services.json是否在历史中
git log --all --full-history -- app/google-services.json

# 检查.trae目录是否在历史中
git log --all --full-history -- .trae/
```

**使用BFG清理**：
```bash
# 下载BFG Repo-Cleaner（https://rtyley.github.io/bfg-repo-cleaner/）
# 假设已下载到 ~/tools/bfg.jar

# 清理google-services.json
java -jar ~/tools/bfg.jar --delete-files google-services.json

# 清理.trae目录
java -jar ~/tools/bfg.jar --delete-folders .trae

# 清理ai_tests目录
java -jar ~/tools/bfg.jar --delete-folders ai_tests

# 清理AGENTS.md
java -jar ~/tools/bfg.jar --delete-folders AGENTS.md

# 强制垃圾回收
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 验证清理结果
git log --all --full-history -- .trae/
```

**首次推送公仓**（可能需要force）：
```bash
# 如果历史清理过，需要强制推送
git push public master-public --force

# 如果是新仓库，正常推送
git push public master-public
```

## Architecture Decisions（架构决策）

### ADR-1: 选择分支隔离而非.gitignore隔离

**决策**：采用分支隔离策略（master-private + master-public）

**理由**：
- `.gitignore`无法区分私仓推送和公仓推送，私仓提交时也会忽略敏感文件，导致AI文档丢失
- 分支隔离物理隔离，私仓分支包含全量代码，公仓分支仅包含脱敏代码
- Git Hook只在公仓推送时触发，私仓提交无阻碍

**后果**：
- 需要手动同步私仓分支到公仓分支
- 需要维护两份.gitignore（私仓版本和公仓版本）

### ADR-2: pre-push Hook而非pre-commit Hook

**决策**：使用pre-push Hook拦截推送

**理由**：
- pre-commit Hook在每次commit时触发，私仓提交AI文档时也会被拦截
- pre-push Hook只在推送时触发，可以区分推送目标（private vs public）
- 只对public远程生效，private远程不受影响

**后果**：
- 开发者可能在本地commit了敏感文件，但推送时才发现
- 需要清晰的错误提示，指导开发者如何处理

### ADR-3: 敏感文件清单化管理

**决策**：敏感文件清单硬编码在pre-push Hook中

**理由**：
- 敏感文件类型固定（AI文档、配置文件），变化频率低
- 清单化管理易于维护和更新
- 避免配置文件管理复杂性

**后果**：
- 新增敏感文件类型需更新Hook脚本
- 清单需与实际项目文件同步

## Data Flow（数据流）

### 私仓提交流程

```
开发者编辑代码
    ↓
git checkout master-private
    ↓
git add <files>
    ↓
git commit -m "feat: XXX"
    ↓
git push private master-private
    ↓
私仓远程接收（全量代码）
```

### 公仓提交流程

```
开发者合并私仓更新
    ↓
git checkout master-public
    ↓
git merge master-private（停止跟踪敏感文件）
    ↓
git add <files>
    ↓
git commit -m "sync: XXX"
    ↓
git push public master-public
    ↓
pre-push Hook检测
    ↓
    ├─ 检测到敏感文件 → 拦截，输出错误
    └─ 无敏感文件 → 推送成功
```

## File Changes（文件变更）

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `.git/hooks/pre-push` | Git pre-push Hook脚本 |
| `docs/specs/git-multi-remote-isolation/` | OpenSpec四文档 |

### 修改文件

| 文件路径 | 变更内容 |
|----------|----------|
| `.gitignore`（公仓版本） | 添加敏感文件排除规则 |
| Git远程配置 | 添加private和public远程 |

### 停止跟踪文件（公仓分支）

> **重要说明**：以下文件在工作区保留，仅停止Git跟踪（`git rm --cached`），配合.gitignore防止提交到公仓。

| 文件路径 | 说明 |
|----------|------|
| `.trae/` | AI Skill和参考文档目录 |
| `ai_tests/` | AI自动化测试系统目录 |
| `AGENTS.md` | AI主规范文件 |
| `app/google-services.json` | Firebase配置（含敏感信息） |
| `.github/workflows/legado.jks` | 签名密钥（已在目录中） |
| `app/逍遥-开源阅读1122.bat` | 可能含本地路径的脚本 |

### 可选停止跟踪文件（根据开源策略）

| 文件路径 | 说明 |
|----------|------|
| `docs/` 目录 | 大部分为AI生成的项目文档，可保留部分如`INDEX.md`、`README.md` |
| `.github/scripts/lzy_web.py` | GitHub Actions脚本，可能含敏感信息 |
| `.github/scripts/tg_bot.py` | Telegram Bot脚本，可能含Token |

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
| `local.properties` | 本地配置（已在.gitignore） |
| `.env` | 环境变量文件（如存在） |

### C类：临时文件/构建产物（已在.gitignore）

| 文件/目录 | 原因 |
|-----------|------|
| `temp/` | 临时文件目录 |
| `output/` | 测试输出目录 |
| `*.log` | 日志文件 |
| `build/`、`.gradle/`、`.idea/` | 构建产物 |

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

| 文件/目录 | 建议 |
|-----------|------|
### F类：可选隔离（根据开源策略）

| 文件/目录 | 建议 |
|-----------|------|
| `docs/` 目录 | 大部分为AI生成文档，可仅保留`INDEX.md`、`README.md` |

## 实施顺序

1. **阶段1：Git多远程配置**
   - 添加private和public远程
   - 验证远程配置

2. **阶段2：分支创建**
   - 创建master-private分支
   - 创建master-public分支并停止跟踪敏感文件

3. **阶段3：Git Hook配置**
   - 创建pre-push Hook脚本
   - 设置可执行权限
   - 测试Hook拦截功能

4. **阶段4：历史清理（如需要）**
   - 检测历史敏感文件
   - 使用BFG清理历史
   - 验证清理结果

5. **阶段5：首次推送**
   - 推送私仓分支
   - 推送公仓分支
   - 验证公仓仓库干净