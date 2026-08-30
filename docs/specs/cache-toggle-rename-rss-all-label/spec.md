# spec.md - 文案调整：视频缓存开关改名 + 订阅「全部」分组标签缩短

## Intent

- 用户反馈 1：内置视频播放器设置中的「边下边播」开关本质上只是播放缓存策略（ExoPlayer SimpleCache 开关），且播放器已新增独立的「下载」按钮，名称易误导用户以为与下载功能重复。需改名为准确表达"播放时缓存"的文案。
- 用户反馈 2：订阅源的「全部分组」名称四个字太长，希望缩短为「全部」。

## Scope

### 做什么

- 修改 `cache_play` 字符串文案：「边下边播」→「播放时缓存」（默认 strings.xml，仅中文定义）
- 修改 `all_groups` 字符串文案（4 个语言文件）：
  - `values-zh/strings.xml`：「全部分组」→「全部」
  - `values-zh-rHK/strings.xml`：「全部分組」→「全部」
  - `values-zh-rTW/strings.xml`：「全部分組」→「全部」
  - `values/strings.xml`（默认/英文）：`All groups` → `All`
- 更新 `updateLog.md`（面向用户说明两处文案变更）

### 不做什么

- 不改任何逻辑代码（VideoPlay.videoCache、ExoPlayerHelper.cacheDataSourceFactory、RssFragment、SourceFolderAdapter 等均零变更）
- 不改「查看全部分组」（`highlight_rule_group_view_all`，高亮规则功能，语义不同）
- 不改书源搜索页硬编码文案「是否切换到全部分组？」（SearchActivity/ChangeBookSourceDialog 等，属书源换源/搜索功能，非本次反馈范围）
- 不改 `SourceFolderAdapter` 中 `R.string.all_groups → KEY_ALL_GROUPS` 的封面 key 映射（按资源 ID 比对，文案变更天然不影响）

## Approach

### Selected Approach

直接修改字符串资源值，资源名（`cache_play`/`all_groups`）保持不变。

理由：
- 两处字符串引用点少（`cache_play` 仅 `VideoSettingsPanelContent.kt` 一处；`all_groups` 仅 RssFragment 5 处 + SourceFolderAdapter 1 处按 ID 比对），改值不改名即可全局生效，零代码变更、零回归风险。
- 资源名改名（如 `cache_play` → `video_cache`）无任何收益，反而增加 diff 与出错面。

### Alternatives Considered

| 替代方案 | 否决理由 |
|---------|---------|
| 资源名一并改名（`all_groups` → `all`） | 无收益；`all_groups` 与封面 key `KEY_ALL_GROUPS` 语义绑定清晰，改名徒增 diff |
| 「边下边播」改名为「视频缓存」 | 与设置中"清理缓存"等概念仍可能混淆；「播放时缓存」更精确表达"播放过程中的缓存策略" |
| 「边下边播」改名+加副标题说明 | 面板空间有限，一个勾选项加副标题过度设计 |
| 订阅页在代码层硬编码「全部」而保留资源值 | 违反文案走 strings.xml 的项目规范（i18n 破损审计 C-02 教训），且 explore 等页面复用风险 |

### Drawbacks

- 老用户已习惯「边下边播」旧名称，升级后需重新认知。缓解：updateLog.md 明确说明"原『边下边播』更名为『播放时缓存』"。
- 「全部」与未来可能出现的用户自建分组重名可能性极低（分组名由用户输入，系统不拦截"全部"，但订阅页该位置是特殊文件夹固定标签，不与用户分组列表混排显示歧义）。
- 默认 `values/strings.xml` 的 `cache_play` 本身是中文直写（i18n 历史问题 C-02），本次不修复英文缺失，保持最小变更。

### Prior Art

- 主流视频 App（B 站等）设置中类似开关命名为「播放时缓存」/「缓存设置」，无「边下边播」字样。
- 原版 Legado 书源页分组标签使用简短文案习惯。

## Requirements

| ID | 需求 | 说明 |
|----|------|------|
| R1 | 视频设置面板缓存开关文案改为「播放时缓存」 | `cache_play` 字符串值变更，UI 唯一引用点 `VideoSettingsPanelContent.kt` 自动生效 |
| R2 | 订阅页「全部分组」标签显示为「全部」 | `all_groups` 4 个语言文件值变更；覆盖：标签栏胶囊、文件夹视图头部、类型文件夹视图入口 |
| R3 | 订阅文件夹封面功能不受影响 | `SourceFolderAdapter` 按 `R.string.all_groups` 资源 ID 映射 `KEY_ALL_GROUPS`，改文案后长按封面/换封面仍正常 |
| R4 | updateLog.md 记录两处文案变更 | 追加在 `## cronet版本:` 之后、已有条目之前 |

## Scenarios

### S1: 视频设置面板查看改名后的开关

> 用户打开内置视频播放器 → 设置面板，勾选项显示「播放时缓存」而非「边下边播」，勾选状态与原 `videoCache` 配置一致，开关行为不变。

### S2: 订阅页标签栏显示「全部」

> 用户进入订阅页（新版/经典形态），标签栏第一个胶囊显示「全部」；点击后显示全部订阅源，行为不变。

### S3: 订阅文件夹视图显示「全部」

> 用户在订阅页文件夹视图下，特殊文件夹「全部」正常显示；长按可换封面、封面正常加载（key 仍为 `KEY_ALL_GROUPS`）；点击进入显示全部订阅源。

### S4: 语言切换

> 系统语言繁中/英文环境下，订阅页对应显示「全部」/ `All`，无遗漏语言变体。
