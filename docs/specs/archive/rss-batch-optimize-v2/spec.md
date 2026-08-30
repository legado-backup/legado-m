# spec.md - RSS 订阅源批量优化 v2（222源）

## Intent

用户提供了 222 个 RSS 订阅源 JSON 文件，要求"尽可能完善所有订阅源，尤其是必填字段一定要有，有些订阅源如果有问题，尽可能去修复优化，如果实在优化修复不了，看看注释信息，去查找最新的域名，整个过程反哺skill"。

本任务在 v1（65源批量优化）基础上扩展，处理 222 个源（规模 3.4 倍），复用 v1 的工作流与陷阱库，同时识别和处理 v1 未遇到的新场景。

## Scope

### 做什么

1. **类型识别与分类**：识别每个源的类型（type=0网页/1图片/2视频），根据源内容自动设置正确type
2. **批量字段补全**：用 Playwright 访问每个源首页，提取并补全字段
   - 必填：sourceIcon、searchUrl、ruleArticles、ruleTitle、ruleLink、ruleImage
   - 推荐：sortUrl、ruleNextPage、rulePubDate、ruleContent
3. **导航站深度拆分**：对导航类源站（含多个子站链接），分析子站类型，将图片站/视频站拆分为独立订阅源
4. **失败源深度重试**：对访问失败的源用 14 种技术手段穷尽优化
5. **域名迁移**：对原URL返回小HTML含"备用域名/最新域名获取地址"的源，按5步闭环迁移
6. **反爬源配置**：对反爬源配置 loginUrl + enabledCookieJar，让用户在App内WebView登录获取Cookie
7. **占位符源处理**：对 sourceUrl 长度<20 的占位符源（68个）进行特殊处理（标记或从sourceComment提取真实URL）
8. **模板源处理**：对含 `{{}}` 的模板URL源（7个）从模板提取base_url再访问
9. **图片源JS规则设计**：为图片源（type=1）设计ruleContent JS规则，适配开源阅读的PhotoDialog显示
10. **视频源自动设置**：视频源自动设置 type=2 + ruleContent（嗅探或JS提取视频URL）
11. **JSON 类型修复**：boolean字段必须为 true/false（陷阱15）
12. **导入模拟器验证**：导入到MEmu模拟器，运行4场景验证（列表/搜索/分类/下一页）
13. **skill 反哺**：将本次发现的新陷阱反哺到 legado-source-creator skill 文档

### 不做什么

1. 不修改项目源代码（RssSource.kt 等）
2. 不修改校验器代码（mandatory_fields.py）
3. 不做真机用户登录验证（仅模拟器验证配置正确性）
4. 不做 skill 的结构性重构（只反哺陷阱文档）

## Approach

### Selected Approach：复用 v1 工作流 + 分阶段处理

**9阶段流水线**（基于 v1 5步闭环扩展，新增类型识别/导航站拆分/ruleContent设计）：

```
阶段1: 结构分析（已完成）→ 222源，主要缺失字段统计
阶段2: 预处理（占位符源+模板源特殊处理）
阶段3: 类型识别与分类（DOM特征分析，识别图片/视频/导航/网页源）← 新增
阶段4: 导航站拆分（从导航站提取子站，拆分为独立图片源/视频源）← 新增
阶段5: Playwright批量字段补全（11字段：6必填+5推荐）
阶段6: 字段合法性后置校验（修复无效值，必填字段缺失兜底）
阶段7: 失败源深度重试（14种技术手段）+ 域名迁移（5步闭环）+ 反爬源loginUrl配置
阶段8: 图片源/视频源ruleContent设计（适配PhotoDialog/VideoPlayerActivity调用链）← 新增
阶段9: JSON类型修复（boolean 1/0 → true/false）+ 导入验证 + skill反哺
```

### Alternatives Considered

| 方案 | 描述 | 优点 | 缺点 | 是否选择 |
|------|------|------|------|---------|
| A. 复用v1工作流 | 8阶段流水线 | 经验成熟，已验证 | 处理时间长（222源×20秒=74分钟） | ✅ 选择 |
| B. 并行化处理 | 多线程Playwright | 速度快3-5倍 | 站点反爬可能更严重，调试复杂 | ❌ 否决（稳定性优先） |
| C. 只补全必填字段 | 仅处理MANDATORY缺失字段 | 处理量少，速度快 | 用户要求"尽可能完善所有字段" | ❌ 否决（不符合需求） |
| D. 人工逐个处理 | 用户手动优化 | 质量高 | 222源人工不可行 | ❌ 否决（不可行） |
| E. 直接用AI生成 | 不访问站点，AI根据sourceUrl推测字段 | 速度快 | 准确率低，可能编造字段 | ❌ 否决（不可靠） |

### Drawbacks

