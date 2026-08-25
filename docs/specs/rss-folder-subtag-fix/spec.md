# spec.md — 订阅文件夹样式：点进文件夹头部误显标签/箭头

## Intent

订阅页布局设为「文件夹样式」（`sourceGroupStyle != 0 && sourceGroupMode == 1`，触发文件夹视图）时：

- 主页面 = 文件夹目录，头部无标签（正确）。
- **点击一个文件夹进入子列表后**，头部错误地多出「向下箭头」（`filterToggleButton`）和一个「标签体系下的子标签」（`tagsBar` 二级源标签）。

用户明确要求：**只有「标签样式」才展示标签体系，文件夹样式任何时候都不应展示。**

## Scope

### In-Scope（本次实现）

1. 修复 `renderRssSecondaryTags()` 无条件 `showTags(true)` 导致的标签/箭头误显。
2. 使二级源标签（`tagsBar`）仅在标签样式（`isTagMode`）下展示；文件夹样式点进文件夹后的列表视图保持标签隐藏。

### Out-of-Scope（本次不实现）

- 不改配置字段、不改数据结构、不改数据库。
- 不改变 `isFolderViewMode` / `isTagMode` / `isShowingFolder` 运行状态语义。
- 不影响「列表平铺」（`sourceGroupStyle == 0`）之外的其他形态逻辑分支。
- 不改 `MainTopBarView`、`RoundedTagBarView` 组件本身。

## Approach

### Selected Approach：在 `renderRssSecondaryTags` 增加「非标签样式即隐藏」守卫

根因：`upRssFlowJob()` 的 `collect` 数据回调（[RssFragment.kt L1219](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L1219)）无论处于哪种形态都会调用 `renderRssSecondaryTags(sorted)`；而该方法只要 `sources.isNotEmpty()` 就无条件 `binding.topBar.showTags(true)`（[RssFragment.kt L1238](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L1238)），覆盖了 `applyView()` 在文件夹模式已执行的 `showTags(false)`，于是 `tagsBarRequested=true`，regular 样式下 `filterToggleButton`（向下箭头）也随之出现。

修复方式：在 `renderRssSecondaryTags()` 入口加守卫 —— 若**非标签模式**（`!isTagMode`），则 `showTags(false)` 并直接返回，不填充 `tagsBar` 内容、不触发标签/箭头显示。

```kotlin
// D1: 刷新二级源标签（当前分组的源快捷标签，对齐书架 tagsBar）
// 修复 rss-folder-subtag-fix：二级源标签仅在标签样式(isTagMode)下展示；
// 文件夹样式点进文件夹后的列表视图不显示标签栏与右侧向下箭头。
private fun renderRssSecondaryTags(sources: List<RssSource>) {
    if (!isTagMode) {
        binding.topBar.showTags(false)
        return
    }
    // ……原有 tagsBar 填充逻辑不变……
}
```

理由：改动收敛在单方法入口，保持「标签样式显示 / 其他形态隐藏」的语义，与用户要求一致；不触碰 `applyView()` / 运行状态逻辑，回归面最小。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 在 `applyView()` 中彻底移除 `showTags(false)` 的保护 | 修改 `applyView()` 的 else 分支逻辑 | `applyView()` 当前实现是正确的（非标签模式已隐藏），问题在数据回调回补，故改 `applyView()` 治标不治本 |
| 在 `upRssFlowJob()` 调用处传 `isSubDirectory` 标志 | 由调用方决定是否渲染二级标签 | 需要在多处调用点传参，改动面大；`renderRssSecondaryTags` 自身就应持有「仅标签模式展示」这一不变量 |
| 全局封装 `setSecondaryTagVisible(boolean)` | 抽象一层显隐控制 | 过度设计，单点守卫已足够清晰 |

### Drawbacks

- **列表平铺（`sourceGroupStyle == 0`）形态下二级源标签将不再显示**：目前该形态也依赖 `renderRssSecondaryTags` 展示底部源标签，修复后统一为「仅标签样式展示」。这与用户「只有设置为标签才展示」的要求一致，属预期行为变化；如需平铺形态保留标签，可后续单独讨论。
- 若未来出现「文件夹点进后仍需二级过滤」的需求，需在此基础上扩展。

接受上述缺点，以换取行为与用户认知一致、代码不变量清晰、改动最小。

### Prior Art

- 书架/订阅标签体系统一：`docs/specs/tag-mode-unify/`（`MainTopBarView` 顶栏标签体系，`tagsBar` 二级多级过滤）。
- 本文件上一轮 D1/D2 设计与 `applyView()` 统一入口：`docs/specs/source-layout-detail-refinement/`。

## Requirements

### 功能需求（FR）

- **FR-1** 文件夹样式主页面：文件夹目录视图，头部无标签、无向下箭头（保持不变）。
- **FR-2** 文件夹样式点进文件夹后的子列表视图：头部不显示标签、不显示向下箭头。
- **FR-3** 标签样式（`sourceGroupMode == 0`）：二级源标签与向下箭头正常展示（保持不变）。

### 非功能需求（NFR）

- **N1** 改动收敛在 `renderRssSecondaryTags` 单方法，不触碰配置/数据/组件。
- **N2** 编译通过，无残留调试日志。
- **N3** 文件夹样式/标签样式两形态回归验证通过。

## Scenarios

### 正常场景

1. 用户把订阅布局设为「文件夹样式」→ 主页显示文件夹目录，头部无标签 → 点进某个文件夹 → 子列表显示，头部**无标签、无向下箭头**。✅
2. 用户把订阅布局改为「标签样式」→ primaryBar 分组胶囊 + tagsBar 二级源标签 + 向下箭头正常展示。✅

### 边界/异常场景

1. 「列表平铺」（`sourceGroupStyle == 0`）：二级源标签不再展示（预期行为变化，见 Drawbacks）。
2. 返回键回文件夹目录：`onFolderClick`→`isShowingFolder=true`→`applyView()` 文件夹分支仍隐藏标签（不变）。