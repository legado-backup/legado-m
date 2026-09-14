# 视频播放器多线路多集状态残留修复 — Tasks

## 1. 核心实现

- [ ] 1.1 在 `VideoPlay.initSource` 开头（`isLoading = true` 之后）清空
      `rssRoutes`/`rssEpisodes`/`rssRouteIndex`/`rssEpisodeIndex`，并添加注释说明意图
      - 验证标准：Grep 确认清空代码存在且位于 `isLoading = true` 之后、`source` 加载之前

## 2. 验证测试

- [ ] 2.1 编译通过：`./gradlew assembleAppDebug` 无编译错误（L1）
- [ ] 2.2 静态核查：Grep `VideoPlay.rssRoutes` 全部读取点均为 null 安全访问（L2）
- [ ] 2.3 场景核查（静态）：确认 `isNew=false` 悬浮窗恢复路径不经过 `initSource`（L2）

## 3. 文档收尾

- [ ] 3.1 更新 `app/src/main/assets/updateLog.md`（基于 git diff 提炼面向用户变更说明）
- [ ] 3.2 更新 `docs/specs/INDEX.md` 增加本 spec 条目（状态：开发中）
- [ ] 3.3 检查 issues-found/ai_memory_main 是否需同步；无对应文档则注明
