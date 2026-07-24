# Legados Forks 对比与集成 - 任务清单

> 基于 spec.md 和 design.md 的实施任务分解，按优先级分阶段执行。
> P0 调整为 7 项（UrlRecordInterceptor 降级到 P1）。

---

## 1. 准备工作

- [ ] 1.1 确认需求范围（P0 7项/P1 5项/P2 6项，含三维度审查后的修正）
- [ ] 1.2 阅读本项目关键源码确认接口缺口（已完成：PaintPool无clear()/CacheManager有evictAll()/AppConfig用SP/BackupConfig差异）
- [ ] 1.3 确认 Markwon 依赖（已完成：本项目已有 markwon.core/image.glide/ext.tables/html）
- [ ] 1.4 确认 BackupConfig 字段差异清单（已完成：fork多出bookCacheKey+ignoreBookCache+R.string.book_cache）
- [ ] 1.5 编写 BackupConfig 字段差异备忘文档（详见 spec.md "BackupConfig 字段差异清单"章节）

## 2. 前置条件准备（接口缺口修复）

- [ ] 2.1 PaintPool 新增 clear() 方法（回收所有对象并清空池）
- [ ] 2.2 AppConfig 新增 mdLinkInnerBrowser Boolean 字段（SharedPreferences，默认 true）
- [ ] 2.3 strings.xml 新增 R.string.book_cache 条目
- [ ] 2.4 编译验证前置修改无错误

## 3. P0 高价值功能移植（7项）

- [ ] 3.1 移植 HelpDoc(6行) + HelpDocManager(69行) 内置帮助文档系统
- [ ] 3.2 移植 MemoryPressure(90行) 内存压力监控
- [ ] 3.3 移植 InnerBrowserUrlSpan(24行) + InnerBrowserLinkResolver(24行) 内部链接解析
- [ ] 3.4 移植 BackupFileValidator(597行) 备份文件验证
- [ ] 3.5 移植 BackupInfoHelper(324行) 备份信息展示
- [ ] 3.6 移植 StorageCalculator(782行) 存储空间管理
- [ ] 3.7 移植 SpecialContentProtector(41行) 内容保护

## 4. P0 集成适配

- [ ] 4.1 App.kt 注册 MemoryPressure ComponentCallbacks2 回调
- [ ] 4.2 CacheManager.memoryLruCache.evictAll() 集成到 MemoryPressure 释放流程
- [ ] 4.3 PaintPool.clear() 集成到 MemoryPressure 释放流程
- [ ] 4.4 ContentProcessor.kt 集成 SpecialContentProtector 处理步骤
- [ ] 4.5 Restore.kt 集成 BackupFileValidator 验证逻辑 + AlertDialog 失败提示
- [ ] 4.6 BackupActivity 集成 BackupInfoHelper 信息卡片
- [ ] 4.7 新建 HelpDocActivity（左侧文档列表 + 右侧 Markdown 渲染）
- [ ] 4.8 新建 StorageManageActivity（缓存详情列表 + 一键清理）
- [ ] 4.9 AboutActivity/MainFragment 添加"帮助文档"入口按钮
- [ ] 4.10 SettingsActivity 添加"存储管理"入口 + mdLinkInnerBrowser 开关
- [ ] 4.11 创建 assets/help/ 目录并编写帮助文档内容
- [ ] 4.12 InnerBrowserUrlSpan/InnerBrowserLinkResolver 集成到阅读内容渲染流程
- [ ] 4.13 编译验证 P0 功能无错误

## 5. P0 功能测试验证

- [ ] 5.1 MemoryPressure 测试：ADB send-trim-memory 命令验证回调触发 + AppLog 日志输出
- [ ] 5.2 BackupFileValidator 测试：正常备份文件 + 损坏JSON + 缺必需字段 3种夹具验证
- [ ] 5.3 InnerBrowserLink 测试：内部链接 + 外部链接 + 开关关闭 3种场景
- [ ] 5.4 HelpDoc 测试：验证文档列表展示 + Markdown 渲染 + 文档切换
- [ ] 5.5 StorageCalculator 测试：验证缓存大小计算准确性 + 清理操作执行
- [ ] 5.6 SpecialContentProtector 测试：验证 HTML 标签保护效果
- [ ] 5.7 BackupInfoHelper 测试：验证备份概况信息卡片展示
- [ ] 5.8 回归测试：阅读 + 书源搜索 + 书架管理 + 备份恢复 + RSS 阅读

## 6. P1 中价值功能移植与集成（5项）

- [ ] 6.1 移植 UrlRecordInterceptor(201行) + AppConfig 新增 urlRecordEnabled（默认 false）+ HttpHelper 条件性添加
- [ ] 6.2 UrlRecordInterceptor 性能测试：100次请求延迟对比（开/关状态）
- [ ] 6.3 移植 CoverHtmlTemplateConfig(189行) + BookCover 集成
- [ ] 6.4 BackupConfig 差异合并（新增 bookCacheKey + ignoreBookCache）
- [ ] 6.5 移植 BubblePackageManager(287行) + 段评 UI 集成
- [ ] 6.6 AudioPlay.kt 选择性差异合并（逐行对比，仅合并歌词回调等有价值逻辑）
- [ ] 6.7 编译验证 P1 功能无错误

## 7. 文档同步

- [ ] 7.1 更新 docs/project-flow/modules/ 相关文档（新增 HelpDoc/MemoryPressure/StorageCalculator 等模块说明）
- [ ] 7.2 更新 docs/project-flow/task-navigation.md 模块锚点
- [ ] 7.3 更新 docs/project-flow/quick-reference.md（新增帮助文档/存储管理命令）
- [ ] 7.4 更新 docs/INDEX.md 状态（移动到"已完成的功能"）
- [ ] 7.5 更新 assets/updateLog.md
