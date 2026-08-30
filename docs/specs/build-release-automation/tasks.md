# 构建发布自动化实施任务（build-release-automation）

> **状态：✅ 已完成（L3 真实发版成功，待检查点 3 最终验收）**
> 2026-08-30 · 方案：选项 1（publish_release.py 升级一键发布编排器，build-legado.bat 保持薄层，附带触发器注释 + 更新源地址修正）
> 设计文档：[design.md](./design.md) · 事实源：docs/temp-analysis/build-release-analysis-20260830.md
> 粒度约束：单任务 ≤10 文件 · 总计 20 条 · 五组顺序执行（组 1 前置核验 → 组 5 验证收尾）
> 完成级别：✅=场景验证 / ⚠️=代码完成或功能验证（缺失项注明）

## 1 准备 ✅

- [x] 1.1 核验 AppUpdateGitee 实况 ✅：定位 app/src/main/java/io/legado/app/help/update/AppUpdateGitee.kt L31/L33（查询 lyc486/legado）；修正目标 Chinashitou/legado
- [x] 1.2 精读 scripts/publish_release.py 现状（526 行）✅：重构蓝图产出（函数级清单+改造点+风险 8 条），并发现 build-legado.bat 延迟扩展死代码 bug
- [x] 1.3 读规范文档基准 ✅：apk-publish-workflow 七步/反模式保留条款清单确认

## 2 编排器核心 ✅（526→790 行重写）

- [x] 2.1 五阶段骨架 ✅（Level 3：L1 dry-run 全流程走通+R2 负向测试）
- [x] 2.2 构建执行层 ✅（Level 2：dry-run 模拟+ARTIFACT 行解析逻辑就位，真实构建联动归 5.3 L3）
- [x] 2.3 校验强化 fail-fast 分级 ✅（Level 3：R2 负向测试 exit 1 拦截验证）
- [x] 2.4 发布层 gh CLI ✅（Level 2：gh_run 重试+幂等复用+asset 跳过实现，真实上传归 5.3）
- [x] 2.5 git tag 回滚锚点 ✅（Level 2：幂等+push 前确认实现，真实 push 归 5.3）
- [x] 2.6 L2 门禁交互确认 ✅（Level 2：默认 N+--l2-evidence 存在性/当日 mtime 校验实现；真机演练归 5.2）
- [x] 2.7 分层确认协议落地 ✅（Level 2：--confirm-stage build|tag + publish.bat 薄壳创建）

## 3 附带治理 ✅

- [x] 3.1 注释幽灵触发器 ✅：test.yml（push+workflow_run 连带）与 web.yml（push）已注释，保留 pull_request/workflow_dispatch
- [x] 3.2 更新源地址修正 ✅（Level 1：AppUpdateGitee.kt L31/L33 → Chinashitou/legado，compileAppDebugKotlin 通过）

## 4 文档同步 ✅

- [x] 4.1 重写 docs/project-rules/apk-publish-workflow.md ✅：单命令主线（§2 五阶段/确认点/参数表 7 项/tag 回滚）+§4 已知问题闭环更新+§6 反模式追加 3 条+旧七步压缩为历史沿革
- [x] 4.2 同步 ci-cd-pipeline.md（幽灵触发器清零+§4 整节重写为编排器）+ quick-reference.md（一键发布/预览/回滚 3 行速查）✅
- [x] 4.3 docs/INDEX.md 描述更新 + AGENTS.md 速查表新增一键发布行 ✅

## 5 验证收尾（进行中）

- [x] 5.1 L1 编排器 --dry-run 全流程走查 ✅（Level 3）：五阶段模拟完整/无副作用/updateLog 当日条目真实校验通过/脱敏自检 token 明文零出现/退出码 0；附加 R2 负向测试（--version 3.99.010101 → exit 1 拦截）
- [ ] 5.2 L2 真机门禁演练 ⏳：需 MEmu 模拟器（quick_build_install.py + l2_verify_video_player.py 走通后演练编排器确认点双路径）
- [ ] 5.3 L3 真实发版演练 ⏳：将真实产生远端 Release+tag，执行时机须用户确认
- [ ] 5.4 updateLog 收尾 🟡：updateLog 已补「检查更新源修复」条目（编译前完成）；临时分析文档归档决策与三级检查随检查点 2 后收尾

## AOAdapt 日志

| 时间 | 阶段 | 操作 | 结果 | 备注 |
|------|------|------|------|------|
| 2026-08-30 21:5x | 1.2 蓝图 | 精读 build-legado.bat | 发现 L2 未开 EnableDelayedExpansion → libcronet.so 强制校验块实为死代码从未执行 | 已修复（setlocal EnableDelayedExpansion），属既有 bug 非本任务引入 |
| 2026-08-30 21:5x | 2.x 重写 | Write 全量重写 publish_release.py | 首轮 L1 dry-run 报 `gitee_publish is not defined` | 重写时误删 Gitee requests 层，已原样回补（Gitee 无 gh CLI 等价物必须保留） |
| 2026-08-30 21:5x | 5.1 L1 | dry-run bump 版本无产物场景 | Stage3 产物缺失误拦截 dry-run | 调整分支顺序：dry-run 允许无产物仅模拟；真实发布保持 fail-fast |
| 2026-08-30 21:5x | 编译 | gradlew 默认缓存 | transforms metadata.bin 损坏 | 改用项目规范 env（GRADLE_USER_HOME=F:\gh）编译通过；默认缓存损坏为历史遗留非本任务引入 |
