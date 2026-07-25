# 目录高级技巧

> 目录规则（TocRule）的高级写法，涵盖排序、与详情页合一处理、多页目录等场景。
> 所有内容已通过 Legado 源码确认。

---

## 1. 目录排序三种方法

部分网站的目录章节顺序混乱（如倒序或乱序），需要通过 JS 重新排序。

### 方法一：文本数字排序

```javascript
var list = JSON.parse(result);
list.sort(function(a, b) {
    return parseInt(a.text.match(/\d+/)[0]) - parseInt(b.text.match(/\d+/)[0]);
});
result = JSON.stringify(list);
```

**原理**：
- 从章节标题中提取数字（如"第12章"中的 12）
- 按数字大小升序排列
- `text` 是章节标题字段

**适用场景**：章节标题含数字序号但 HTML 顺序混乱。

### 方法二：属性 ID 排序

```javascript
var list = JSON.parse(result);
list.sort(function(a, b) {
    return parseInt(a.id) - parseInt(b.id);
});
result = JSON.stringify(list);
```

**原理**：
- 利用 HTML 元素的 `id` 属性作为排序依据
- `id` 通常按章节顺序递增

**适用场景**：章节元素有递增的 id 属性。

### 方法三：data-id 属性排序

```javascript
var list = JSON.parse(result);
list.sort(function(a, b) {
    return parseInt(a['data-id']) - parseInt(b['data-id']);
});
result = JSON.stringify(list);
```

**原理**：
- 利用自定义 `data-id` 属性排序
- 部分网站使用 `data-id` 而非 `id` 存储章节序号

**适用场景**：章节元素使用 data-id 自定义属性。

---

## 2. 目录与详情页合一处理

部分网站没有独立的目录页，目录信息就在详情页中。

### 章节 URL 填 `{{baseUrl}}`

```json
{
  "ruleTocUrl": "{{baseUrl}}"
}
```

- `{{baseUrl}}` 表示使用当前详情页 URL 作为目录页 URL
- Legado 会用详情页的 URL 重新加载页面并按目录规则解析

### 不填目录链接

当目录就在详情页时，可以不填 `ruleTocUrl`，直接在目录规则中解析详情页内容：

```
tag.html
```

或

```
tag.body
```

- `tag.html` 获取整个页面的 HTML
- `tag.body` 获取 body 标签内容
- Legado 会自动用当前页面作为目录数据源

**适用场景**：单页应用、目录和详情在同一页面、无独立目录 URL。

---

## 3. 目录下一页高级写法

部分网站目录分多页显示，需要获取所有页的章节。

### 隐藏标签获取页码

```
option@value
```

- 部分网站用 `<select>` 下拉框切换目录页
- `option@value` 提取所有 `<option>` 的 value 属性（即各页 URL 或页码）
- Legado 会自动遍历所有 value 加载分页

### 并发加载多页

```
[name=pageselect] > option!0@value
```

- `!0` 表示排除第一个 option（通常是"请选择"占位项）
- Legado 会并发加载所有提取到的分页 URL
- 比串行加载快得多

### JS 生成多页 URL

```javascript
var baseUrl = result.match(/(.*)\/\d+\.html/)[1];
var pages = [];
for (var i = 1; i <= 10; i++) {
    pages.push(baseUrl + '/' + i + '.html');
}
result = pages.join('\n');
```

**原理**：
- 从第一页 URL 中提取基础路径
- 生成所有分页 URL
- 每行一个 URL，Legado 会逐页加载

**适用场景**：目录超过一页、分页 URL 有规律、需要获取全部章节。
