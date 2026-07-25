# CMS 样本库

> 来源：GitHub 开源 CMS 仓库默认模板 HTML（脱敏处理）
> 用途：为 legado-source-creator 提供常见 CMS 模板结构参考，辅助书源规则编写

## 目录

| CMS 类型 | 目录 | 样本页面 | 选择器映射 |
|---------|------|---------|-----------|
| 苹果CMS V10 | maccms-v10/ | list / detail / search / play | selectors.json |
| 苹果CMS X10 | maccms-x10/ | list / detail / search / play | selectors.json |

## 苹果CMS V10 说明

苹果CMS V10（maccms10）是最广泛部署的影视站 CMS，其模板结构是书源编写的最常见目标。

### 模板来源

- GitHub 仓库：`magicblack/maccms10`
- 默认模板路径：`template/default/html/vod/`
- 获取日期：2026-06-14

### 关键特征

| 特征 | 说明 |
|------|------|
| 播放页变量 | `player_aaaa`（JSON 格式，含 url/name 字段） |
| 懒加载图片 | `data-original` 属性（非标准 `src`） |
| 列表容器 | `.stui-vodlist` / `.vodlist` / `.mac-catalog-show__grid` |
| 播放列表 | `.stui-content__playlist` / `.play_source_tab` + `.js-vod-play-source-body` |
| 分页 | `.stui-page` / `.mac-catalog-show__pager` |
| 分类URL | `/index.php/vod/type/id/{分类ID}.html` |

### 样本页面说明

| 文件 | 对应页面 | 关键选择器 |
|------|---------|-----------|
| list.html | 分类/列表页 | `.stui-vodlist li` / `.vodlist li` |
| detail.html | 详情页 | `.stui-content__playlist a` / `.play_source_tab` |
| search.html | 搜索页 | `.stui-vodlist li` / `.vodlist li` |
| play.html | 播放页 | `player_aaaa` JS变量 |

## 苹果CMS X10 说明

苹果CMS X10（maccms10-php8）是 V10 的 PHP8 升级版，模板全面重构，CSS 类名从 `stui-` 改为 `module-` 前缀。

### 模板来源

- GitHub 仓库：`magentron/maccms10-php8`
- 默认模板路径：`template/maccms10-php8/html/vod/`
- 获取日期：2026-06-14

### 关键特征

| 特征 | 说明 |
|------|------|
| 播放页变量 | `player_aaaa`（JSON 格式，含 url/name 字段，与 V10 一致） |
| 懒加载图片 | `data-src` 属性（V10 使用 `data-original`） |
| 列表容器 | `.module-items .module-item`（V10 使用 `.stui-vodlist li`） |
| 播放列表 | `.module-play-list a`（V10 使用 `.stui-content__playlist a`） |
| 分页 | `.module-page a.next`（V10 使用 `.stui-page a.next`） |
| 备注标记 | `.module-item-note`（V10 使用 `.pic-text`） |
| 分类URL | `/vodtype/{id}.html`（V10 使用 `/index.php/vod/type/id/{id}.html`） |
| 详情URL | `/voddetail/{id}.html`（V10 使用 `/vod/detail/id/{id}.html`） |
| 播放URL | `/vodplay/{id}-{sid}-{nid}.html`（V10 使用 `/vod/play/id/{id}/sid/{sid}/nid/{nid}.html`） |

### V10 → X10 核心差异速查

| V10 选择器 | X10 选择器 |
|-----------|-----------|
| `.stui-vodlist li` | `.module-items .module-item` |
| `.stui-page a.next` | `.module-page a.next` |
| `.stui-content__playlist a` | `.module-play-list a` |
| `.pic-text` | `.module-item-note` |
| `data-original` | `data-src` |
| `/index.php/vod/type/id/` | `/vodtype/` |

### 样本页面说明

| 文件 | 对应页面 | 关键选择器 |
|------|---------|-----------|
| list.html | 分类/列表页 | `.module-items .module-item` / `.module-item-note` |
| detail.html | 详情页 | `.module-play-list a` / `.module-tab-item` |
| search.html | 搜索页 | `.module-items .module-item` / `.module-page a.next` |
| play.html | 播放页 | `player_aaaa` JS变量 / `.module-player-nav-item` |

## 使用方式

1. 编写书源时，先对照 `selectors.json` 中的选择器映射
2. 用样本 HTML 验证选择器是否匹配
3. 注意 `fallbacks` 字段提供了常见变体选择器
4. 实际站点可能使用自定义模板，选择器会有差异