1. **处理时间长**：222源×20秒=约74分钟（Playwright访问），加上失败重试和域名迁移，总时间可能2-3小时
2. **Playwright访问可能失败**：部分源可能CF防护/超时/失效，需要14种技术手段重试
3. **域名迁移不一定成功**：即使找到"最新域名获取地址"，获取的新域名也可能已失效
4. **反爬源loginUrl无效场景**：模拟器DNS问题（陷阱14）会导致loginUrl也无效，只能保留配置标记用户可选

### Prior Art

- v1 批量优化（65源）：24/65 Playwright成功，14种技术手段穷尽优化，最终8个truly_dead
- 域名迁移5步闭环（陷阱8）：idx=60成功案例
- 反爬源loginUrl配置（陷阱13）：7个源配置loginUrl

## Requirements

### 功能需求

| REQ-ID | 需求 | 优先级 | 验收标准 |
|--------|------|--------|---------|
| REQ-1 | 类型识别 | P0 | 每个源有正确的type（0/1/2） |
| REQ-2 | sourceIcon 必填 | P0 | 100% 源有 sourceIcon |
| REQ-3 | searchUrl 必填 | P0 | 100% 源有 searchUrl |
| REQ-4 | ruleImage 必填 | P0 | 100% 源有 ruleImage（列表有图片） |
| REQ-5 | ruleArticles 必填 | P0 | 100% 源有 ruleArticles |
| REQ-6 | ruleTitle 必填 | P0 | 100% 源有 ruleTitle |
| REQ-7 | ruleLink 必填 | P0 | 100% 源有 ruleLink |
| REQ-8 | 失败源深度重试 | P0 | 穷尽14种技术手段后剩余失败源数 |
| REQ-9 | 域名迁移 | P1 | 对含"备用域名"提示的源迁移成功 |
| REQ-10 | 反爬源loginUrl配置 | P1 | 反爬源配置loginUrl+enabledCookieJar |
| REQ-11 | 占位符源处理 | P1 | 68个占位符源标记或提取真实URL |
| REQ-12 | 模板源处理 | P2 | 7个模板源提取base_url |
| REQ-13 | 导航站拆分 | P1 | 导航类源拆分为独立图片源/视频源 |
| REQ-14 | 图片源ruleContent JS | P0 | type=1源有适配PhotoDialog的ruleContent |
| REQ-15 | 视频源ruleContent | P0 | type=2源有嗅探或JS提取视频URL的ruleContent |
| REQ-16 | JSON类型修复 | P0 | boolean字段为true/false |
| REQ-17 | 导入模拟器验证 | P0 | 4场景验证通过率 |
| REQ-18 | skill反哺 | P1 | 新陷阱文档化到batch-optimization-patterns.md |

### 非功能需求

| NFR-ID | 需求 | 验收标准 |
|--------|------|---------|
| NFR-1 | 输出安全 | 不输出业务字段原文（sourceName/sourceUrl等） |
| NFR-2 | 脱敏 | 脚本输出用编号源[N]替代真实名称 |
| NFR-3 | 健壮性 | 单源失败不中断整体流程 |
| NFR-4 | 可恢复 | 失败源记录到报告，可单独重试 |

## Scenarios

### 场景1：正常源处理

**输入**：sourceUrl 是http开头，站点可达，字段部分缺失
**处理**：Playwright访问 → 提取4字段 → 后置校验 → 补全
**输出**：源4字段完整，enabled=true

### 场景2：占位符源处理

**输入**：sourceUrl 长度<20（如"91香蕉国产"），非真实URL
**处理**：标记为placeholder_source，从sourceComment提取真实URL（如果有），否则标记needs_manual
**输出**：源标记分类，不能访问的源明确告知用户

### 场景3：模板源处理

**输入**：sourceUrl 含 `{{}}`（如 `https://997767.xyz/{{page==1?'':'page/'+page+'/'}}`）
**处理**：用正则去除模板部分，提取base_url（`https://997767.xyz/`），访问base_url提取字段
**输出**：源4字段完整，ruleNextPage保留模板

### 场景4：失效源域名迁移

**输入**：sourceUrl 访问返回小HTML（约130字节），内容含"备用域名：xxx"和"最新域名获取地址：URL"
**处理**：5步闭环迁移 → 访问原URL提取候选域名 → 访问"获取地址" → 去重去CDN → 测试可达性 → 用新域名替换sourceUrl
**输出**：sourceUrl替换为新域名，4字段重新提取

### 场景5：反爬源处理

**输入**：sourceUrl 访问返回HTTP 403或17字节"Request Forbidden"
**处理**：配置 loginUrl=sourceUrl + enabledCookieJar=true，标记user_optional_login
**输出**：用户可在App内WebView登录获取Cookie

### 场景6：truly_dead源处理

**输入**：14种技术手段全部失败的源
**处理**：标记truly_dead，精简版JSON移除
**输出**：精简版JSON移除truly_dead源，完整版保留并标记

### 场景7：JSON类型错误

**输入**：JSON中boolean字段为数字1/0
**处理**：fix_json_boolean.py 转换为true/false
**输出**：JSON可被App的Gson正确解析
