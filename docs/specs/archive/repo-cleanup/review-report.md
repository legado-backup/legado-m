# Repo Cleanup - 深度穿透审查报告

> 审查日期: 2026-07-15
> 审查范围: README.md / spec.md / design.md / tasks.md
> 审查方法: 逐项源码 Grep/Read/LS 验证 + git ls-files 排查 + CI workflow 全文审查

---

## 一、逐条整改明细

### 阻断级问题

#### B1: docs/temp-analysis/ 删除会断链 -- 设计方案严重遗漏链接修复步骤

- **缺陷定位**: design.md + "1.1 明确可安全删除" 表 + "Phase 1+2" 命令段 + tasks.md T1.4
- **问题本质**: design.md 声称"被多个 specs/ 文档描述性文本引用，删除后不影响功能"，但源码验证发现存在 **12 个活跃 markdown 链接** 指向 temp-analysis 文件，删除后这些链接全部断链，违反设计基准第4条（文档可核验性）和落地可执行性要求。
- **活跃链接清单**:
  1. `docs/specs/network-perf-stability/README.md` L156-163: 8 个 `[xxx.md](../../temp-analysis/xxx.md)` 链接
  2. `docs/project-rules/forks_comparison_methodology.md` L509-512: 4 个 `[xxx.md](../temp-analysis/xxx.md)` 链接
  3. `docs/project-flow/architecture/multi-agent-analysis-spec.md` L77/117/264/277: 4 个描述性引用（路径引用，非 markdown 链接，断链风险较低但仍需更新）
  4. `docs/project-rules/complex-task-pipeline.md` L27: 1 个描述性引用
- **整改替换文本**:

**design.md "1.1 明确可安全删除" 表中 docs/temp-analysis/ 行替换为**:

```markdown
| `docs/temp-analysis/` | Grep `temp-analysis` | 被多个文档引用，含 12 个活跃 markdown 链接，**需先修复链接再删除** |
```

**design.md Phase 1+2 命令段前新增**:

```markdown
**前置步骤：修复活跃链接**（必须在 `git rm -r docs/temp-analysis/` 之前完成）：

1. `docs/specs/network-perf-stability/README.md` L156-163：将 8 个 `../../temp-analysis/xxx.md` 链接改为指向对应沉淀文档（如 `../../project-rules/forks_comparison_methodology.md`），或移除链接改为纯文本说明
2. `docs/project-rules/forks_comparison_methodology.md` L509-512：将 4 个 `../temp-analysis/xxx.md` 链接改为纯文本说明或移除案例链接
3. `docs/project-flow/architecture/multi-agent-analysis-spec.md`：将 temp-analysis 路径引用改为 `.gitignore` 忽略的本地目录说明
4. `docs/project-rules/complex-task-pipeline.md` L27：同上

**验证**：`grep -rn "temp-analysis" docs/` 应只返回 repo-cleanup spec 自身的引用
```

**tasks.md T1.4 替换为**:

```markdown
### T1.4 修复 temp-analysis 活跃链接
- 修改 `docs/specs/network-perf-stability/README.md` L156-163：8 个链接改为纯文本或指向沉淀文档
- 修改 `docs/project-rules/forks_comparison_methodology.md` L509-512：4 个链接改为纯文本
- 修改 `docs/project-flow/architecture/multi-agent-analysis-spec.md`：路径引用更新
- 修改 `docs/project-rules/complex-task-pipeline.md` L27：路径引用更新
- 验证：`grep -rn "temp-analysis" docs/ | grep -v repo-cleanup` 无结果
- 回滚：`git checkout HEAD -- <modified files>`

### T1.5 删除临时分析文档
- 前提：T1.4 链接修复完成
- `git rm -r docs/temp-analysis/`
- 验证：确认目录删除
- 回滚：`git checkout HEAD -- docs/temp-analysis/`
```

---

#### B2: test.yml 硬编码明文密码未纳入 CI 改造范围

