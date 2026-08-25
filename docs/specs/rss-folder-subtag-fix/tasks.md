# tasks.md — 订阅文件夹样式：点进文件夹头部误显标签/箭头

## 1. 准备工作

- [x] 1.1 复核 `renderRssSecondaryTags()` 现行逻辑与 `applyView()` 的标签隐藏交互（已定位根因）

## 2. 核心实现

- [x] 2.1 在 `renderRssSecondaryTags()` 入口加 `if (!isTagMode)` 守卫，非标签样式 `showTags(false)` 后 return
- [x] 2.2 确认 `applyView()` 现有逻辑无需改动（非标签模式本已隐藏标签）

## 3. 验证

- [x] 3.1 编译通过（`./gradlew assembleAppDebug`，App 前缀）※ compileAppDebugKotlin exit 0
- [x] 3.5 updateLog 同步 + 无残留调试日志（本次改动未新增日志；Grep 无新增调试点）
- [ ] 3.2 文件夹样式：主页目录无标签 → 点进文件夹子列表头无标签/无向下箭头（待真机）
- [ ] 3.3 标签样式：primaryBar + tagsBar + 向下箭头正常展示（待真机）
- [ ] 3.4 返回键回文件夹目录：仍隐藏标签（待真机）

## AOAdapt 日志

- 无阻塞问题。