# Tasks: RSS 订阅源年龄验证自动绕过

## 1. 需求分析与源码验证
- [x] 1.1 分析目标站点年龄验证机制（已确认：服务端Cookie校验，Cookie名=YES_Eighteen）
- [x] 1.2 阅读 Legado RssSource 实体定义，确认可用字段（header/loginCheckJs/injectJs/enabledCookieJar）
- [x] 1.3 阅读 Rss.kt 执行链路，确认 loginCheckJs 执行时机
- [x] 1.4 阅读 ReadRssActivity WebView 流程，确认 injectJs 执行时机和 CookieManager 链路
- [x] 1.5 用 curl 获取站点真实 HTML，验证 Cookie 机制和验证页结构

## 2. 核心实现 - 修改订阅源 JSON
- [ ] 2.1 修改 header 字段：添加 Cookie 预置（Layer 1 - OkHttp 层）
- [ ] 2.2 新增 loginCheckJs 字段：检测验证页 + 自动请求验证URL（Layer 2 - OkHttp 兜底）
- [ ] 2.3 新增 injectJs 字段：检测验证按钮 + 自动点击（Layer 3 - WebView 兜底）
- [ ] 2.4 验证 JSON 格式正确性（Rhino ES5 兼容、jsoup 选择器正确）

## 3. 验证
- [ ] 3.1 用 curl 验证 Header Cookie 预置是否生效
- [ ] 3.2 验证 loginCheckJs 逻辑是否正确（JS 语法、Rhino 兼容性）
- [ ] 3.3 验证 injectJs 逻辑是否正确（DOM 选择器、点击触发）
- [ ] 3.4 输出优化后的完整订阅源 JSON

## 4. 自进化 - 更新 Skill 文档
- [ ] 4.1 更新 troubleshooting.md：新增"服务端年龄验证自动绕过"经验
- [ ] 4.2 更新 js-patterns.md：新增 loginCheckJs 静默验证模式
- [ ] 4.3 更新 SKILL.md：新增"年龄验证自动破除"决策参考
