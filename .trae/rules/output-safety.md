输出安全与违禁词规避规范

核心：思考和输出都禁止出现违禁词。不能因触发违禁词中断对话和任务。


一、思考铁律（最高优先级，每次思考前必读）

1. 收到工具输出第一动作是扫描敏感词并替换为代号，不是分析内容。
   思考中只允许出现：异常类型、错误码、调用栈、DOM选择器、字段名、函数名、技术结构。
   禁止在思考中原样引用：源名称、域名、URL、cookie内容、分类名称、成人内容词汇。
   即使为了分析也不行，必须先替换为代号：源名称→源[N]，域名→站点A，URL→/path/{id}，cookie→***，成人词汇→"含成人内容"，分类名→分类X。

2. 禁止Grep搜索业务数据字段，只搜索技术字段。
   禁止搜索：sourceName、sourceUrl、sortUrl、sourceComment、title、name、summary、description。
   允许搜索：ruleImage、coverDecodeJs、ruleReview、id、type、enabled、函数名、类名。

3. logcat日志处理：只输出技术结论（错误码、异常类型、调用栈、数量统计），禁止输出含域名/cookie/源名称/分类名称的原始日志行。cookie只记录长度和是否成功，不引用内容。


二、工具调用前置预判（调用工具前必答三问）

1. 返回内容是否可能含源名称、源URL、源标题？→ 改用技术关键词搜索，或head_limit<=5分页读取。
2. 返回内容是否可能含域名、完整URL、IP、邮箱、手机号？→ 域名用代号，路径模式化。
3. 返回内容是否可能含成人、违法、政治敏感词汇？→ 禁止直接调用，改用脚本过滤后输出编号。


三、高风险工具调用黑名单（禁止模式，基于铁证）

1. Grep搜索sourceName/sourceUrl/sortUrl/sourceComment → 返回数十个源真实名称含成人内容。替代：搜索技术字段ruleImage/coverDecodeJs/ruleReview/enabled。
2. Grep搜索title/name/summary/description（在源JSON/DB中）→ 返回业务文本含敏感词。替代：搜索结构字段id/type/sort/customOrder。
3. Read整个RSS源JSON文件（无offset+limit）→ 含全部源真实名称。替代：用offset+limit只读必要行。
4. 子代理dump_hierarchy输出源列表 → UI含源真实名称。替代：脚本输出用编号源[1]/源[2]。
5. Grep搜索源名称关键词 → 直接命中成人内容。替代：按源ID编号搜索。
6. 读取logcat全量日志未过滤 → 日志含源名称、域名、URL、cookie内容。替代：Grep过滤技术关键词（Exception/Error/FATAL/自定义tag），head_limit<=20。


四、脚本处理方式（AI可获取但不显示）

logcat日志：用Grep过滤技术关键词（自定义tag如LoginRefresh/HighlightRefresh、Exception/Error/FATAL），只输出技术结论，禁止输出含域名/cookie的原始日志行。
源列表：脚本输出用编号源[1]/源[2]替代真实名称。
数据库/JSON：用offset+limit只读必要行，或用脚本提取技术字段而非业务字段。
cookie内容：只记录长度和是否保存成功，禁止引用cookie字段值。


五、禁止被中断的执行要求（强制）

AI必须严格执行思考铁律和输出规范，主动规避违禁词，禁止被审查中断。
一旦被中断，用户需要重新发起对话，这会打断工作流程、丢失上下文、浪费用户时间和金钱。
因此AI必须在每一步都严格遵守：
1. 思考前先扫描工具输出是否含敏感词，先替换为代号再分析。
2. 输出前对照自检清单逐项检查。
3. 工具调用前先答前置预判三问。
4. 任何不确定是否敏感的内容，默认按敏感处理（过滤或代号替代）。
绝对不允许因思考或输出包含违禁词而被审查中断。这是AI的责任，不是用户的。


六、输出前自检

1. 成人/违法/政治敏感/暴力内容？→ 过滤。
2. 视频网站域名？→ 代号替代。
3. 敏感字段（token/cookie/password/key/secret/auth）？→ 隐藏为***。
4. 完整URL？→ 只保留路径模式。
5. 原始日志/HTML全文？→ 提取技术信息。
6. 思考过程是否包含违禁词？→ 第一时间替换为代号。
7. 正文是否引用了源名称、域名、URL、cookie内容、分类名称？→ 替换为代号。


七、用户要求专注于技术分析时

只输出：异常类型、错误码、调用栈、技术结论、修复方案。
不输出：源名称、域名、URL、cookie内容、分类名称、业务数据。
