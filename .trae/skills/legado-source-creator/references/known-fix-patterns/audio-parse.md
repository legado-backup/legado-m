# 音频解析模式

## 适用场景
音频订阅源（音乐/有声书），需从页面中提取音频 URL 并配置播放。

## 修复源示例
- 放屁音乐

## 代码片段
```json
{
  "ruleArticles": {
    "title": "class.song-title@text",
    "image": "class.cover@tag.img@src",
    "url": "class.play-btn@data-url"
  },
  "ruleContent": {
    "content": "<js>\nvar audioUrl = java.ajax(result);\naudioUrl;\n</js>"
  }
}
```

## 注意事项
- 音频 URL 可能是加密的，需 JS 解密后才能播放
- 部分音频源返回的是 JSON 接口数据，需用 JSONPath 提取 url 字段
- 音频文件可能是 m4a/mp3/ogg 格式，Legado 支持自动识别
- 若音频 URL 有时效性（带 token/expire），需在 JS 中实时请求获取
- 有声书多为分集形式，配合 nextContentUrl 实现连续播放
