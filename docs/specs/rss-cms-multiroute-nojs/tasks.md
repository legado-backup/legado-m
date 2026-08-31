# tasks.md — rss-cms-multiroute-nojs

> 功能：视频订阅源多线路多集零JS解析增强 + CMS采集书源转化（MacCMS 免JS多线路多集）
> 测试包：`io.legado.miss.app.debug`（代码开发阶段用测试包，禁止混用正式包，铁证规范 package-naming.md）
> 验证要求：必须用 `ai_tests\venv\Scripts\python.exe`；测试前必读 `ai_tests/docs/fixed_test_workflow.md`
> 关联文档：[spec.md](./spec.md) ｜ [design.md](./design.md) ｜ [rss-subsystem.md](../../project-flow/modules/rss-subsystem.md)
> 说明：任务完成即勾选 `- [x]`；实施中遇到问题在文末 `## AOAdapt 日志` 按 Action/Observation/Adapt 补记（24H 制）。

## 1. 准备工作

- [ ] 1.1 重新核实 `Rss.kt`（parseEpisodesByLines 现状）与 `AnalyzeRule.kt`（getString 大括号 `{{$.xxx}}` 模板支持、replaceRegex 分段语义）关键行号与现状：行号可能漂移，禁止凭设计文档行号直接改，以当次读取为准
- [ ] 1.2 请求目标站点 API 验证响应结构：确认 `class` 数组字段、`vod_play_from`/`vod_play_url` 真实格式（`$$$` 线路分隔、`#` 集分隔、`$` 名/址分隔）、m3u8 直链可达性；记录仅保留路径模式（如 `/api.php/provide/vod?ac=detail&ids={id}`），不落域名原文
- [ ] 1.3 获取真实分类数据（class 数组 type_id/type_name）生成 sortUrl 静态枚举（形如 `分类名::/path/{type_id}` 多行值），作为 3.1 sortUrl 输入
- [ ] 1.4 阅读 `ai_tests/docs/fixed_test_workflow.md` 确认真机测试八步流程、固化脚本入口（quick_build_install.py / import_rss_source.py）与 venv 解释器要求

## 2. 解析层增强（Rss.kt）

- [ ] 2.1 数据规范化层 + 解析层兜底增强（v3）：①新增 `normalizeMacCmsBody`——检测详情响应 JSON 含 `vod_play_from`/`vod_play_url` 带 `$$$` 时增量注入结构化 routes（原字段不动、非 JSON/无特征零侵入、item 已有 routes 字段跳过并记 AppLog），在 `getRoutesContentAwait`/`getEpisodesAwait` 2 处 `setContent` 调用点前接入；②`ruleRoutes` 采集点改 `getStringList` 优先取线路名列表，空时回落 `getString`+`\n` 分割（旧源兼容）；③`parseEpisodesResult` 增加 routeIndex 参数（2 处调用点传入），结果非 JSON 数组且含 `$$$` 时隐式按线路分组取第 N 组兜底，越界取首组并记 AppLog；④`parseEpisodesByLines` 增强 CMS 段解析：识别 `集名$URL#集名$URL` 段——先按 `#` 分割、再按 `$` 以 limit=2 拆名/址，title 缺省为「第N集」；旧格式（多行纯URL）保持兼容，JSON 数组分支不动
- [ ] 2.2 编写边界用例自查：含 `$$$` 多线路串各 routeIndex（0/中间/最后/越界取首组）、单线路无 `$$$`、集名含特殊字符（含 `$`/`#`）、空段、末尾无 `#`、畸形 play_url 不崩溃、旧格式（多行URL / JSON数组）回归、item 已有 routes 字段跳过规范化（原字段保留断言）、`$.routes[*].name` 列表规则（getStringList 优先）、`$.routes[N].episodes` 各 routeIndex 正确互不串线、回落路径旧写法（`$.list[0].vod_play_from##\$\$\$##\n`）回归；逐条记录预期与实际输出（临时验证脚本禁止放 `temp/`）
- [ ] 2.3 基于 `git diff` 逐文件对照变更，更新 `app/src/main/assets/updateLog.md`（追加在 `## cronet版本:` 之后、已有条目之前；面向用户语言；编译前完成，禁止交付阶段才补写）

## 3. 订阅源转化

