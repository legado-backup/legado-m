# 已知修复模式索引

> 共 8 种修复模式，基于真实书源/订阅源修复经验沉淀。按问题特征定位模式，直接复用代码片段。

## 模式速查表

| 模式 | 适用场景 | 修复源示例 | 文档 |
|------|---------|-----------|------|
| JS补全绝对路径 | Web Components自定义元素href返回相对路径 | 奇书塔/中国古典/衍墨轩 | [js-absolute-path.md](./js-absolute-path.md) |
| og:novel meta+@put/@get | 详情页选择器失效，页面使用og:novel meta标签 | 奇书塔/衍墨轩 | [og-novel-meta.md](./og-novel-meta.md) |
| nextContentUrl分页 | 正文分页（多页正文） | PO18/衍墨轩 | [next-content-url.md](./next-content-url.md) |
| replaceRegex净化 | 去广告/章节标题重复/水印文字 | 奇书塔/PO18 | [replace-regex.md](./replace-regex.md) |
| 搜索方法转换 | GET搜索返回空，需改为POST或调整URL | PO18 | [search-method.md](./search-method.md) |
| GBK编码 | GBK编码网站的搜索关键词 | PO18 | [gbk-encoding.md](./gbk-encoding.md) |
| 排行榜URL失效 | 网站改版导致排行榜URL变化 | 放屁音乐 | [ranking-url.md](./ranking-url.md) |
| 音频解析 | 音频订阅源（音乐/有声书） | 放屁音乐 | [audio-parse.md](./audio-parse.md) |

## 使用方式

1. 根据问题特征（相对路径/分页/编码等）定位模式
2. 查阅对应文档的代码片段
3. 注意事项中标注的陷阱，避免重复踩坑