- **缺陷定位**: design.md "Phase 3: CI 签名密钥安全化" + tasks.md "Phase 3"
- **问题本质**: design.md Phase 3 只处理 .jks 文件的存储方式（改用 GitHub Secrets base64 解码），但 test.yml L176-177 中的 `RELEASE_STORE_PASSWORD=gedoor_legado` 和 `RELEASE_KEY_PASSWORD=gedoor_legado` 是硬编码明文密码。release.yml 已正确使用 `${{ secrets.xxx }}` 格式，test.yml 未同步改造将导致"签名密钥安全化"名不副实。
- **源码证据**:
  - [test.yml](file:///f:/myself/github/WeAgentChat/temp/legado/.github/workflows/test.yml#L176-L177): `RELEASE_STORE_PASSWORD=gedoor_legado`
  - [release.yml](file:///f:/myself/github/WeAgentChat/temp/legado/.github/workflows/release.yml#L58-L62): 已正确使用 `${{ secrets.RELEASE_KEY_PASSWORD }}` 等
  - [ci-cd-pipeline.md](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/architecture/ci-cd-pipeline.md#L111-L112): 文档中也暴露了明文密码
- **整改替换文本**:

**design.md "Phase 3: CI 签名密钥安全化" 整段替换为**:

```markdown
### Phase 3: CI 签名密钥与密码安全化

1. **编码**: `base64 -w 0 .github/workflows/legado.jks` -> 记录 base64 字符串
2. **配置 GitHub Secrets**:
   - `SIGNING_KEY_BASE64` = base64 编码的 jks
   - `KEY_STORE_PASSWORD` / `KEY_ALIAS` / `KEY_PASSWORD`
   - **新增** `TEST_STORE_PASSWORD` = 测试版签名密码（原 gedoor_legado）
   - **新增** `TEST_KEY_PASSWORD` = 测试版密钥密码（原 gedoor_legado）
3. **修改 CI test.yml**（L169-178 整段替换）:
   ```yaml
   - name: Release Apk Sign
     run: |
       echo "给apk增加签名"
       echo "${{ secrets.SIGNING_KEY_BASE64 }}" | base64 -d > $GITHUB_WORKSPACE/app/legado.jks
       cat >> $GITHUB_WORKSPACE/gradle.properties << EOF
       RELEASE_STORE_FILE=./legado.jks
       RELEASE_KEY_ALIAS=legado
       RELEASE_STORE_PASSWORD=${{ secrets.TEST_STORE_PASSWORD }}
       RELEASE_KEY_PASSWORD=${{ secrets.TEST_KEY_PASSWORD }}
       EOF
   ```
4. **删除**: `git rm .github/workflows/legado.jks`
5. **可选**: `git filter-repo --path .github/workflows/legado.jks --invert-paths` 清理历史
6. **更新文档**: `docs/project-flow/architecture/ci-cd-pipeline.md` L108-112 移除明文密码，改为 Secrets 引用说明

**commit**: `security: move signing key and passwords from repo to GitHub Secrets`
```

**tasks.md Phase 3 替换为**:

```markdown
## Phase 3: CI 签名密钥与密码安全化

### T3.1 编码签名密钥
- `base64 -w 0 .github/workflows/legado.jks` 记录输出
- 验证：base64 字符串可还原为 .jks

### T3.2 配置 GitHub Secrets
- 添加 6 个 Secrets：
  - `SIGNING_KEY_BASE64` / `KEY_STORE_PASSWORD` / `KEY_ALIAS` / `KEY_PASSWORD`
  - **新增** `TEST_STORE_PASSWORD`（测试版签名密码）
  - **新增** `TEST_KEY_PASSWORD`（测试版密钥密码）
- 验证：GitHub Settings -> Secrets 中确认存在

### T3.3 修改 CI workflow test.yml
- 修改 `.github/workflows/test.yml` L169-178 整段：
  - L172: 改为 `echo "${{ secrets.SIGNING_KEY_BASE64 }}" | base64 -d > $GITHUB_WORKSPACE/app/legado.jks`
  - L176-177: 改为 `RELEASE_STORE_PASSWORD=${{ secrets.TEST_STORE_PASSWORD }}` / `RELEASE_KEY_PASSWORD=${{ secrets.TEST_KEY_PASSWORD }}`
- 验证：push 分支后 CI 运行成功

### T3.4 更新 CI 文档
- 修改 `docs/project-flow/architecture/ci-cd-pipeline.md` L108-112：移除明文密码，改为 Secrets 引用说明
- 修改 `docs/project-flow/build-apk-guide.md` L238：更新签名文件来源说明

### T3.5 删除仓库中的 .jks
- 前提：T3.2 + T3.3 验证通过
- `git rm .github/workflows/legado.jks`
- commit: `security: move signing key and passwords from repo to GitHub Secrets`
```

---

### 高级问题

#### H1: ksp_info.txt 遗漏 -- 构建日志被 git 跟踪但未纳入清理清单

- **缺陷定位**: spec.md "2.1 明确废弃文件" 表
- **问题本质**: `ksp_info.txt`（38KB KSP 构建日志）被 git 跟踪，属于构建产物/临时文件，符合 spec.md 中"废弃临时文件"的清理范围，但完全未出现在排查结果中。
- **源码证据**: `git ls-files -- "ksp_info.txt"` 返回 `ksp_info.txt`；`wc -c ksp_info.txt` = 38042 bytes
- **整改替换文本**:

**spec.md "2.1 明确废弃文件" 表追加一行**:

```markdown
| 9 | `ksp_info.txt` | 构建日志 | 38KB | KSP (Kotlin Symbol Processing) 构建日志，属于构建产物，不应提交到仓库 |
```

**design.md "1.1 明确可安全删除" 表追加一行**:

```markdown
| `ksp_info.txt` | Grep `ksp_info` in *.md | 无任何文档/代码引用，孤立构建日志 |
```

**design.md Phase 1+2 git rm 命令追加**:

```bash
git rm ksp_info.txt
```

**design.md .gitignore 追加**:

```gitignore
ksp_info.txt
```

**tasks.md T1.1 修改为**:

```markdown
### T1.1 删除根目录废弃文件
- `git rm AGENTS.md.bak classes.jar gsy.aar avd.bat avd.sh ksp_info.txt`
- 验证：`git status` 确认 6 文件已删除
- 回滚：`git checkout HEAD -- <file>`
```

**tasks.md T2.1 .gitignore 规则追加 `ksp_info.txt`**:

```markdown
- 追加规则：`docs/temp-analysis/` / `*.bak` / `*.class` / `avd.bat` / `avd.sh` / `ksp_info.txt`
```

---

#### H2: git-repo-management.md 与 spec 矛盾 -- rhino-1.7.14.jar 描述为"不变更"但 spec 要删除

- **缺陷定位**: design.md "Phase 5: 文档同步" + tasks.md "Phase 5"
- **问题本质**: `docs/project-flow/git-repo-management.md` L214 将 `modules/rhino/lib/rhino-1.7.14.jar` 列为"锁定版本，不变更"，但 spec 要删除它。Phase 5 文档同步仅提及签名密钥和 INDEX.md，未提及此条目更新。删除 jar 后文档描述将变为虚假信息。
- **源码证据**: [git-repo-management.md:214](file:///f:/myself/github/WeAgentChat/temp/legado/docs/project-flow/git-repo-management.md#L214)
- **整改替换文本**:

**design.md "Phase 5: 文档同步" 替换为**:

```markdown
### Phase 5: 文档同步

- 更新 `docs/INDEX.md`：移除 `docs/temp-analysis/` 引用
- 更新 `docs/project-flow/git-repo-management.md`：
  - L214 移除 `modules/rhino/lib/rhino-1.7.14.jar` 条目（已删除，改用 Gradle 依赖 `libs.mozilla.rhino`）
  - 签名密钥说明改为 GitHub Secrets 注入
- 更新 `docs/project-flow/architecture/ci-cd-pipeline.md` L108-112：移除明文密码
- 更新 `docs/project-flow/build-apk-guide.md` L238：签名文件来源说明
- 更新 `docs/project-rules/forks_comparison_methodology.md` L509-512：移除或更新 temp-analysis 链接
- 更新 `docs/specs/network-perf-stability/README.md` L156-163：移除或更新 temp-analysis 链接
```

**tasks.md Phase 5 替换为**:

```markdown
## Phase 5: 文档同步

### T5.1 更新 docs/INDEX.md
- 移除 `docs/temp-analysis/` 引用

### T5.2 更新 git-repo-management.md
- 移除 L214 `modules/rhino/lib/rhino-1.7.14.jar` 条目
- 签名密钥说明改为 GitHub Secrets 注入

### T5.3 更新 CI/构建相关文档
- `docs/project-flow/architecture/ci-cd-pipeline.md`：移除明文密码，改为 Secrets 说明
- `docs/project-flow/build-apk-guide.md` L238：签名文件来源改为 GitHub Secrets

### T5.4 更新 temp-analysis 链接引用
- `docs/project-rules/forks_comparison_methodology.md` L509-512：链接改为纯文本说明
- `docs/specs/network-perf-stability/README.md` L156-163：链接改为纯文本说明

### T5.5 更新其他引用文档
- `docs/project-flow/architecture/multi-agent-analysis-spec.md`：temp-analysis 路径改为本地目录说明
- `docs/project-rules/complex-task-pipeline.md` L27：同上
```

---

#### H3: git filter-repo 在当前环境不可用

- **缺陷定位**: design.md "Phase 3" 第5步可选操作
- **问题本质**: `git filter-repo` 未安装（`ModuleNotFoundError: No module named 'git_filter_repo'`），且 design.md 未提供安装方式或替代方案。Windows 环境下安装 git-filter-repo 需额外步骤。
- **整改替换文本**:

**design.md Phase 3 第5步替换为**:

```markdown
5. **可选**: 清理 git 历史中的 .jks 文件（需安装 git-filter-repo）：
   ```bash
   # 安装 git-filter-repo（Windows + Python 3）
   pip install git-filter-repo
   # 执行历史清理
   git filter-repo --path .github/workflows/legado.jks --invert-paths --force
   # 注意：需要 force push，所有协作者需重新克隆
   ```
   替代方案（若 git-filter-repo 安装失败）：
   ```bash
   # 使用 BFG Repo-Cleaner（需 Java）
   java -jar bfg.jar --delete-files legado.jks
   git reflog expire --expire=now --all && git gc --prune=now --aggressive
   ```
```

---

#### H4: test_rss_sources.json 引用描述不准确

- **缺陷定位**: spec.md "2.3 需用户确认的文件" 第11行
- **问题本质**: spec 声称 `test_sources.json` + `test_rss_sources.json` "被 e2e_test.py 引用"，但源码验证只有 `test_sources.json` 被 e2e_test.py L13 引用，`test_rss_sources.json` 无任何代码引用。描述不准确可能导致误判。
- **整改替换文本**:

**spec.md "2.3 需用户确认的文件" 第11行替换为**:

```markdown
| 11 | `test_sources.json` + `test_rss_sources.json` | 测试数据 JSON | `test_sources.json` 被 e2e_test.py L13 引用；`test_rss_sources.json` 无代码引用，完全孤立 | git rm --cached 移除跟踪，保留本地 |
```

---

### 中级问题

#### M1: .trae/documents/ 下可能的废弃规划文档

- **缺陷定位**: spec.md "2.1 明确废弃文件" 表（遗漏）
- **问题本质**: `.trae/documents/` 下有 3 个规划文档被 git 跟踪：
  - `source-layout-deep-refactor.md` - 书源布局深度重构方案（已有 `docs/specs/source-layout-redesign/` 正式 spec）
  - `source-layout-refactor-continuation.md` - 仅被 `docs/specs/source-layout-redesign/tasks.md` 引用
  - `speed-dialog-ui-optimization.md` - 无任何外部引用，完全孤立
- **整改建议**: 将 `speed-dialog-ui-optimization.md` 加入 spec.md 2.1 表（无引用，可安全删除）；`source-layout-*.md` 需用户确认是否已完成沉淀到正式 spec。

---

#### M2: modules/rhino/lib/ 删除 jar 后为空目录

- **缺陷定位**: design.md Phase 1+2 git rm 命令
- **问题本质**: 删除 `modules/rhino/lib/rhino-1.7.14.jar` 后，`lib/` 目录将变为空目录。git 不跟踪空目录，但设计中未明确是否需要处理空目录遗留。
- **整改替换文本**:

**design.md Phase 1+2 git rm 命令中 rhino 行替换为**:

```bash
git rm modules/rhino/lib/rhino-1.7.14.jar
# 删除空目录（git 不跟踪空目录，但清理文件系统）
rmdir modules/rhino/lib 2>/dev/null || true
```

---

#### M3: .gitignore 规则不够完善

- **缺陷定位**: design.md ".gitignore 追加" 段
- **问题本质**: 当前 .gitignore 缺少以下规则：
  - `ksp_info.txt` 或 `ksp_*.txt` -- 构建日志
  - `.trae/documents/` -- AI 临时规划文档（如果决定清理的话）
  - 现有 L54-55 的 `.bak` 和 `.class` 规则只针对特定文件，不够通用
- **整改替换文本**:

**design.md .gitignore 追加段替换为**:

```gitignore
# 防止再次提交废弃文件
docs/temp-analysis/
*.bak
*.class
avd.bat
avd.sh
ksp_info.txt
# 防止再次提交构建日志
ksp_*.txt
```

---

#### M4: Skill 脚本目录存在大量可能废弃的一次性脚本

- **缺陷定位**: spec.md "2.3 需用户确认的文件"（遗漏）
- **问题本质**: `.trae/skills/legado-source-creator/scripts/` 下有 70+ 个 Python 脚本，其中至少 20+ 个看起来是一次性调试/测试脚本（如 `debug-single.py`, `ws_test.py`, `ws_test2.py`, `test-real-biquge.py`, `verify-decrypt.py` 等）。spec 仅识别了 `dedup_sources.py` 和 `dedup_sources_v2.py` 两个废弃脚本，遗漏了大量同类文件。
- **整改建议**: 在 spec.md 2.3 表中追加一行说明，建议用户对 scripts/ 目录做一次全面审计，识别更多一次性脚本。

---

#### M5: ci-cd-pipeline.md 暴露明文密码需同步更新

- **缺陷定位**: design.md "Phase 5: 文档同步"
- **问题本质**: `docs/project-flow/architecture/ci-cd-pipeline.md` L111-112 包含明文密码 `gedoor_legado`，Phase 5 文档同步未将其纳入更新范围。
- 已整合至 H2 的 Phase 5 替换文本中（T5.3）。

---

#### M6: design.md SymmetricDecryptor 验证结论需补充说明

- **缺陷定位**: design.md "1.1 明确可安全删除" 表
- **问题本质**: `SymmetricDecryptor` 在 `SymmetricCryptoAndroid.kt:60` 有源码提及（注释中引用了接口名），design.md 声称"无任何 Java 源码引用"不完全准确。虽然该引用是指 hutool 库的接口（来自 Gradle 依赖），而非根目录的 .class 文件，但应补充说明以避免误解。
- **整改替换文本**:

**design.md "1.1 明确可安全删除" 表 SymmetricDecryptor 行替换为**:

```markdown
| `cn/hutool/.../SymmetricDecryptor.class` | Grep `SymmetricDecryptor` in *.kt | `SymmetricCryptoAndroid.kt:60` 注释中提及该接口名，但引用来自 Gradle hutool 依赖，非根目录 .class 文件。**根目录 .class 文件孤立，可安全删除** |
```

---

## 二、验证结果汇总

| 待删文件 | 源码验证结论 | 安全删除? |
|---------|-------------|----------|
| `AGENTS.md.bak` | 无代码引用，仅 spec 描述性引用 | YES |
| `classes.jar` | 无 Gradle 配置引用；`ksp_info.txt` 中的 `classes.jar` 是 Gradle 内部构建产物路径，非本文件引用 | YES |
| `gsy.aar` | 无任何 Gradle/代码引用 | YES |
| `cn/hutool/.../SymmetricDecryptor.class` | 根目录 .class 文件孤立；源码中 hutool 引用来自 Gradle 依赖 | YES（补充说明） |
| `app/cronetlib_149_backup/` | 无代码/构建引用 | YES |
| `avd.bat` + `avd.sh` | 无任何文件引用 | YES |
| `docs/temp-analysis/` | **12 个活跃 markdown 链接** 会断链 | **NO -- 需先修复链接** |
| `modules/rhino/lib/rhino-1.7.14.jar` | build.gradle L38 已注释；lib/ 目录删除后为空 | YES（需删除空目录） |
| `ksp_info.txt` (**遗漏**) | 无任何引用，38KB 构建日志 | YES（应加入清单） |
| `.github/workflows/legado.jks` | test.yml L172 引用；**L176-177 还有明文密码** | 需改造（含密码） |

---

## 三、遗漏发现

| 文件 | 类型 | 大小 | 引用情况 | 建议操作 |
|------|------|------|---------|---------|
| `ksp_info.txt` | 构建日志 | 38KB | 无引用 | 加入 spec 2.1 表，git rm |
| `.trae/documents/speed-dialog-ui-optimization.md` | 规划文档 | - | 无外部引用 | 建议加入 spec 2.3 表确认删除 |
| `.trae/documents/source-layout-deep-refactor.md` | 规划文档 | - | 已有正式 spec | 建议加入 spec 2.3 表确认删除 |
| `.trae/documents/source-layout-refactor-continuation.md` | 规划文档 | - | 仅被 source-layout-redesign/tasks.md 引用 | 建议加入 spec 2.3 表确认 |
| Skill scripts/ 目录 20+ 一次性脚本 | 调试脚本 | - | 大多无外部引用 | 建议用户全面审计 |

---

## 四、阻塞点

| 阻塞点 | 严重程度 | 说明 | 解决方案 |
|--------|---------|------|---------|
| temp-analysis 链接断链 | **阻断** | 删除目录后 network-perf-stability/README.md 和 forks_comparison_methodology.md 中 12 个链接失效 | 先修复链接再删除（见 B1 整改） |
| test.yml 明文密码 | **阻断** | 仅移 .jks 不处理密码，安全改造不完整 | 同步改造密码注入（见 B2 整改） |
| git filter-repo 不可用 | 高 | 系统未安装，Phase 3 可选步骤无法执行 | 补充安装说明或 BFG 替代方案（见 H3 整改） |
| git-repo-management.md 虚假信息 | 高 | 删除 rhino jar 后文档仍描述"不变更" | Phase 5 同步更新（见 H2 整改） |

---

## 五、安全问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| test.yml L176-177 明文密码 | **高** | `gedoor_legado` 硬编码在 workflow 中，任何有仓库读权限者可见 |
| ci-cd-pipeline.md L111-112 暴露密码 | 中 | 文档中记录了明文密码 |
| .jks 文件是唯一敏感文件 | 低 | `git ls-files -- "*.jks" "*.keystore"` 仅返回 `.github/workflows/legado.jks`，无其他签名密钥 |
| test_sources.json / test_rss_sources.json | 低 | 验证结构含源数据 JSON（按输出安全规范未读取内容），结构为 JSON 数组，`git rm --cached` 处理方式正确 |

---

## 六、修改建议汇总

| 优先级 | 问题编号 | 修改文件 | 修改章节 | 修改类型 |
|--------|---------|---------|---------|---------|
| 阻断 | B1 | design.md | 1.1 表 + Phase 1+2 | 修改验证结论 + 新增前置步骤 |
| 阻断 | B1 | tasks.md | T1.4 | 拆分为链接修复+删除两步 |
| 阻断 | B2 | design.md | Phase 3 | 整段替换，含密码改造 |
| 阻断 | B2 | tasks.md | Phase 3 | 整段替换，新增 T3.4/T3.5 |
| 高 | H1 | spec.md | 2.1 表 | 追加 ksp_info.txt 行 |
| 高 | H1 | design.md | 1.1 表 + Phase 1+2 + .gitignore | 追加 ksp_info.txt |
| 高 | H1 | tasks.md | T1.1 + T2.1 | 追加 ksp_info.txt |
| 高 | H2 | design.md | Phase 5 | 扩展文档同步范围 |
| 高 | H2 | tasks.md | Phase 5 | 拆分为 T5.1-T5.5 |
| 高 | H3 | design.md | Phase 3 第5步 | 补充安装说明和替代方案 |
| 高 | H4 | spec.md | 2.3 表第11行 | 修正引用描述 |
| 中 | M1 | spec.md | 2.3 表 | 追加 .trae/documents/ 确认项 |
| 中 | M2 | design.md | Phase 1+2 | 追加空目录清理 |
| 中 | M3 | design.md | .gitignore | 追加 ksp_*.txt 规则 |
| 中 | M4 | spec.md | 2.3 表 | 追加 scripts/ 审计建议 |
| 中 | M6 | design.md | 1.1 表 | 补充 SymmetricDecryptor 说明 |

---

## 七、多维度评审汇总

| 维度 | 合规项 | 问题项 | 判定依据 |
|------|--------|--------|---------|
| 代码一致性 | 7/8 文件验证结论正确 | SymmetricDecryptor 描述不精确(M6)；test_rss_sources.json 引用描述错误(H4) | Grep 源码验证 |
| 技术成熟度 | Git rm / .gitignore / GitHub Secrets 方案成熟 | git filter-repo 不可用(H3)；test.yml 密码改造遗漏(B2) | 实测验证 |
| 落地可执行性 | Phase 1+2 任务粒度合理 | temp-analysis 删除无前置链接修复(B1)；Phase 5 文档同步范围不足(H2) | 链接可达性验证 |
| OpenSpec 合规性 | 四文件架构清晰 | MUST 级需求"安全合规"未完全落地（密码仍明文） | RFC 2119 对照 |
| 全需求覆盖 | 8 项明确废弃基本覆盖 | ksp_info.txt 遗漏(H1)；.trae/documents/ 遗漏(M1)；scripts/ 遗漏(M4) | git ls-files 排查 |
| 完备性 | 风险评估基本覆盖 | 链接断链风险未识别(B1)；空目录遗留未处理(M2) | 边界场景分析 |

---

## 八、问题优先级整改清单

| 优先级 | 编号 | 问题位置 | 问题描述 | 整改建议 |
|--------|------|---------|---------|---------|
| 阻断 | B1 | design.md 1.1 + Phase 1+2; tasks.md T1.4 | temp-analysis 删除会断 12 个链接 | 先修复链接再删除 |
| 阻断 | B2 | design.md Phase 3; tasks.md Phase 3 | test.yml 明文密码未处理 | 同步改造密码注入 |
| 高 | H1 | spec.md 2.1; design.md; tasks.md | ksp_info.txt 遗漏 | 加入清理清单 |
| 高 | H2 | design.md Phase 5; tasks.md Phase 5 | 文档同步范围不足 | 扩展至 5 个更新任务 |
| 高 | H3 | design.md Phase 3 第5步 | git filter-repo 不可用 | 补充安装/替代方案 |
| 高 | H4 | spec.md 2.3 表第11行 | test_rss_sources.json 引用描述错误 | 修正描述 |
| 中 | M1 | spec.md 2.3 表 | .trae/documents/ 遗漏 | 追加确认项 |
| 中 | M2 | design.md Phase 1+2 | 空目录遗留 | 追加 rmdir |
| 中 | M3 | design.md .gitignore | 规则不够完善 | 追加 ksp_*.txt |
| 中 | M4 | spec.md 2.3 表 | Skill 一次性脚本遗漏 | 追加审计建议 |
| 中 | M6 | design.md 1.1 表 | SymmetricDecryptor 描述不精确 | 补充说明 |

---

## 九、需求遗漏专项说明

1. **ksp_info.txt**（38KB 构建日志）-- 完全未出现在排查结果中，应加入 spec.md 2.1 表第9项
2. **test.yml 明文密码** -- spec.md FR-4 "安全文件处理"仅提及 .jks，未涵盖 workflow 中的硬编码密码，需求定义不完整
3. **.trae/documents/ 临时规划文档** -- 至少 `speed-dialog-ui-optimization.md` 完全无引用，应纳入排查范围
4. **Skill scripts/ 一次性脚本** -- 20+ 调试/测试脚本未纳入排查，spec 仅识别了 2 个重复脚本

---

## 十、整体评审结论与量化评分

**判定结果**: **需要整改后落地**

存在 2 个阻断级问题（temp-analysis 链接断链 + test.yml 明文密码），完成上述全部整改后方可实施。

**量化评分**（0-100分）:

| 维度 | 评分 | 说明 |
|------|------|------|
| 代码匹配度 | 82 | 8 项中 7 项验证结论正确，1 项描述不精确；1 项引用描述错误 |
| 技术成熟度 | 75 | 核心方案成熟，但 git filter-repo 不可用，密码改造遗漏 |
| 落地清晰度 | 68 | temp-analysis 删除缺前置步骤，Phase 5 文档同步范围不足，遗漏 ksp_info.txt |

---

## 十一、整改后落地可行性最终确认

完成 B1+B2+H1+H2+H3+H4 六项整改后，该文档可支撑落地。执行人员按整改后的 tasks.md 顺序执行即可，无需额外设计或二次拆解。

关键前提：
1. B1 的 temp-analysis 链接修复必须在删除目录前完成
2. B2 的 GitHub Secrets 配置必须由用户手动完成（涉及仓库设置权限）
3. H3 的 git filter-repo 为可选步骤，不影响核心流程
