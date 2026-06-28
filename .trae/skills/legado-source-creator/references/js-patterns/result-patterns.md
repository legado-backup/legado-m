# result 变量使用模式 + 控制流模式 + 变量赋值模式

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析

---

## 二、result 变量使用模式

| 模式 | 次数 | 说明 |
|------|------|------|
| result.match() | 4,223 | 正则匹配提取数据 |
| result = ... | 2,551 | 赋值重写result（跨字段传递） |
| result.replace() | 2,334 | 字符串替换/清洗 |
| result.split() | 264 | 分割字符串 |
| result[0] | 183 | 数组索引取值 |
| result.trim() | 139 | 去除首尾空白 |
| result.toArray() | 121 | 转为数组 |
| result.html | 120 | 获取HTML内容 |
| result.push() | 119 | 数组追加元素 |
| result.includes() | 113 | 字符串包含判断 |

### 核心模式：result 跨字段传递

```
# ruleBookInfo.init 中设置变量
@js:
var data = JSON.parse(result);
java.put('bookId', data.id);    // 缓存bookId
result;

# ruleToc.chapterList 中使用变量
@js:
var bookId = java.get('bookId'); // 取出bookId
var url = 'https://api.example.com/books/' + bookId + '/chapters';
var html = java.ajax(url);
JSON.parse(html).data;
```

---

## 三、控制流模式

| 模式 | 次数 | 说明 |
|------|------|------|
| if/else | 3,180 | 条件判断 |
| JSON.stringify | 1,768 | 对象转JSON字符串 |
| JSON.parse | 1,662 | JSON字符串转对象 |
| for循环 | 1,609 | 遍历数组/列表 |
| while循环 | 631 | 条件循环 |
| try/catch | 590 | 异常处理 |

---

## 四、变量赋值模式

| 变量 | 次数 | 典型用途 |
|------|------|----------|
| url = ... | 1,917 | 构造请求URL |
| list = ... | 1,137 | 构造列表数据 |
| src = ... | 559 | 图片/视频源地址 |
| html = ... | 259 | HTML内容 |
| body = ... | 213 | 请求体 |
| doc = ... | 46 | DOM文档对象 |
