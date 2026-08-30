# Design: 同步阅读 Sigma 2026-07 最新提交

## Technical Approach

逐文件精准同步 4 个上游提交的变更，按优先级执行：P0 bug 修复 → P1 订阅源更新 → P2 配置默认值。

## Architecture Decisions

### AD-01: 手动同步而非 git merge/cherry-pick
- **Context**: 上游 Sigma 仓库 7228 commits ahead，且我们已有 Sigma 没有的 UI/UX 优化
- **Concern**: 直接 merge 或 cherry-pick 可能引入大量冲突或意外变更
- **Decision**: 手动逐文件同步 4 个提交的 5 个文件 7 处修改
- **Goal**: 最小化变更范围，确保只引入目标提交的修改
- **Tradeoff**: 需要手动对比和验证，但变更量小（7处），可控
- **Status**: Accepted

### AD-02: 订阅源 JSON 整体替换而非局部修改
- **Context**: rssSources.json 文件较大，局部修改容易出错
- **Concern**: CSS 选择器和域名变更涉及嵌套 JSON 结构
- **Decision**: 下载上游完整 rssSources.json 替换本地文件
- **Goal**: 确保订阅源数据与上游完全一致
- **Tradeoff**: 无法增量对比，但文件由上游维护，整体替换更安全
- **Status**: Accepted

## Data Flow

```
上游 GitHub (Luoyacheng/legado)
    │
    ├─ commit 844867b → AppWebDav.kt, ReadBookActivity.kt, BgTextConfigDialog.kt
    ├─ commit 98b73c7 → rssSources.json
    ├─ commit 0a6bb89 → AppConfig.kt (preDownloadNum)
    └─ commit 25f4fcd → AppConfig.kt (threadCount)
    
本地项目
    ├─ AppWebDav.kt ← 2处 return → return@forEach
    ├─ ReadBookActivity.kt ← joinToString + case 13
    ├─ BgTextConfigDialog.kt ← arrayListOf(1,2,5,13)
    ├─ rssSources.json ← 整体替换
    └─ AppConfig.kt ← threadCount 16→32, preDownloadNum 10→2
```

## File Changes

| 文件 | 变更类型 | 修改处数 | 优先级 |
|------|---------|---------|--------|
| AppWebDav.kt | Bug 修复 | 2 | P0 |
| ReadBookActivity.kt | Bug 修复 + 优化 | 2 | P0/P2 |
| BgTextConfigDialog.kt | Bug 修复 | 1 | P0 |
| rssSources.json | 数据更新 | 1 | P1 |
| AppConfig.kt | 默认值调整 | 2 | P2 |
