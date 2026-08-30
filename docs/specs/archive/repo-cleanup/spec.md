# Repo Cleanup - 需求规格

## 1. 背景

项目仓库共 2999 个文件被 git 跟踪，其中包含大量废弃的临时文件、备份文件、构建产物、临时分析文档等。这些文件：
- 污染仓库历史，增加克隆体积
- 干扰 AI 和开发者定位有效文件
- 部分敏感文件（.jks 签名密钥、.class 反编译产物）存在安全风险
- 违反 .gitignore 规则（已被忽略的文件类型仍有历史遗留）

## 2. 排查结果

### 2.1 明确废弃文件（建议删除）

| # | 文件/目录 | 类型 | 大小 | 原因 |
|---|----------|------|------|------|
| 1 | `AGENTS.md.bak` | 备份文件 | 44KB | 主规范备份，已完成瘦身，备份不再需要 |
| 2 | `classes.jar` | 构建产物 | 292KB | 反编译/提取的 hutool class jar，应走 Gradle 依赖 |
| 3 | `gsy.aar` | 构建产物 | 340KB | GSY 视频播放器 AAR，应走 Maven 依赖或 git submodule |
| 4 | `cn/hutool/crypto/symmetric/SymmetricDecryptor.class` | .class 文件 | 4KB | 反编译的 hutool class，应走 Gradle 依赖 |
| 5 | `app/cronetlib_149_backup/` | 备份目录 | 1.8MB | Cronet 149 版本备份 jar（6个），已升级到新版本，旧备份不再需要 |
| 6 | `avd.bat` + `avd.sh` | 临时脚本 | <1KB | 模拟器启动脚本，功能简单且已有 ai_tests 替代方案 |
| 7 | `docs/temp-analysis/` | 临时分析文档 | 512KB | AI 分析过程中的临时文档（16个），结论已沉淀到 specs/ 和 project-rules/，临时文档可删除 |
| 8 | `modules/rhino/lib/rhino-1.7.14.jar` | 旧依赖 jar | - | build.gradle 已注释掉，改用 `libs.mozilla.rhino` |
| 9 | `ksp_info.txt` | 构建日志 | 38KB | KSP 编译信息日志，无任何引用，属于构建产物 |

### 2.2 安全风险文件（必须处理）

| # | 文件 | 风险 | 建议 |
|---|------|------|------|
| 10 | `.github/workflows/legado.jks` | 签名密钥提交到仓库，任何有仓库读权限的人可获取 | 从仓库中移除，改用 GitHub Secrets 注入 |
| 11 | `test.yml` L176-177 明文密码 | `RELEASE_STORE_PASSWORD=gedoor_legado` 明文暴露在 CI 配置中 | 改用 `${{ secrets.xxx }}` 引用 |

### 2.3 需用户确认的文件

| # | 文件/目录 | 类型 | 说明 | 建议 |
|---|----------|------|------|------|
| 12 | `dedup_sources.py` + `dedup_sources_v2.py` | Skill 重复脚本 | 被 smart_dedup_v3.py 取代的旧迭代版本 | 删除旧版保留最终版 |
| 13 | `test_sources.json` | 测试数据 JSON | 被 e2e_test.py 引用，含源数据 | git rm --cached 移除跟踪，保留本地 |
| 14 | `test_rss_sources.json` | 测试数据 JSON | **无代码引用**，含源数据 | git rm --cached 移除跟踪，保留本地 |
| 15 | `docs/specs/legado-skill-v2-rebuild/test-encoding.txt` | 测试文件 | 编码测试临时文件 | 删除 |

### 2.4 删除前置条件：断链修复

> **阻断级发现**：`docs/temp-analysis/` 被 12 个 markdown 链接引用，直接删除会导致断链。必须先修复链接再删除。

| 引用文件 | 断链数 | 修复方式 |
|---------|--------|---------|
| `docs/specs/network-perf-stability/README.md` | 8 | 移除或替换为 specs/ 内对应文档链接 |
| `docs/project-rules/forks_comparison_methodology.md` | 4 | 移除或替换为 project-rules/ 内对应文档链接 |

## 3. 功能需求

### FR-1: 删除明确废弃文件
- 删除 2.1 表中列出的 8 项文件/目录
- 从 git 跟踪中移除（`git rm`）

### FR-2: 清理临时分析文档（前置：断链修复）
- **前置**：修复 `docs/specs/network-perf-stability/README.md` 和 `docs/project-rules/forks_comparison_methodology.md` 中指向 `docs/temp-analysis/` 的 12 个断链
- 删除 `docs/temp-analysis/` 整个目录
- 补充 `.gitignore` 规则防止再次提交

### FR-3: 更新 .gitignore
- 新增规则防止类似临时文件再次被提交

### FR-4: 签名密钥与密码安全化
- `.github/workflows/legado.jks` 从仓库中移除，改用 GitHub Secrets 注入
- `test.yml` L176-177 明文密码改为 `${{ secrets.xxx }}` 引用
- 新增 GitHub Secrets：`SIGNING_KEY_BASE64` / `KEY_STORE_PASSWORD` / `KEY_ALIAS` / `KEY_PASSWORD`

### FR-5: 评估 Skill 临时脚本
- 识别已废弃的重复迭代脚本并删除
- 测试数据 JSON 从 git 移除但保留本地（test_rss_sources.json 无代码引用可直接移除）

## 4. 非功能需求

| 需求 | 说明 |
|------|------|
| 体积缩减 | 目标减少仓库体积 ≥ 2.5MB |
| .gitignore 完善 | 新增 ignore 规则覆盖所有已删除文件类型 |
| 安全合规 | 签名密钥不存储在仓库中 |
| 文档同步 | 更新 docs/INDEX.md 和 git-repo-management.md |

## 5. 限制与风险

| 限制 | 说明 |
|------|------|
| .jks 历史清理 | 需强制推送，所有协作者需重新克隆 |
| Skill 脚本评估 | 需用户确认哪些已废弃 |
| classes.jar/gsy.aar | 如有隐性依赖可能在构建时暴露，可恢复 |
