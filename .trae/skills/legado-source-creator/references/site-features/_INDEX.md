# 网站特征与高频问题模式索引

> 基于真实源验证（9.1-9.5）+ 修复后测试（2026-06-20）积累的高频问题模式，按网站特征分类，提供解决方案指针。

## 目录

| 文档 | 覆盖场景 | 关联源 |
|------|---------|--------|
| [high-frequency-issues.md](./high-frequency-issues.md) | 7 大高频问题模式 + 修复方案 + 修复后真实测试统计 | 51cg/611371056/acgfta/mjv006/jfg/1080zyk |
| [relative-url-pattern.md](./relative-url-pattern.md) | 相对 URL 拼接模式 | 51cg/acgfta/mjv006 |
| [cf-shield-pattern.md](./cf-shield-pattern.md) | CF 盾检测与降级 | 1080zyk/611371056 |
| [site-feature-to-rule-type.md](./site-feature-to-rule-type.md) | 网站特征→规则类型映射表 | txtzw/uaa/18AV/秀人集 |
| [webview-requirements.md](./webview-requirements.md) | WebView 需求模式文档 | 18AV-new/秀人集v20/禁漫天堂 |

## 验证统计

### 修复前（已废弃 - 假成功）

| 指标 | 数值 | 说明 |
|------|------|------|
| 验证源总数 | 7（6 RSS + 1 书源）| |
| ~~通过率~~ | ~~100%~~ | ⚠️ 假成功，debug() 吞掉异常 |

### 修复后（2026-06-20 真实结果）

| 指标 | 数值 | 说明 |
|------|------|------|
| 测试源总数 | 20（10 书源 + 10 订阅源）| |
| 通过率 | 0% | 真实结果，不再假成功 |
| 网络失败 | 50% | 网站已失效 |
| 搜索/发现失败 | 40% | 规则不匹配或源格式不标准 |
| needsWebView | 0% | 未检测到（网络先失败）|
| needsUserIntervention | 0% | 未检测到（网络先失败）|
