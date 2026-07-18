# Legado Source Creator Skill v4 重构方案

> **触发原因**：用户严厉反馈"skill 不能真正替用户创建可用源+自动测试+修复完善"
> **分析报告**：
> - `docs/temp-analysis/legado_mandatory_fields.md`（源码必填字段分析）
> - `docs/temp-analysis/ai_test_reuse_for_skill.md`（ai_test 真机测试经验）
> **创建日期**：2026-07-18

## 一、v3 根本问题反思

### 1.1 v3 做了什么（但没解决根本问题）

| 任务 | 成果 | 局限 |
|------|------|------|
| T1-T3 归档 | 砍 12 模块+45 脚本 | 只减负未增能 |
| T4 sanitize None bug | 修复 JSON 输出 | 只是基础 bug |
| T5 E2E 测试 | 10/10 通过 | 只测 sanitize 函数，没测"能否真正生成可用源" |
| T7 SKILL.md 精简 | 738→176 行 | 文档瘦身 ≠ 能力提升 |

### 1.2 用户真正要的能力（v3 全部缺失）

1. **必填字段强制校验**：生成的源缺关键字段 = 不可用 = 用户要手动补 DB
2. **真机测试集成**：JVM 仿真不是终点，要利用 ai_test 真机经验
3. **自动修复完善循环**：生成 → 测试 → 失败 → 诊断 → 修复 → 重测

## 二、关键发现（源码验证）

### 2.1 BookSource/RssSource 必填字段清单（源码验证）

**用户认知纠正**：
- ❌ BookSource **没有** icon/sortUrl 字段
- ✅ BookSource 对应概念是 `exploreUrl`（发现URL）+ `ruleBookInfo.coverImageUrl`（封面规则）
- ✅ RssSource 有 sourceIcon/sortUrl 但都是可选（有 fallback 降级）

**"功能必填"字段清单**（不填某功能不可用）：

| 字段 | BookSource | RssSource | 缺失影响 |
|------|------------|-----------|----------|
| 主键 URL | bookSourceUrl（必填） | sourceUrl（必填） | 无法导入 |
| 名称 | bookSourceName（推荐） | sourceName（推荐） | UI 显示混乱 |
| 搜索 | searchUrl | searchUrl | 搜索功能不可用 |
| 列表规则 | ruleSearch | ruleArticles | 搜索结果/列表无法解析 |
| 详情规则 | ruleBookInfo | - | 详情页无法解析 |
| 目录规则 | ruleToc | - | 章节列表无法获取 |
| 正文规则 | ruleContent | ruleContent | 正文无法获取 |
| 发现/分类 | exploreUrl（可选） | sortUrl（可选） | 发现页/分类切换不可用 |
| 图标 | ❌ 不存在 | sourceIcon（可选） | 仅影响 UI |

### 2.2 ai_test 真机测试经验（可复用）

**已积累的能力**（10 lib 模块 + 7 核心脚本 + 10 核心经验）：
- `MemuController`：MEmu 模拟器控制
- `ApkDeployer`：APK 编译+安装
- `UiExecutor`：UI 操作执行器
- `quick_build_install.py`：编译+安装+L1验证
- `import_rss_source.py`/`import_book_source.py`：导入源（含 Room WAL 处理）
- `batch_source_test.py`：批量源遍历
- `nav_helper.py`：脱敏导航
- 关键经验：Room WAL 模式 / dismiss_dialogs / swipe_ext / 脱敏范式

## 三、v4 重构方案

### 3.1 核心架构：3 层能力

```
Layer 1: 生成层（必填字段校验器）
  → 源 JSON 生成时强制校验功能必填字段
  → 缺字段时拒绝输出，提示 AI 补全

Layer 2: 静态校验层（增强现有 skill 脚本）
  → sanitize_source_json（已有）
  → mandatory_field_validator（新增）
  → quick-verify.py（已有，增强字段校验）

Layer 3: 真机验证层（集成 ai_test）
  → quick_build_install.py（复用）
  → import_rss_source.py / import_book_source.py（复用）
  → 新增 source_runtime_validator.py（真机加载验证）
  → 新增 auto_fixer_loop.py（自动修复循环）
```

### 3.2 必填字段校验器设计

