# Repo Cleanup - 任务清单

## 任务概览

| Phase | 任务数 | 风险 | 前置依赖 |
|-------|--------|------|---------|
| Phase 1+2: 安全删除+.gitignore | 7 | 低 | 无 |
| Phase 1.5: 断链修复 | 2 | **阻断** | Phase 1+2 |
| Phase 3: 签名密钥与密码安全化 | 5 | 中 | Phase 1.5 |
| Phase 4: Skill 清理 | 3 | 中 | 需用户确认 |
| Phase 5: 文档同步 | 3 | 低 | Phase 1-4 |

---

## Phase 1+2: 安全删除 + .gitignore

### T1.1 删除根目录废弃文件
- `git rm AGENTS.md.bak classes.jar gsy.aar avd.bat avd.sh ksp_info.txt`
- 验证：`git status` 确认 6 文件已删除
- 回滚：`git checkout HEAD -- <file>`

### T1.2 删除反编译 .class 文件
- `git rm -r cn/`（仅含 1 个 .class 文件）
- 验证：cn/ 目录整体删除
- 回滚：`git checkout HEAD -- cn/`

### T1.3 删除 Cronet 旧版备份
- `git rm -r app/cronetlib_149_backup/`
- 验证：确认 `app/cronetlib/` 仍在
- 回滚：`git checkout HEAD -- app/cronetlib_149_backup/`

### T1.4 删除旧版 rhino jar
- `git rm modules/rhino/lib/rhino-1.7.14.jar`
- 验证：编译 `./gradlew :modules:rhino:compileKotlin`
- 回滚：`git checkout HEAD -- modules/rhino/lib/rhino-1.7.14.jar`

### T2.1 更新 .gitignore 并提交
- 追加规则：`docs/temp-analysis/` / `*.bak` / `*.class` / `avd.bat` / `avd.sh` / `ksp_info.txt`
- 与 T1.1-T1.4 合并提交
- commit: `chore: remove abandoned temp files, backup jars, and build logs`

**注意**：`docs/temp-analysis/` 暂不删除，需先完成 Phase 1.5 断链修复。

---

## Phase 1.5: 断链修复（阻断级）

### T1.5a 修复 network-perf-stability/README.md 断链
- 文件：`docs/specs/network-perf-stability/README.md`
- 8 个链接指向 `docs/temp-analysis/`
- 修复方式：移除链接或替换为 specs/ 内对应文档

### T1.5b 修复 forks_comparison_methodology.md 断链
- 文件：`docs/project-rules/forks_comparison_methodology.md`
- 4 个链接指向 `docs/temp-analysis/`
- 修复方式：移除链接或替换为 project-rules/ 内对应文档

### T1.5c 删除 docs/temp-analysis/ 并提交
- 前提：T1.5a + T1.5b 验证无断链
- `git rm -r docs/temp-analysis/`
- commit: `docs: fix broken links to temp-analysis before removal`

---

## Phase 3: 签名密钥与密码安全化

### T3.1 编码签名密钥
- `base64 -w 0 .github/workflows/legado.jks` 记录输出
- 验证：base64 字符串可还原为 .jks

### T3.2 配置 GitHub Secrets（6 个）
- `SIGNING_KEY_BASE64` = base64 编码的 jks
- `KEY_STORE_PASSWORD` / `KEY_ALIAS` / `KEY_PASSWORD`
- `TEST_STORE_PASSWORD` / `TEST_KEY_PASSWORD`（test.yml 专用）
- 验证：GitHub Settings → Secrets 中确认存在

### T3.3 修改 CI workflow
- 修改 `.github/workflows/test.yml`：
  - L172：`echo "${{ secrets.SIGNING_KEY_BASE64 }}" | base64 -d > $GITHUB_WORKSPACE/app/legado.jks`
  - L176：`RELEASE_STORE_PASSWORD=${{ secrets.KEY_STORE_PASSWORD }}`
  - L177：`RELEASE_KEY_PASSWORD=${{ secrets.KEY_PASSWORD }}`
- 验证：push 分支后 CI 运行成功

### T3.4 删除仓库中的 .jks
- 前提：T3.2 + T3.3 验证通过
- `git rm .github/workflows/legado.jks`
- commit: `security: move signing key and passwords from repo to GitHub Secrets`

### T3.5 可选：清理 git 历史
- `pip install git-filter-repo`
- `git filter-repo --path .github/workflows/legado.jks --invert-paths`
- `git push --force`
- **注意**：需所有协作者重新克隆

---

## Phase 4: Skill 脚本清理（需用户确认）

### T4.1 删除重复迭代脚本
- `git rm .trae/skills/.../dedup_sources.py .trae/skills/.../dedup_sources_v2.py`
- 保留：`smart_dedup_v3.py`

### T4.2 移除测试数据 JSON
- `git rm --cached .trae/skills/.../test_sources.json`（被 e2e_test.py 引用，保留本地）
- `git rm .trae/skills/.../test_rss_sources.json`（无代码引用，直接删除）
- .gitignore 追加：`.trae/skills/*/scripts/test_*.json`

### T4.3 删除 test-encoding.txt
- `git rm docs/specs/legado-skill-v2-rebuild/test-encoding.txt`

---

## Phase 5: 文档同步

### T5.1 更新 docs/INDEX.md
- 移除 `docs/temp-analysis/` 引用

### T5.2 更新 git-repo-management.md
- rhino-1.7.14.jar 从"不变更"改为"已移除"
- 签名密钥改为 GitHub Secrets 注入
- .gitignore 新增规则说明

### T5.3 更新 ci-cd-pipeline.md
- 移除明文密码引用

---

## 执行约束

| 约束 | 说明 |
|------|------|
| Phase 1+2 合并提交 | 删除和 .gitignore 同一次 commit |
| Phase 1.5 是阻断级 | docs/temp-analysis/ 删除前必须修复 12 个断链 |
| Phase 3 需 GitHub 操作 | 用户需手动配置 6 个 Secrets |
| Phase 4 需用户确认 | Skill 脚本不能擅自删 |
| 每个 Phase 完成后 AskUserQuestion | 强制交互规范 |
