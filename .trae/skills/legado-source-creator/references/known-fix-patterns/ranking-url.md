# 排行榜URL失效模式

## 适用场景
网站改版导致排行榜（sortUrl）URL 路径变化，原有配置失效返回 404 或空列表。

## 修复源示例
- 放屁音乐

## 代码片段
```json
{
  "sortUrl": "热歌榜,https://www.fangpi.com/rank/hot\n新歌榜,https://www.fangpi.com/rank/new\n原创榜,https://www.fangpi.com/rank/original"
}
```

## 注意事项
- 音乐网站排行榜可能是热词榜单而非歌曲榜单，需确认页面内容类型
- 网站改版后旧 URL 可能重定向到首页而非 404，需检查实际返回内容
- 排行榜 URL 更新后，对应的 ruleArticles 选择器也可能需要同步调整
- 建议在 sourceComment 中记录更新日期，便于后续维护
