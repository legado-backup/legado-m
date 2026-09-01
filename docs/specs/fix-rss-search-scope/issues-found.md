# Issues Found: 订阅搜索范围上下文修复

## IF-01: 搜索页菜单切换范围时同关键词双触发重搜（观察项，非本 spec 范围）

- **来源**：2026-09-02 真机验证 3.3-⑤（手动切换范围）appLog 证据
- **现象**：搜索页"更多菜单"切换范围后，同关键词触发两次搜索——`RssSearchActivity.initData` 的 `searchScope.stateLiveData` observer（query 非空自动 `submitSearch`）与菜单动作处理里的 `reSearchIfNeeded()`（`handleMenuAction`/`handleGroupSelect` 内显式再搜）各发一次，appLog 可见两条 `开始RSS搜索 searchId=…`（相差约 5ms，第二次 `cancelSearch` 取消第一次）
- **影响**：功能结果正确（第二次搜索完整执行、结果与源数量判定均正常），仅多一次并发搜索开销；用户无感
- **归属**：rss-unified-search 既有接线逻辑，非 fix-rss-search-scope 改动引入（本 spec 仅改 scope 计算/传参，不动搜索触发链）
- **处置**：登记不修；B3 Rss 域（compose 分册）动工时若重构该页可顺带收敛为单一触发点
- **状态**：已登记，待排期（随 B3）