```python
# .trae/skills/legado-source-creator/scripts/legado_client/validator/mandatory_fields.py

class MandatoryFieldValidator:
    """必填字段校验器：基于 Legado 源码功能必填字段清单。"""

    BOOK_SOURCE_MANDATORY = {
        "导入层": ["bookSourceUrl"],
        "搜索功能": ["searchUrl", "ruleSearch.bookList", "ruleSearch.name"],
        "详情功能": ["ruleBookInfo.name", "ruleBookInfo.author"],
        "目录功能": ["ruleToc.chapterList", "ruleToc.chapterName"],
        "正文功能": ["ruleContent.content"],
    }

    RSS_SOURCE_MANDATORY = {
        "导入层": ["sourceUrl"],
        "列表功能": ["ruleArticles", "ruleTitle", "ruleLink"],
        "正文功能": ["ruleContent"],
        "推荐": ["sourceName", "sortUrl"],  # 不强制但强烈推荐
    }

    def validate(self, source_dict: dict, source_type: str) -> dict:
        """返回校验结果：missing_fields / warning_fields / passed"""
        ...
```

### 3.3 真机测试集成设计

```python
# .trae/skills/legado-source-creator/scripts/legado_client/validator/runtime_validator.py

class RuntimeValidator:
    """真机运行时验证器：复用 ai_test 能力。"""

    def __init__(self):
        # 复用 ai_test/lib 模块
        from ai_tests.lib.memu_controller import MemuController
        from ai_tests.lib.apk_deployer import ApkDeployer
        self.memu = MemuController()
        self.deployer = ApkDeployer()

    def validate_source_loadable(self, source_json: str, source_type: str) -> dict:
        """验证源能否真机加载。
        1. quick_build_install.py 编译+安装
        2. import_rss_source.py / import_book_source.py 导入
        3. 打开 Legado → 验证源加载
        4. 返回：success/failed_stage/error_msg
        """
        ...
```

### 3.4 自动修复完善循环设计

```python
# .trae/skills/legado-source-creator/scripts/legado_client/validator/auto_fixer_loop.py

class AutoFixerLoop:
    """自动修复循环：生成 → 测试 → 诊断 → 修复 → 重测。"""

    MAX_ITERATIONS = 3

    def run(self, source_dict: dict, source_type: str) -> dict:
        """端到端自动修复循环。"""
        for i in range(self.MAX_ITERATIONS):
            # 1. 必填字段校验
            validation = self.validator.validate(source_dict, source_type)
            if validation["missing_fields"]:
                source_dict = self._fix_missing_fields(source_dict, validation)
                continue

            # 2. 真机测试
            runtime_result = self.runtime_validator.validate_source_loadable(...)
            if runtime_result["success"]:
                return {"success": True, "source": source_dict}

            # 3. 失败诊断 + 修复
            fix = self._diagnose_and_fix(runtime_result, source_dict)
            if not fix["applied"]:
                return {"success": False, "reason": "无法自动修复"}
            source_dict = fix["source"]

        return {"success": False, "reason": "超过最大修复次数"}
```

## 四、v4 实施路线图

### Phase 1: 必填字段校验器（核心）
- T1: 新增 `validator/mandatory_fields.py`（基于源码清单）
- T2: 集成到 `auto_fixer.py` 生成流程
- T3: 新增 E2E 测试用例（缺字段拒绝输出）

### Phase 2: 真机测试集成
- T4: 新增 `validator/runtime_validator.py`（复用 ai_test）
- T5: 集成 `quick_build_install.py` + `import_*_source.py`
- T6: 新增真机加载验证测试

### Phase 3: 自动修复循环
- T7: 新增 `validator/auto_fixer_loop.py`
- T8: 集成必填校验 + 真机测试 + 诊断修复
- T9: 端到端验证：AI 生成源 → 自动修复 → 真机可用

### Phase 4: 文档与经验沉淀
- T10: SKILL.md 更新 v4 工作流
- T11: 经验写入 basic-memory
- T12: v4 验收

## 五、与 v3 的关系

**v3 已完成的保留**：
- sanitize_source_json 函数（v4 继续用）
- 归档后的精简 legado_client 包
- E2E 测试框架

**v3 剩余任务调整**：
- T6 文档合并：延后到 v4 Phase 4
- T9 真机单点验证：取消，由 v4 Phase 2 取代

**v4 新增**：
- validator/ 模块（3 个新文件）
- 必填字段清单（基于源码）
- ai_test 集成（复用现有能力）
