# Spec：rss-folder-cover-dialog-align（订阅文件夹封面弹框对齐书架）

## Intent

经典订阅文件夹视图的封面替换交互，当前是"长按 → HandleFileActivity 通用操作列表 → 选完直接落库"的最简链路：无预览、无标准弹框、无恢复默认入口（Compose 版）、URL 语义与书架分歧。目标是对齐书架侧 `GroupEditDialog` 的封面编辑能力与视觉体系：长按即弹标准 Compose 表单弹框，含封面预览、选图（http 直存）、恢复默认、确定/取消编辑态语义。

## Scope

### In Scope

1. 新建 `RssFolderCoverDialog`（ComposeDialogFragment），容器/取色/按钮全部走 ui-standards 标准体系（AppDialogFrame / rememberAppDialogStyle / LegadoMiuixActionButton）
2. 长按文件夹（SourceFolderComposeGrid onFolderLongClick）改为直接打开该弹框（对齐书架交互）
3. 封面预览区：BookCoverImage 回显当前封面，选图后实时更新
4. 选图：复用 HandleFileContract（IMAGE 模式）；http/https 直存 URL 字符串（对齐书架 GroupEditDialog 语义）；本地文件 readUri → MD5 命名复制到 externalFiles/covers/
5. 恢复默认：预览置空 + 确定时删除 source_group_covers 记录（KIND_RSS）
6. 编辑态语义：封面变更仅暂存 state，点确定才 upsert/delete 并同步 folderComposeCovers；取消/dismiss 不落库
7. 特殊文件夹（全部分组/未分组/类型）同样支持（沿用 groupKey 机制）

### Out of Scope

1. 分组名/排序/刷新开关等编辑能力（书架 GroupEditDialog 含这些是因为它同时承担分组编辑；订阅分组是字符串标签无实体，无对应字段可编辑）
2. 存储模型迁移（订阅侧保持 source_group_covers 表，不改为实体字段）
3. 书架侧"清除封面 UI 未绑定"问题的修复（已在 ui-style-unify 范畴，另行处理）
4. 图片裁剪/压缩能力（两侧现状均无，不新增）
5. 新版订阅模式的封面交互

## Approach

### Selected Approach

新建独立的 `RssFolderCoverDialog : ComposeDialogFragment()`，UI 骨架克隆书架 `GroupEditDialog` 的标准体系（ComposeDialogFragment 基类 + AppDialogSize.Form + AppDialogFrame + rememberAppDialogStyle + BookCoverImage 预览 + LegadoMiuixActionButton 操作区），但内容收敛为封面编辑四要素：预览区 / 选图入口 / 恢复默认 / 确定取消。数据层沿用 source_group_covers 表（KIND_RSS + groupKey），保存链路复用 RssFragment 既有的 readUri→MD5 复制→upsert→folderComposeCovers 同步逻辑，将"选图回调直接落库"改为"暂存 state、确定落库"。

理由：
- 书架弹框 UI 已是项目标准体系最佳实践，克隆骨架成本最低且视觉天然一致
- 两侧存储模型不同（实体字段 vs 独立表），强行统一存储反而扩大改动面（违反精准修改原则）
- 长按交互对齐书架"即弹框"，消除"菜单→列表→再选"的两层跳转

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| A1：直接复用 GroupEditDialog（传入订阅分组伪实体） | GroupEditDialog 强耦合 BookGroup 实体与 GroupViewModel（分组名/排序/删除分组），订阅分组无实体无这些语义；传入伪实体会引入大量禁用分支，修改公共弹框风险波及书架 |
| A2：保留 HandleFileActivity 链路，仅加预览 | HandleFileActivity 是通用文件操作 Activity，无法承载"编辑态暂存+确定落库"语义；且列表弹框样式与标准表单体系割裂，正是本次要消除的体验差距 |
| A3：统一存储到 BookGroup 式字段 | 需要给订阅分组建实体/加字段（涉及 DB 迁移），改动面大且订阅分组本质是字符串标签，为封面引入实体违反极简原则 |
| A4：在 SourceFolderComposeGrid 内嵌封面管理面板（非弹框） | 偏离书架交互模型（弹框），且网格内嵌编辑面板状态管理复杂 |

### Drawbacks

