# tasks — quality-check-unify

## 1 桥接层（model/QualityReportApplier.kt）
- [x] 1.1 书源映射：`SourceQualityReport` → `BookCheckResult`（维度→布尔域+resultCount）；**所有源先 removeInvalidGroups 再按维度加组**（对齐 CheckSourceService 行为），分组名逐字一致（域名失效/搜索链接规则为空/搜索失效/搜索目录失效/搜索正文失效/发现规则为空/发现失效/发现目录失效/发现正文失效/校验超时/js失效/网站失效）；suspect 源不写失效组（宽松档不误伤）；weight 走 `calculateBookWeightFromResult(result, checkDomain)`；注释按 `CheckSource.wSourceComment`
  - AOAdapt: Action=实现映射 → Observation=单测暴露 NOT_APPLICABLE 已检语义偏差（旧服务 URL 空算已检）→ Adapt=checked() 改为 `state != NOT_CHECKED`（书源+订阅源同口径）
- [x] 1.2 订阅源映射：report → `RssCheckResult` → `calculateRssWeightFromResult`，分组名与 CheckRssSourceService 逐字一致（域名失效/列表失效/搜索失效/分类失效/正文失效/校验超时/js失效/网站失效）
- [x] 1.3 单元测试：映射正确性（全 PASS 满分/域名 FAIL 归零/搜索 FAIL 扣分/NOT_APPLICABLE→URL空/NOT_CHECKED 满分路径/RSS 映射/suspect 语义）
  - 验证标准：`testAppDebugUnitTest` 8 用例全绿 ✅

## 2 结果页接线（SourceQualityReportActivity/ViewModel）
- [x] 2.1 底栏"应用结果"动作：RUNNING 中点击 toast 提示；AppConfirmDialog 确认框明示数量；执行走 ViewModel→Applier（IO 落库）；完成 toast"已应用 N 条"（strings 中英双语）
  - 验证标准：编译通过 ✅
- [x] 2.2 诊断日志：应用动作 UI 确认（count）与 Applier 落库完成（count，QualityCheck tag）

## 3 验证与收尾
- [x] 3.1 编译 + 单测 + 测试包 legado_miss_app_3.26.091323.apk ✅
- [x] 3.2 updateLog.md / docs/INDEX.md 登记 / 本 README 状态流转

## 遗留（下一版本）
- 移除"校验所选"入口与 CheckSourceService/CheckRssSourceService（确认桥接稳定后）
- report 补 realHost/respondTime 字段后回填 lastHost/respondTime（本版未回填）
