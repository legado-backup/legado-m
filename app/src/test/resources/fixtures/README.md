# 单测夹具（fixtures）目录与命名约定

> 归属：epub-md-rich-rendering 补充任务 **S13**（`docs/specs/epub-md-rich-rendering/tasks.md`）。

## 目录

```
app/src/test/resources/fixtures/
├── md/        # Markdown 章节样本（喂给 MdDocumentBuilder / MdChapterizer）
├── epub/      # XHTML / OPF 片段样本（喂给 epubcore 解析器）
└── template/  # 阅读页模板 JSON（喂给 ReaderTemplatePackage / ImportMapper）
```

## 命名

- 一律**小写 + 连字符**，语义前置：`basic.md`、`spine-fragment.xhtml`、`minimal.json`。
- 变体用后缀区分：`<base>-<variant>.<ext>`（如 `basic-nested-list.md`）。
- **禁止**用时间戳 / 随机数命名（夹具必须可被多用例复用且可 diff）。

## 承载格式

- 文本类（md / json / xhtml / css / js）**直接入库**。
- 二进制（真 EPUB zip / 图片）**不入库**：在用例内用 `ZipOutputStream` / 最小字节构造（`ReaderTemplateImportMapperTest`
  的 ZIP 用例即此口径），避免仓库膨胀与二进制 diff 噪音。

## 已被消费的夹具（防"建了没人用"）

| 夹具 | 消费用例 |
|---|---|
| `md/basic.md` | `testkit.FixturesConventionTest`（经 `MdDocumentBuilder` 真实解析，断言 GFM 表格等结构） |
| `template/minimal.json` | `testkit.FixturesConventionTest`（断言模板最小结构键 + `data-reader-flow="body"` 契约） |
| `epub/spine-fragment.xhtml` | `testkit.FixturesConventionTest`（非空 + 可解析为 XHTML 片段） |

## 加载方式（单测内）

```kotlin
val text = javaClass.classLoader!!.getResource("fixtures/md/basic.md")!!.readText()
```

> 需要"读**主源码/资产**"时不要用本目录，改用 `testkit.SourceFileProbe`（它对工作目录做了三候选回退）。