| 缺点 | 接受理由 |
|------|---------|
| 新增一个弹框类（与 GroupEditDialog 存在骨架相似代码） | 两侧数据语义不同，抽公共组件反而制造过早抽象；骨架相似度集中在容器层（本就是标准组件），业务层各自独立 |
| http URL 直存后，断网/失效 URL 显示空白封面（书架现状同样如此） | 对齐书架语义优先；BookCover.load 已有失败兜底（回退图标），可接受 |
| 恢复默认需点确定才生效（书架编辑态同款） | 与书架一致；比现状"菜单里立即删除"多一步，但换来统一的编辑态心智 |

### Prior Art

- 书架 GroupEditDialog（本项目）——本次对齐标杆
- SourceFolderConfigDialog（本项目）——订阅侧标准 Compose 弹框先例（AppDialogFrame + onValuesChange 编辑态 + 取消还原），验证了该模式在订阅侧可行

## Requirements

### R1 弹框入口

- R1.1 长按经典订阅文件夹视图任意文件夹卡片，直接打开 RssFolderCoverDialog
- R1.2 弹框展示所按文件夹的名称（标题）与当前封面预览

### R2 封面预览

- R2.1 预览区使用 BookCoverImage（DETAIL 样式，尺寸对齐书架 90×120dp）
- R2.2 无封面时显示 FolderOpen 图标占位（对齐 SourceFolderCover 现有兜底）
- R2.3 选图返回或恢复默认后，预览实时更新

### R3 选图

- R3.1 "选择图片"入口走 HandleFileContract（IMAGE 模式），行为与书架 GroupEditDialog.selectImage 一致
- R3.2 http/https 结果直接作为封面字符串暂存（对齐书架直存语义）
- R3.3 本地文件 readUri → MD5 命名复制到 externalFiles/covers/，暂存本地路径

### R4 恢复默认

- R4.1 提供"恢复默认"操作，点击后预览回退占位图标
- R4.2 该文件夹原本无封面时，恢复默认不可见或点击无副作用（防误触）

### R5 保存与取消

- R5.1 确定时有新封面 → upsert(KIND_RSS, groupKey, path)；封面被恢复默认且原有记录 → delete(KIND_RSS, groupKey)
- R5.2 落库后同步更新 folderComposeCovers state，文件夹网格即时重组
- R5.3 取消/系统返回/dismiss 不产生任何落库
- R5.4 编辑中途重复进入弹框，预览始终从数据库当前值起步（不受上次未保存操作影响）

### R6 样式与主题

- R6.1 弹框走 ComposeDialogFragment + AppDialogFrame + rememberAppDialogStyle，随主题/日夜模式/E-Ink 联动
- R6.2 窗口规格 AppDialogSize.Form、居中、中心动画（对齐 GroupEditDialog 窗口配置）

## Scenarios

### S1 正常替换封面

1. 经典订阅 → 文件夹视图 → 长按某文件夹
2. 弹出封面弹框，预览显示当前封面（或占位图标）
3. 点"选择图片" → HandleFileActivity → 系统相册选图
4. 返回弹框，预览实时更新为所选图
5. 点"确定" → 弹框关闭，文件夹网格该卡片封面立即更新

### S2 手动输入网络图片

1. 长按文件夹 → 选择图片 → HandleFileActivity 操作列表选"输入图片链接"
2. 输入 http(s) 链接返回
3. 预览尝试加载该 URL；确定后封面值直接为该 URL（不下载复制）

### S3 恢复默认

1. 长按已有自定义封面的文件夹 → 预览显示当前封面
2. 点"恢复默认" → 预览回退占位图标
3. 点"确定" → 网格卡片回退 FolderOpen 占位图标，数据库记录删除

### S4 取消不落库

1. 长按文件夹 → 选图（预览已变）→ 点"取消"或按返回
2. 弹框关闭，网格封面保持原样，数据库无变化
3. 再次长按进入，预览从数据库当前值起步

### S5 特殊文件夹

1. 长按"全部分组"/"未分组"/类型文件夹
2. 弹框正常工作，封面按 groupKey 写入 source_group_covers（沿用既有特殊 key 约定）

### S6 主题联动

1. 深色模式 / 自定义主题 / E-Ink 模式下打开弹框
2. 容器底色、描边、圆角、按钮配色、字体均随主题，无硬编码色
