# Repo Cleanup - 技术方案

## 1. 源码深度验证结果

> 用户要求"深度分析别误删"，对每个待删文件进行了源码引用验证。
> 审查代理进行了穿透验证，发现 2 个阻断级问题，已修正。

### 1.1 明确可安全删除（已验证无引用）

| 文件 | 验证方式 | 验证结果 |
|------|---------|---------|
| `AGENTS.md.bak` | Grep `AGENTS.md.bak` | 仅被 docs/ 描述性文本引用，无代码引用 |
| `classes.jar` | Grep `classes.jar` in *.gradle* | **无任何 Gradle 配置引用**，孤立文件 |
| `gsy.aar` | Grep `gsy.aar` in *.gradle* | **无任何 Gradle 配置引用**，孤立文件 |
| `cn/hutool/.../SymmetricDecryptor.class` | Grep `SymmetricDecryptor` in *.java | **无任何 Java 源码引用**，孤立 .class |
| `app/cronetlib_149_backup/` | Grep `cronetlib_149_backup` | 无代码/构建引用 |
| `avd.bat` + `avd.sh` | Grep `avd.bat|avd.sh` | 无任何文件引用，孤立脚本 |
| `modules/rhino/lib/rhino-1.7.14.jar` | Grep `rhino-1.7.14` in build.gradle | **已被注释掉**（`//api(fileTree(...))`），改用 `libs.mozilla.rhino` |
| `ksp_info.txt` | Grep `ksp_info` | **无任何引用**，KSP 构建日志产物 |

### 1.2 需断链修复后删除（阻断级）

| 文件 | 当前引用 | 改造方案 |
|------|---------|---------|
| `docs/temp-analysis/` | **12 个 markdown 链接**：network-perf-stability/README.md 8个 + forks_comparison_methodology.md 4个 | **前置**：先修复 12 个断链，再删除目录 |

### 1.3 需改造后删除

| 文件 | 当前引用 | 改造方案 |
|------|---------|---------|
| `.github/workflows/legado.jks` | CI `test.yml` L172: `cp ...legado.jks` | 改用 GitHub Secrets base64 解码 |
| `test.yml` L176-177 | 明文密码 `RELEASE_STORE_PASSWORD=gedoor_legado` | 改用 `${{ secrets.KEY_STORE_PASSWORD }}` |

### 1.4 需用户确认

| 文件 | 说明 |
|------|------|
| `dedup_sources.py` / `dedup_sources_v2.py` | 被 `smart_dedup_v3.py` 取代的旧迭代 |
| `test_sources.json` | 被 `e2e_test.py` 引用，含源数据 |
| `test_rss_sources.json` | **无代码引用**，含源数据，可直接移除 |

## 2. 技术方案

### Phase 1+2: 安全删除 + .gitignore

**执行命令**：
```bash
git rm AGENTS.md.bak classes.jar gsy.aar avd.bat avd.sh ksp_info.txt
git rm -r cn/hutool/
git rm -r app/cronetlib_149_backup/
git rm modules/rhino/lib/rhino-1.7.14.jar
```

**注意**：`docs/temp-analysis/` 暂不删除，需先完成 Phase 1.5 断链修复。

**.gitignore 追加**：
```gitignore
# 防止再次提交废弃文件
docs/temp-analysis/
*.bak
*.class
avd.bat
avd.sh
ksp_info.txt
```

**不添加** `*.jar` / `*.aar` 规则，因为 `app/cronetlib/` 中的 jar 仍需跟踪。

**体积收益**：~2.0MB（cronetlib_149_backup 1.8MB + classes.jar 292KB + gsy.aar 340KB + 其他 ~90KB）

**commit**: `chore: remove abandoned temp files, backup jars, and build logs`

### Phase 1.5: 断链修复（前置，阻断级）

修复 12 个指向 `docs/temp-analysis/` 的 markdown 链接：

1. **`docs/specs/network-perf-stability/README.md`** (8 个链接)
   - 这些链接指向 temp-analysis 中的分析报告
   - 修复方式：移除链接（分析结论已沉淀到 design.md/spec.md）或替换为 specs/ 内对应文档

2. **`docs/project-rules/forks_comparison_methodology.md`** (4 个链接)
   - 修复方式：移除或替换为 project-rules/ 内对应文档

3. 修复完成后：`git rm -r docs/temp-analysis/`

**commit**: `docs: fix broken links to temp-analysis before removal`

### Phase 3: 签名密钥与密码安全化

1. **编码**: `base64 -w 0 .github/workflows/legado.jks` → 记录 base64 字符串
2. **配置 GitHub Secrets**（6 个）:
   - `SIGNING_KEY_BASE64` = base64 编码的 jks
   - `KEY_STORE_PASSWORD` / `KEY_ALIAS` / `KEY_PASSWORD`
   - `TEST_STORE_PASSWORD` / `TEST_KEY_PASSWORD`（test.yml 专用）
3. **修改 CI**:
   - `test.yml` L172 改为 `echo "${{ secrets.SIGNING_KEY_BASE64 }}" | base64 -d > $GITHUB_WORKSPACE/app/legado.jks`
   - `test.yml` L176-177 改为 `RELEASE_STORE_PASSWORD=${{ secrets.KEY_STORE_PASSWORD }}` / `RELEASE_KEY_PASSWORD=${{ secrets.KEY_PASSWORD }}`
4. **删除**: `git rm .github/workflows/legado.jks`
5. **可选**: `git filter-repo --path .github/workflows/legado.jks --invert-paths` 清理历史
   - **前置**：`pip install git-filter-repo`（当前环境未安装，BFG Repo Cleaner 是替代方案）

**commit**: `security: move signing key and passwords from repo to GitHub Secrets`

### Phase 4: Skill 脚本清理

| 操作 | 文件 | 说明 |
|------|------|------|
| 删除 | `dedup_sources.py` | 被 smart_dedup_v3.py 取代 |
| 删除 | `dedup_sources_v2.py` | 被 smart_dedup_v3.py 取代 |
| git rm --cached | `test_sources.json` | 被 e2e_test.py 引用，移除跟踪但保留本地 |
| git rm | `test_rss_sources.json` | **无代码引用**，可直接移除 |
| .gitignore 追加 | `.trae/skills/*/scripts/test_*.json` | 防止再次提交 |
| 删除 | `docs/specs/legado-skill-v2-rebuild/test-encoding.txt` | 临时调试文件 |

**commit**: `chore: cleanup legacy skill scripts and test data`

### Phase 5: 文档同步

- 更新 `docs/INDEX.md`：移除 `docs/temp-analysis/` 引用
- 更新 `docs/project-flow/git-repo-management.md`：
  - rhino-1.7.14.jar 从"不变更"改为"已移除"
  - 签名密钥改为 GitHub Secrets 注入
  - .gitignore 新增规则说明
- 更新 `docs/project-flow/architecture/ci-cd-pipeline.md`：移除明文密码引用

## 3. 风险评估

| 风险 | 等级 | 应对 |
|------|------|------|
| 删除 classes.jar/gsy.aar 后构建失败 | 低 | 已验证无 Gradle 引用，可恢复 |
| docs/temp-analysis/ 断链 | **阻断** | Phase 1.5 修复 12 个链接后再删除 |
| test.yml 明文密码泄露 | **阻断** | Phase 3 一并改造密码引用 |
| CI 签名密钥迁移失败 | 中 | 先在分支测试 CI 改造 |
| git filter-repo 未安装 | 中 | `pip install git-filter-repo` 或 BFG 替代 |
| Skill 脚本误删 | 中 | 仅删已验证重复版本 |
