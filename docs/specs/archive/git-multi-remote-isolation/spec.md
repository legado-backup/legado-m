# Git多远程仓库隔离方案 - 规格说明

## Intent（意图）

**用户需求**：在私仓进行开发（使用AI等特性能力），同时维护一个公开仓库（仅提供源码+必要文档），防止AI相关文档、敏感配置、个人信息泄露到公开仓库。

**核心目标**：
1. 私仓推送到 `https://github.com/syq17496152/legado.git`（全量代码）
2. 公仓推送到 `https://github.com/LaoDengGTQ/legado-M`（仅源码+必要文档）
3. 公仓提交必须经过门禁验证，确保敏感文件不被推送

## Scope（范围）

### In Scope（在范围内）

1. **Git多远程配置**：添加 `private` 和 `public` 两个远程仓库
2. **分支隔离机制**：`master-private`（私仓）与 `master-public`（公仓）分支隔离
3. **敏感文件清单定义**：AI文档、配置文件、临时文件等
4. **Git pre-push Hook**：自动检测并拦截敏感文件推送到公仓
5. **历史提交清理**：使用BFG清除历史中的敏感信息（如已存在）
6. **提交流程规范**：明确私仓提交→公仓提交的两阶段流程

### Out of Scope（不在范围内）

1. **GitHub Actions自动同步**：暂不实现私仓到公仓的自动同步
2. **Git Submodule拆分**：不采用子模块方案
3. **SSH多账号配置**：假设两个仓库使用同一GitHub账号（或用户已配置SSH）
4. **公仓Issue/PR管理**：仅关注代码推送隔离，不涉及社区管理

## Approach（方法）

### 分支隔离策略（推荐方案）

```
master-private (私仓分支)
├── 全量代码（含 .trae/、ai_tests/、AGENTS.md 等）
├── 敏感配置（google-services.json 等）
└── 推送到 remote: private

master-public (公仓分支)
├── 脱敏代码（删除敏感文件）
├── 仅保留源码 + 必要文档（README.md、LICENSE 等）
└── 推送到 remote: public
```

**优势**：
- 物理隔离，私仓分支与公仓分支独立演进
- Git Hook只在公仓推送时触发，私仓提交无阻碍
- 历史清晰，公仓历史干净无敏感信息

### Alternatives Considered（备选方案）

| 方案 | 优势 | 劣势 | 决策 |
|------|------|------|------|
| **.gitignore隔离** | 简单，无需分支管理 | 无法区分私仓推送和公仓推送 | ❌ 不采用 |
| **双仓库目录隔离** | 两个独立目录，完全隔离 | 磁盘占用大，同步复杂 | ❌ 不采用 |
| **Git Submodule拆分** | 模块化管理 | 配置复杂，不适合本项目 | ❌ 不采用 |

### Drawbacks（局限性）

1. **分支同步成本**：私仓功能更新需手动合并到公仓分支
2. **历史不可逆**：若历史提交已包含敏感信息，需一次性清理
3. **Hook兼容性**：Windows环境需确保Git Hook可执行权限

## Requirements（需求）

### 功能需求

1. **R1 - Git多远程配置**
   - 添加远程 `private`：`git@github.com:syq17496152/legado.git`
   - 添加远程 `public`：`git@github.com:LaoDengGTQ/legado-M.git`
   - 验证远程配置正确

2. **R2 - 分支隔离**
   - 创建 `master-private` 分支（基于当前 `master`）
   - 创建 `master-public` 分支（从 `master-private` 删除敏感文件）
   - 确保 `.gitignore` 公仓版本与私仓版本不同

3. **R3 - Git pre-push Hook**
   - 拦截推送到 `public` 远程时的敏感文件
   - 检测文件清单：
     - `.trae/` 目录（所有子目录和文件）
     - `ai_tests/` 目录（所有子目录和文件）
     - `docs/` 目录（可选，根据开源策略）
     - `AGENTS.md` 文件
     - `app/google-services.json` 文件
     - 其他敏感文件（见 design.md）
   - 输出错误提示并阻止推送

4. **R4 - 历史提交清理**
   - 检查历史提交是否包含敏感文件
   - 使用BFG Repo-Cleaner清理（如需要）
   - 验证清理后历史干净

### 非功能需求

1. **NFR1 - 安全性**：门禁机制100%可靠，无绕过漏洞
2. **NFR2 - 可维护性**：敏感文件清单易于更新
3. **NFR3 - 开发体验**：私仓提交不受影响，公仓提交流程清晰

## Scenarios（场景）

### S1 - 私仓开发提交

```
开发者 → 编辑代码 → git checkout master-private → git commit → git push private master-private
```

**结果**：私仓提交成功，AI文档和敏感配置正常提交。

### S2 - 公仓发布提交

```
开发者 → git checkout master-public → git merge master-private（删除敏感文件） → git commit → git push public master-public
```

**结果**：
- 若检测到敏感文件 → Hook拦截，推送失败，提示错误
- 若无敏感文件 → 推送成功，公仓更新

### S3 - 敏感文件误添加

```
开发者 → 在 master-public 分支添加 .trae/new-file.md → git commit → git push public master-public
```

**结果**：pre-push Hook拦截，输出错误提示：
```
[ERROR] 检测到敏感文件，禁止推送到公仓：
  - .trae/new-file.md
请删除敏感文件或切换到私仓分支提交。
```

### S4 - 历史提交包含敏感信息

```
开发者 → 准备首次公仓推送 → 发现历史提交包含 google-services.json
```

**结果**：使用BFG清理历史：
```bash
java -jar bfg.jar --delete-files google-services.json
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push public master-public --force
```