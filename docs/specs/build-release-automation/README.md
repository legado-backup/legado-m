# build-release-automation — 打包发布体系自动化优化

> 状态：✅ 已完成（2026-08-31 最终验收通过；L3 真实发版成功，Release 3.26.083022 三包齐全+tag 已推送）
> 生成日期：2026-08-30

## 功能概述

对打包发布体系做自动化优化，对标阅读NG（Next Generation Legado）的 CI/CD 全自动发版能力。经方案对比（GitHub Actions 恢复+加固 / 本地+云端混合 / 本地全自动增强），选定**"本地全自动增强"路线**：将现有 `publish_release.py`（526 行）升级为**一键发布编排器**，串联"版本确认 → 三包构建 → 校验强化 → gh release 上传 → git tag 推送"五阶段全流程；`build-legado.bat`（249 行，含 `:STOP_DAEMON` 清场与 libcronet.so 强制校验）保持薄构建层不动。

本 spec 直接回应现有发版链路的五大痛点：两次手工命令割裂、校验 WARN 不阻断（fail-fast 缺失）、无 git tag 回滚锚点、上游遗产 workflow 的幽灵 CI 触发器、检查更新源地址与实际发布仓不一致。

## 核心能力

1. **一键发布编排**：单命令完成"版本确认 → test/release/coexist 三包依次构建 → 校验强化 → gh release 上传 → git tag 推送"全流程，消除两次手工命令割裂。
2. **校验强化 fail-fast**：updateLog 当日条目缺失、三包产物缺失均从 WARN 升级为 exit 非零；libcronet.so 校验保留 exit 1 级别；新增 apksigner 验签 + 包名/版本三包一致性校验。
3. **门禁不可绕过**：真机 L2 测试交互式确认（默认 N 拒绝，禁止 --force-skip；AI 代答必须绑定 `--l2-evidence` 当日 L2 报告，证据校验不过即拒绝）；三包全上传且 test 包带 `_debug` 后缀命名防冲突，上传前逐包包名断言防混发；每包构建后内嵌 daemon 清场（等价 `:STOP_DAEMON`）。
4. **双形态入口**：人工双击 `publish.bat`（薄壳，交互式确认链）；AI 场景 `python scripts/publish_release.py` + AskUserQuestion 代答确认（`--confirm-stage` 续跑 + L2 证据绑定），门禁由用户亲自放行并留痕。
5. **发布与回滚锚点**：gh CLI 上传替代 requests（规避 uploads.github.com SSL 与 51MB+ 大文件双坑）；git tag push 前打印供人工确认，形成版本回滚锚点。
6. **幽灵 CI 清理**：注释 test.yml / web.yml 的 push 触发器（secrets 未配置的空转失败源），注释后 push 零 CI 运行。
7. **更新源一致性修复**：AppUpdateGitee.kt 查询的旧仓地址与脚本实际发布仓对齐，消除应用内"检查更新"失效 bug。

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 设计规格：Intent / Scope / Approach（含 Alternatives + Drawbacks + Prior Art）/ Requirements / Scenarios / 编排器五阶段流程图 |
| [../../temp-analysis/build-release-analysis-20260830.md](../../temp-analysis/build-release-analysis-20260830.md) | 事实源：打包发布体系深度分析报告（NG 论断清单 / 本项目现状盘点 B1-B6 / 差距分析 / 方案选项 D / 门禁边界 E） |

## 状态标记

- ✅ 已完成（2026-08-31）：20/20 任务完成，L1 dry-run 全绿 + L2 真机验证 + L3 真实发版成功（Release 3.26.083022 三包齐全+tag 回滚锚点）
- 使用方式：`publish.bat`（人工交互）或 `ai_tests\venv\Scripts\python.exe scripts\publish_release.py`（AI 代答，--confirm-stage/--l2-evidence）；`--dry-run` 预览
- 遗留：Gitee token 未配置（补后 --platform both 可用）；l2_verify_video_player 待有源环境补测
