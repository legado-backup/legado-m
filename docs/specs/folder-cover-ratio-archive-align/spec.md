# 文件夹封面比例对齐 Archive — spec

## Intent
解决书架/发现页文件夹模式下，自定义文件夹封面（多为方形/横版图）被强制塞入过瘦高的竖版容器后视觉失真（图片被竖向放大裁剪、观感"被拉长"）的问题。通过与阅读Archive/原版的文件夹封面宽高比保持一致（4:3），让文件夹风格宽高协调、图片呈现自然。

## Scope
**In-Scope：**
- 书架页文件夹网格封面比例 0.7 → 0.75（`BookshelfScreen.kt` 的 `FolderGroupGridContent`）
- 发现页文件夹网格封面比例 0.7 → 0.75（`SourceFolderComposeGrid.kt`）
- View 版文件夹卡片封面比例 0.7 → 0.75（`item_source_folder_grid.xml`）
- 文档同步（INDEX / project-flow）

**Out-of-Scope：**
- 不改书籍封面比例（`BookGrid`/列表书籍封面仍保持 0.7，书形封面本身协调）
- 不改变封面加载方式/ScaleType（仍保持 centerCrop 裁剪语义）
- 不改文件夹图标(FolderOpen)样式
- 不做"按图片原始比例自适应高度"的大改造

## Approach
### Selected Approach
将三处文件夹封面容器的目标宽高比从 `0.7f` 统一改为 `0.75f`，与阅读Archive 的 `CoverImageView.onMeasure` 固定高宽比 **width × 4/3（即 W/H = 0.75）** 保持一致。改动极小、风险低、可逐点核验。

理由：
- Archive/原版作为用户认可的基线，其文件夹封面比例即为 0.75，直接对齐即可满足"不拉长/协调"诉求。
- 仅改容器比例参数，不触碰加载链路与裁剪逻辑，回归面小。

### Alternatives Considered
| 方案 | 说明 | 否决理由 |
|------|------|----------|
| 改使用 FIT_CENTER（整图显示） | 任意宽高完整显示、绝不裁剪 | 与 Archive 行为不一致（Archive 也是 centerCrop + 固定比例），且会引入留白、观感改变过大；用户明确要求"对齐 Archive 比例" |
| 改为尺寸自适应（按图原始比例定高） | CoverImageView 之外再引入自定义测量 | 大改，引入不确定布局抖动，超出本次诉求 |
| 保持 0.7 不改 | — | 不满足用户诉求 |

### Drawbacks
- 0.7 → 0.75 仅缓和"拉长感"，对于极端超宽（如 16:9）横图，centerCrop 仍会裁剪两侧。这是 Archive 相同的固有行为，接受。

### Prior Art
- 阅读Archive（Rimchars/legado）`CoverImageView.onMeasure`：`measuredHeight = measuredWidth * 4 / 3`。
- 阅读R/原版 `item_bookshelf_grid_group.xml` 用 `CoverImageView`（宽 match_parent，高由 onMeasure 强制 4/3）。

## Requirements
- REQ-1（书架）：书架文件夹网格封面容器宽高比取 0.75（W/H）。
- REQ-2（发现页）：发现页文件夹网格封面容器宽高比取 0.75（W/H）。
- REQ-3（View版）：View 版文件夹卡片封面 `layout_constraintDimensionRatio` 改为 `0.75`。
- REQ-4：不改动书籍封面 0.7、不改加载方式与 ScaleType。
- REQ-5：编译通过，书架/发现页文件夹封面呈现协调。

## Scenarios
- S1：方形封面。书架文件夹网格中，方形图以 0.75 容器 centerCrop 显示，拉长感显著缓解。
- S2：横版封面。发现页文件夹网格中，横版图按 0.75 容器裁剪，与 Archive 观感一致。
- S3：无封面（默认 FolderOpen 图标）。仅显示图标，不受比例影响，变化前/后一致。
- S4：回归。书籍封面网格仍为 0.7，未被误改。