- [ ] 3.1 生成量子站视频订阅源 JSON（type=2），全部规则字段按设计填入：searchUrl `...?ac=detail&pg={{page}}&wd={{key}}`；ruleArticles `$.list[*]`；ruleTitle `$.vod_name##\.mp4$`；ruleImage `$.vod_pic`；ruleDescription `$.vod_remarks`；ruleLink `https://{API域名}/api.php/provide/vod?ac=detail&ids={{$.vod_id}}`（绝对URL + 大括号模板）；ruleRoutes **列表范式 `$.routes[*].name`**（规范化层注入 routes；兜底写法 `$.list[0].vod_play_from##\$\$\$##\n`，注意成对 `##` 分段）；ruleEpisodes **列表范式 `$.routes[{routeIndex}].episodes`**（`{routeIndex}` 占位符对五种模式透明，兜底写法纯 JSONPath `$.list[0].vod_play_url` 走隐式分组，源 JSON 内换行写作 `\n`）；ruleContent 留空；sortUrl 用 1.3 静态枚举
- [ ] 3.2 导入测试包（`io.legado.miss.app.debug`）验证源 JSON 合法性：字段完整性检查（必填字段、正则转义、`\n` 换行符写入格式），导入无报错；注意开发阶段禁止用正式包（package-naming.md）

## 4. 编译验证

- [ ] 4.1 `Get-Process` 校验无残留 Gradle/Kotlin 构建进程（有残留先清场再编译，防打爆内存）
- [ ] 4.2 `build-legado.bat` 打测试包（内置 `:STOP_DAEMON` 自动清场），编译通过 0 error；如走直接 gradlew 需事后补 `stop-daemons.bat`
- [ ] 4.3 安装到模拟器/真机（`quick_build_install.py` 或 adb install），确认 L1 启动正常

## 5. 真机 L2 验证

- [ ] 5.1 分类 Tab 加载与列表页解析：sortUrl 静态分类展示、ruleArticles 列表条目数、ruleTitle 标题（确认尾部 `.mp4` 已去除）、ruleImage 封面加载
- [ ] 5.2 点开影片：多线路采集（ruleRoutes 列表范式 `$.routes[*].name` 展示线路名）+ 第一线路集数列表（ruleEpisodes 列表范式 `$.routes[0].episodes` routeIndex=0，第N集命名正确）
- [ ] 5.3 切换线路按需采集集数：确认走 `getEpisodesAwait` 链路重新拉取详情并按列表范式 `$.routes[N].episodes` 取对应线路集数，N=1/2 边界正常、超界线路有兜底表现（不崩溃）
- [ ] 5.4 播放验证：m3u8 直链起播，集名显示「第N集」或源集名
- [ ] 5.5 搜索功能验证：searchUrl `{{key}}`/`{{page}}` 注入正确，返回结果列表可点入
- [ ] 5.6 回归验证：既有旧格式集数源（多行URL / JSON数组）不回归，原订阅源播放正常
- [ ] 5.7 `{{$.xxx}}` 大括号模板生效确认：ruleLink/ruleEpisodes 中 vod_id 注入成功（详情页可打开即证明），ruleRoutes 线路名展示正确，`$.routes[*].name` 列表规则（getStringList）生效确认

## 6. 收尾

- [ ] 6.1 issues-found.md 记录所有真机问题（异常类型/错误码/复现步骤，不引用域名与源名称原文）并复核闭环
- [ ] 6.2 文档同步：`docs/project-flow/modules/rss-subsystem.md` 补集数格式支持说明（MacCMS `名$址#` 段免JS解析）；`docs/INDEX.md` 状态流转更新
- [ ] 6.3 清理临时脚本/临时日志：Grep 确认 0 残留（`android.util.Log.d|Log.e` 调试日志 + `temp/` 临时文件），已建的删除
- [ ] 6.4 经验沉淀到项目记忆（`.trae/memory/ai_memory_main.md`）：关键决策、坑点、AOAdapt 摘要；CMS 免JS陷阱可同步沉淀至 legado-source-creator troubleshooting
- [ ] 6.5 （可选，另行确认）其余 12 个资源站批量转化：逐站确认 API 结构差异后再启动，不随本任务自动展开

## AOAdapt 日志

> 实施中遇到问题时按以下格式补记（Action=做了什么 / Observation=观察到什么 / Adapt=如何调整），时间 24H 制：
>
> - [YYYY-MM-DD HH:MM] 问题描述
>   - Action:
>   - Observation:
>   - Adapt:
