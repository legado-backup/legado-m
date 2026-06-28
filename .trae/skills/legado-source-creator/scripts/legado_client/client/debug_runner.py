#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试运行器：从 debug-source.py 提取的核心调试流程。

包含 DebugCollector、辅助函数、run() 入口。
集成孤儿模块：evaluate_confidence / create_interaction_request / navigate_to_source / select_parse_strategy。
JSON去重：run() 入口解析一次 source_obj，后续传递对象。
STAGE_NAMES 统一：使用字符串键而非整数键。

阶段三增强（3.1-3.9）：
- _check_database(): 数据库查询钩子，查同域名源（3.1）
- 四分支处理：命中通过/命中失败/命中修复失败/未命中（3.2-3.5）
- run_and_return(): 异步入口，返回结构化结果（不 sys.exit）
- --skip-db-lookup / --db-only 参数支持（3.7-3.8）
- 数据库降级：config.db_available=False 时跳过所有数据库操作（3.9）
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# 添加 scripts/ 和 tools/ 目录到 sys.path（用于外部可选模块）
from legado_client.utils.config import config
sys.path.insert(0, str(config.scripts_dir))
sys.path.insert(0, str(config.tools_dir))

# 包内模块导入（不需要 try/except）
from legado_client.client.rule_engine_client import RuleEngineClient
from legado_client.analyzer.error_diagnoser import diagnose_error
from legado_client.analyzer.confidence_evaluator import evaluate_confidence
from legado_client.analyzer.source_navigation import navigate_to_source
from legado_client.analyzer.parse_strategy import select_parse_strategy
from legado_client.client.user_interaction import create_interaction_request
from legado_client.experience.experience_manager import search_experience, ExperienceManager
from legado_client.utils.file_utils import load_source_object
from legado_client.analyzer.source_validator import SourceValidator
from legado_client.analyzer.rule_precheck import RulePrecheck

# 包内核心模块导入（已迁移至 legado_client/，不再需要 try/except 降级）
from legado_client.client.obstacle_resolver import resolve_obstacle
from legado_client.analyzer.crypto_analyzer import analyze_encryption
from legado_client.analyzer.auto_fixer import auto_fix_error
from legado_client.client.interactive_guide import report_progress

# 数据库查询钩子（3.1-3.5, 3.9）
from legado_client.fetcher.source_parser import extract_domain_key

# 兼容性标志（保留以避免修改使用处逻辑，现在始终为 True）
_OBSTACLE_RESOLVER_AVAILABLE = True
_CRYPTO_ANALYZER_AVAILABLE = True
_AUTO_FIXER_AVAILABLE = True
_INTERACTIVE_GUIDE_AVAILABLE = True

# 外部可选模块导入已移除（cookie_manager/smart_http_client/knowledge_matcher 待迁移至 legado_client 包内）
# 简化说明：保留可用性标志为 False 以避免使用处 NameError | 已知上限：Cookie持久化/智能HTTP/知识库匹配功能暂不启用 | 升级路径：模块迁移至包内后恢复导入
_COOKIE_MANAGER_AVAILABLE = False
_SMART_HTTP_CLIENT_AVAILABLE = False
_KNOWLEDGE_MATCHER_AVAILABLE = False


# ==================== 常量定义（方向7.3: STAGE_NAMES 使用字符串键） ====================

STAGE_NAMES: Dict[str, str] = {
    "search": "搜索页",
    "detail": "详情页",
    "toc": "目录页",
    "content": "正文页",
}

# JVM 服务端返回的整数 state → 字符串 stage 映射
STATE_TO_STAGE: Dict[int, str] = {
    10: "search",
    20: "detail",
    30: "toc",
    40: "content",
}


# ==================== 阶段七集成辅助函数（7.1-7.9） ====================

def _detect_obstacle_type(msg: str, stack_trace: Optional[str]) -> Optional[str]:
    """7.1-7.3: 从错误信息检测障碍类型（登录/CF/验证码）。

    Returns:
        str | None: 'login'/'cf'/'captcha' 或 None
    """
    combined = f"{msg} {stack_trace or ''}".lower()
    if any(kw in combined for kw in ('登录', 'login', 'signin', '未登录', 'unauthorized', '401')):
        return 'login'
    if any(kw in combined for kw in ('cloudflare', 'cf-challenge', 'just a moment',
                                       'cf_browser', 'challenge-platform', '5秒')):
        return 'cf'
    if any(kw in combined for kw in ('验证码', 'captcha', 'verifycode', 'vcode',
                                       'geetest', 'recaptcha')):
        return 'captcha'
    return None


def _extract_js_from_source(source_obj: dict) -> str:
    """7.4: 从源对象中提取所有 JS 代码片段（@js: / <js>）。

    JSON去重：直接接收 source_obj 字典，不再 json.loads。
    """
    js_parts: List[str] = []
    _js_inline = re.compile(r'@js:(.+?)(?:\n@|$)', re.DOTALL)
    _js_tag = re.compile(r'<js>(.+?)</js>', re.DOTALL)

    def _scan(value) -> None:
        if isinstance(value, str):
            js_parts.extend(m.group(1) for m in _js_inline.finditer(value))
            js_parts.extend(m.group(1) for m in _js_tag.finditer(value))
        elif isinstance(value, dict):
            for v in value.values():
                _scan(v)

    _scan(source_obj)
    return "\n".join(js_parts)


def _run_crypto_analysis(source_obj: dict) -> None:
    """7.4: 扫描源中的 JS 加密调用并输出分析报告。

    JSON去重：直接接收 source_obj 字典。
    """
    if not _CRYPTO_ANALYZER_AVAILABLE:
        return
    js_code = _extract_js_from_source(source_obj)
    if not js_code:
        return
    try:
        report = analyze_encryption(js_code)
        if report.get('has_encryption'):
            print(f"\n  🔐 加密分析: 检测到 {report['call_count']} 处加密调用")
            print(f"     摘要: {report.get('summary', '')}")
            for call in report.get('calls', [])[:5]:
                print(f"     - {call['type']}/{call['operation']} mode={call.get('mode', '?')}"
                      f" key_source={call.get('key_source', '?')}")
                if call.get('decrypt_code'):
                    print(f"       解密模板已生成 (transformation={call.get('transformation', '?')})")
    except Exception as e:
        print(f"  ⚠️ 加密分析异常: {e}")


# ==================== 增强验证报告（5.5） ====================

def _print_evolution_history() -> None:
    """5.5.1 进化记录：从 .evolution_log.json 读取最近5条"""
    print("\n进化记录:")
    log_file = config.scripts_dir / ".evolution_log.json"
    if not log_file.exists():
        print("  (无进化历史)")
        return
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
        if not logs:
            print("  (无进化记录)")
            return
        for entry in logs[-5:]:
            print(f"  v{entry.get('version', '?')} | {entry.get('timestamp', '?')} | {entry.get('change', '?')}")
            print(f"    触发原因: {entry.get('trigger_reason', '?')}")
    except (json.JSONDecodeError, IOError):
        print("  (进化记录读取失败)")


def print_enhanced_report(source_obj: dict) -> None:
    """5.5.4 输出增强验证报告：进化记录 + 网站类型标注。

    JSON去重：直接接收 source_obj 字典。
    """
    print(f"\n{'='*60}")
    print("增强验证报告")
    print(f"{'='*60}")
    _print_evolution_history()


# ==================== 日志回调 ====================

class DebugCollector:
    """收集调试日志和 HTML 源码。

    方向7.3: STAGE_NAMES 使用字符串键。
    方向4: on_error 集成 navigate_to_source + create_interaction_request。
    方向4: generate_report 集成 evaluate_confidence。
    """

    STAGE_NAMES = STAGE_NAMES  # 引用模块级常量

    def __init__(self, source_obj: Optional[dict] = None, site_url: str = "",
                 cookie_store: Optional[dict] = None):
        self.source_obj: Optional[dict] = source_obj
        self.site_url: str = site_url
        self.cookie_store: Optional[dict] = cookie_store
        self.logs: List[dict] = []
        self.html_sources: Dict[str, str] = {}  # stage_str -> html
        self.errors: List[dict] = []
        self.result: Optional[dict] = None
        self.stages_passed: List[str] = []
        self.stages_failed: List[str] = []
        self.unverifiable_items: List[str] = []

    def on_log(self, state: int, msg: str, html: Optional[str]) -> None:
        """日志回调。方向7.3: state(整数) → stage(字符串) 映射。"""
        print(msg)

        # 收集 HTML 源码
        stage = STATE_TO_STAGE.get(state, str(state))
        if html and stage in self.STAGE_NAMES:
            self.html_sources[stage] = html
            print(f"  [HTML 已收集] {self.STAGE_NAMES[stage]} ({len(html)} 字符)")

        self.logs.append({"state": state, "msg": msg})

    def on_error(self, msg: str, stack_trace: Optional[str],
                 failed_stage: Optional[str]) -> None:
        """错误回调。

        方向5：使用ErrorDiagnoser替换_generate_error_suggestion。
        方向4：集成 navigate_to_source（源码定位）+ create_interaction_request（用户交互）。
        """
        print(f"[ERROR] {msg}")
        if failed_stage:
            print(f"  失败阶段: {failed_stage}")
        if stack_trace:
            print(f"  堆栈: {stack_trace[:500]}")

        # 方向5：错误诊断
        suggestion = diagnose_error(msg, stack_trace, failed_stage)
        if suggestion:
            print(f"  💡 修复建议: {suggestion['summary']}")
            for tip in suggestion.get('tips', []):
                print(f"     - {tip}")

        # 方向4孤儿模块集成：navigate_to_source — 输出源码定位信息
        error_type = suggestion.get("error_type", "") if suggestion else ""
        if error_type:
            source_info = navigate_to_source(error_type)
            if source_info.get("jvm_file") != "未知":
                print(f"  📍 源码定位: {source_info['jvm_file']}:{source_info['jvm_line']}")
                print(f"     真机对应: {source_info['real_file']}:{source_info['real_line']}")
                if source_info.get("note"):
                    print(f"     备注: {source_info['note']}")

        # 方向4孤儿模块集成：create_interaction_request — 需用户介入时输出交互请求
        if self.source_obj and error_type:
            interaction = create_interaction_request(self.source_obj, error_type, msg)
            if interaction:
                print(f"  🔔 用户交互: {interaction['message']}")
                print(f"     建议: {interaction.get('suggestion', '')}")
                if interaction.get("needs_user_input"):
                    print(f"     需要输入: {interaction['needs_user_input']}")

        self.errors.append({
            "msg": msg,
            "stackTrace": stack_trace,
            "failedStage": failed_stage,
            "suggestion": suggestion,
        })

        if failed_stage and failed_stage not in self.stages_failed:
            self.stages_failed.append(failed_stage)

    def on_result(self, success: bool, summary: dict) -> None:
        """结果回调"""
        self.result = {"success": success, "summary": summary}

        if success:
            stages = summary.get("stages", "")
            if stages:
                # 3.7: 支持三种分隔符（→/->/, ）
                normalized = stages.replace("->", "→").replace(",", "→")
                for stage in normalized.split("→"):
                    stage = stage.strip()
                    if stage and stage not in self.stages_passed:
                        self.stages_passed.append(stage)

        print(f"\n{'='*60}")
        print(f"调试结果: {'✅ 成功' if success else '❌ 失败'}")
        print(f"{'='*60}")

        if summary:
            for key, value in summary.items():
                print(f"  {key}: {value}")

    def generate_report(self) -> str:
        """生成验证报告。

        方向4孤儿模块集成：evaluate_confidence — 替代手动可信度评估。
        """
        print(f"\n{'='*60}")
        print("验证报告")
        print(f"{'='*60}")

        # 阶段通过情况
        all_stages = ["search", "detail", "toc", "content", "sort"]
        print("\n阶段通过情况:")
        for stage in all_stages:
            if stage in self.stages_passed:
                print(f"  ✅ {stage}: 通过")
            elif stage in self.stages_failed:
                print(f"  ❌ {stage}: 失败")

        # 失败阶段
        if self.stages_failed:
            print(f"\n失败阶段: {', '.join(self.stages_failed)}")

        # 5.1.1: 修复建议
        if self.errors:
            print(f"\n修复建议:")
            for i, err in enumerate(self.errors, 1):
                sug = err.get('suggestion')
                if sug:
                    print(f"  [{i}] {sug['summary']}")
                    for tip in sug.get('tips', []):
                        print(f"      - {tip}")
                    if sug.get('possible_cause'):
                        print(f"      可能原因: {sug['possible_cause']}")
                    if sug.get('rule_debug'):
                        print(f"      规则调试: {sug['rule_debug']}")

        # 不可仿真项
        for log in self.logs:
            if "不可仿真" in log.get("msg", "") or "unverifiable" in log.get("msg", "").lower():
                self.unverifiable_items.append(log["msg"])

        if self.unverifiable_items:
            print(f"\n不可仿真项:")
            for item in self.unverifiable_items:
                print(f"  ⚠️ {item}")

        # HTML 源码收集情况
        if self.html_sources:
            print(f"\nHTML 源码收集:")
            for stage, html in self.html_sources.items():
                stage_name = self.STAGE_NAMES.get(stage, f"stage={stage}")
                print(f"  📄 {stage_name}: {len(html)} 字符")

        # 方向4孤儿模块集成：evaluate_confidence — 可信度评估
        print(f"\n可信度评估:")
        confidence = "unknown"
        if self.result and self.source_obj:
            # 调用 evaluate_confidence 进行可信度评估
            test_result = {
                "success": self.result.get("success", False),
                "stages": self.result.get("summary", {}).get("stages", ""),
            }
            eval_result = evaluate_confidence(self.source_obj, test_result)
            eval_level = eval_result.get("level", "未知")
            eval_score = eval_result.get("score", 0)
            print(f"  评估器: {eval_level} (score={eval_score})")
            for warning in eval_result.get("warnings", []):
                print(f"  ⚠️ {warning}")

            # 兼容原有退出码逻辑
            if self.result["success"]:
                if self.unverifiable_items:
                    confidence = "medium"
                else:
                    confidence = "high"
            else:
                confidence = "low"
        elif self.result:
            if self.result["success"]:
                if self.unverifiable_items:
                    print("  🟡 中可信: 调试通过但存在不可仿真项")
                    confidence = "medium"
                else:
                    print("  🟢 高可信: 端到端调试全部通过")
                    confidence = "high"
            else:
                print("  🔴 低可信: 调试失败")
                confidence = "low"
        else:
            print("  ⚪ 未知: 未收到结果")
            confidence = "unknown"

        return confidence


# ==================== 方向10：多轮迭代修复闭环 ====================

# 简化说明：迭代修复仅处理rule_empty和relative_url两种高频错误 | 已知上限：其他错误类型需AI手动修复 | 升级路径：扩展apply_auto_fix的错误类型分支

def _extract_html_suggestions(collector: DebugCollector) -> List[str]:
    """从collector日志中提取HTML结构分析的建议选择器

    JVM端HtmlStructureAnalyzer输出格式：
        --- 建议选择器 ---
          书籍/文章列表: class.book-card (24 次)
          标题: class.title (10 次)
    """
    suggestions: List[str] = []
    for log in collector.logs:
        msg = log.get("msg", "")
        if "建议选择器" not in msg:
            continue
        lines = msg.split("\n")
        in_suggestions = False
        for line in lines:
            stripped = line.strip()
            if "建议选择器" in stripped:
                in_suggestions = True
                continue
            if in_suggestions:
                if stripped and any(stripped.startswith(kw) for kw in
                                   ("书籍", "标题", "作者", "正文", "章节", "封面")):
                    suggestions.append(stripped)
                elif stripped.startswith("---") or stripped == "":
                    if suggestions:
                        break
    return suggestions


def apply_auto_fix(source_obj: dict, collector: DebugCollector) -> Optional[dict]:
    """根据错误诊断自动应用修复（方向10.3）。

    薄壳包装：委托给 auto_fixer.auto_fix_error()，接入12种自动修复+5种需用户介入能力。
    支持的自动修复类型：rule_parse/css/url_empty/network/rule_empty/relative_url/
                        css_selector_empty/js_error/http_403/field_missing/syntax_error
    需用户介入类型：need_login/cf_challenge/jar_crash/jar_timeout/behavior_mismatch

    Args:
        source_obj: 当前源对象字典
        collector: DebugCollector实例（含errors和html_sources）

    Returns:
        修复后的source_obj字典，无法修复时返回None
    """
    if not collector.errors:
        return None

    error = collector.errors[0]
    source_json = json.dumps(source_obj, ensure_ascii=False)
    # 提取已收集的HTML用于辅助修复（如CSS选择器修正）
    html = None
    if collector.html_sources:
        # 优先使用失败阶段的HTML
        failed_stage = error.get("failedStage", "")
        html = collector.html_sources.get(failed_stage) or next(iter(collector.html_sources.values()))

    fix_result = auto_fix_error(error, source_json, html=html)

    # 输出修复信息
    for fix in fix_result.get("fixes_applied", []):
        print(f"  [自动修复] {fix}")

    # 需用户介入时输出建议
    verify = fix_result.get("verify_result", {})
    if verify.get("status") == "manual":
        for err in fix_result.get("remaining_errors", []):
            print(f"  [需用户介入] {err}")

    if not fix_result.get("fixes_applied"):
        return None
    return fix_result.get("fixed_source")


def iterative_repair_loop(client: RuleEngineClient, source_obj: dict, key: str,
                         source_type: str, initial_collector: DebugCollector,
                         max_iterations: int = 3) -> tuple:
    """AI多轮迭代修复闭环（方向10.2）。

    JSON去重：直接接收 source_obj 字典。

    Args:
        client: RuleEngineClient实例（已连接）
        source_obj: 当前源对象字典
        key: 搜索关键词
        source_type: 'book' 或 'rss'
        initial_collector: 首次调试的DebugCollector
        max_iterations: 最大迭代次数（含首次）

    Returns:
        (collector, source_obj): 最终的collector和源对象
    """
    current_obj = source_obj
    collector = initial_collector
    last_fixed_json = None

    for iteration in range(max_iterations - 1):
        # 已成功则退出
        if collector.result and collector.result.get("success"):
            break

        # 无错误诊断则退出
        if not collector.errors:
            break

        # 尝试自动修复
        fixed_obj = apply_auto_fix(current_obj, collector)
        if not fixed_obj:
            print(f"[迭代 {iteration+2}/{max_iterations}] 无法自动修复，退出迭代")
            break

        # 相同修复检测：连续两轮修复结果相同，说明修复无效，退出
        fixed_json = json.dumps(fixed_obj, ensure_ascii=False)
        if fixed_json == last_fixed_json:
            print(f"[迭代 {iteration+2}/{max_iterations}] 修复无变化，退出迭代")
            break
        last_fixed_json = fixed_json

        current_obj = fixed_obj
        error_type = collector.errors[0].get("suggestion", {}).get("error_type", "")
        print(f"\n[迭代 {iteration+2}/{max_iterations}] 已应用修复（{error_type}），重新测试...")
        print(f"{'='*60}")

        # 重新调试
        current_json = json.dumps(current_obj, ensure_ascii=False)
        collector = DebugCollector(source_obj=current_obj, site_url=collector.site_url,
                                   cookie_store=collector.cookie_store)
        try:
            if source_type == "book":
                client.debug_book_source(
                    current_json, key,
                    on_log=collector.on_log,
                    on_error=collector.on_error,
                    on_result=collector.on_result
                )
            else:
                client.debug_rss_source(
                    current_json, key,
                    on_log=collector.on_log,
                    on_error=collector.on_error,
                    on_result=collector.on_result
                )
        except Exception as e:
            print(f"[迭代 {iteration+2}] 调试异常: {e}")
            break

    return collector, current_obj


# ==================== 阶段三：数据库查询钩子（3.1-3.5, 3.7-3.9） ====================

def _source_to_cache_dict(source) -> Dict[str, Any]:
    """将 Source ORM 对象转为缓存字典（用于返回数据库查询结果）。

    Args:
        source: legado_client.storage.models.Source ORM 实例

    Returns:
        包含关键字段的字典
    """
    return {
        "id": source.id,
        "source_json": source.source_json,
        "last_test_status": source.last_test_status,
        "last_test_stage": source.last_test_stage,
        "test_detail": source.test_detail,
        "source_url": source.source_url,
        "source_name": source.source_name,
        "domain_key": source.domain_key,
        "source_type": source.source_type,
        "last_test_at": str(source.last_test_at) if source.last_test_at else None,
    }


async def _ensure_db_initialized() -> bool:
    """确保数据库已初始化，返回是否可用。

    3.9: 连接失败时自动降级，不抛异常。
    """
    if config.db_available:
        return True
    try:
        from legado_client.storage.database import init_db
        ok = await init_db()
        if ok:
            from legado_client.storage.database import create_tables
            await create_tables()
        return ok
    except Exception:
        return False


async def _check_database(
    source_obj: dict,
    source_type: str,
    skip_db: bool = False,
    db_only: bool = False,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """查数据库同域名源，返回 (action, cached_result)（3.1）。

    3.9: 数据库不可用时自动降级到 "test" 模式。

    Args:
        source_obj: 源对象字典
        source_type: "book" 或 "rss"
        skip_db: 是否跳过数据库查询（3.7: --skip-db-lookup）
        db_only: 是否仅查数据库（3.8: --db-only）

    Returns:
        (action, cached_result) 元组：
        - "cache_hit_pass": 同域名源已测试通过（3.2）
        - "cache_hit_fail": 同域名源测试未通过或未测试（3.3）
        - "cache_miss": 无同域名源（3.5）
        - "db_only_result": 仅返回数据库结果（3.8: --db-only）
        - "test": 跳过数据库，正常测试（skip_db 或 db 不可用）
    """
    # 3.7: --skip-db-lookup 禁用数据库查询
    if skip_db:
        return "test", None

    # 3.9: 数据库降级 - 不可用时跳过所有数据库操作
    if not config.db_available:
        # 尝试初始化一次
        if not await _ensure_db_initialized():
            return "test", None

    # 提取 domain_key
    source_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", "")
    domain_key = extract_domain_key(source_url)
    if not domain_key:
        return "test", None

    # 查询同域名源
    try:
        from legado_client.storage.repository import find_by_domain
        matches = await find_by_domain(domain_key, source_type)
    except Exception:
        # 3.9: 数据库异常时降级
        return "test", None

    if not matches:
        # 3.5: 未命中
        return "cache_miss", None

    # 找最佳匹配：优先 pass，其次最新测试
    best = matches[0]
    for m in matches:
        if m.last_test_status == "pass":
            best = m
            break

    cached = _source_to_cache_dict(best)

    # 3.8: --db-only 模式 - 仅返回数据库结果，不触发 JVM 测试
    if db_only:
        return "db_only_result", cached

    # 3.2: 命中+测试通过
    if best.last_test_status == "pass":
        return "cache_hit_pass", cached

    # 3.3: 命中+测试失败/未测试
    return "cache_hit_fail", cached


async def _save_debug_result(
    source_obj: dict,
    source_type: str,
    debug_result: Dict[str, Any],
) -> Optional[int]:
    """将调试结果保存到数据库（3.5: 未命中时入库）。

    Args:
        source_obj: 源对象字典
        source_type: "book" 或 "rss"
        debug_result: 调试结果字典

    Returns:
        保存后的 source_id，失败返回 None
    """
    # 3.9: 数据库不可用时跳过
    if not config.db_available:
        return None

    try:
        from legado_client.storage.repository import upsert_source, update_debug_result

        # upsert 源
        source_data = dict(source_obj)
        source_data["source_type"] = source_type
        source = await upsert_source(source_data)

        # 插入调试结果
        success = debug_result.get("success", False)
        status = "pass" if success else "fail"
        confidence = debug_result.get("confidence", "unknown")
        stages = debug_result.get("stages_passed", [])
        failed_stages = debug_result.get("stages_failed", [])

        await update_debug_result(source.id, {
            "status": status,
            "stage": failed_stages[0] if failed_stages else (stages[-1] if stages else None),
            "confidence": confidence,
            "message": json.dumps(debug_result.get("errors", []), ensure_ascii=False)[:500] if not success else None,
            "trigger": "ai",
            "key": debug_result.get("key", ""),
            "search_status": "pass" if "search" in stages else ("fail" if "search" in failed_stages else "skip"),
            "detail_status": "pass" if "detail" in stages else ("fail" if "detail" in failed_stages else "skip"),
            "toc_status": "pass" if "toc" in stages else ("fail" if "toc" in failed_stages else "skip"),
            "content_status": "pass" if "content" in stages else ("fail" if "content" in failed_stages else "skip"),
            "fix_applied": debug_result.get("fix_details", []),
            "duration_ms": int(debug_result.get("elapsed_seconds", 0) * 1000),
            "test_mode": "jar",
        })
        return source.id
    except Exception:
        # 3.9: 数据库异常时静默失败
        return None


async def _update_debug_result(
    source_id: int,
    debug_result: Dict[str, Any],
) -> None:
    """更新已有源的调试结果（3.3: 命中失败源重测后更新）。

    Args:
        source_id: 源 ID
        debug_result: 调试结果字典
    """
    if not config.db_available:
        return

    try:
        from legado_client.storage.repository import update_debug_result

        success = debug_result.get("success", False)
        stages = debug_result.get("stages_passed", [])
        failed_stages = debug_result.get("stages_failed", [])

        await update_debug_result(source_id, {
            "status": "pass" if success else "fail",
            "stage": failed_stages[0] if failed_stages else (stages[-1] if stages else None),
            "confidence": debug_result.get("confidence", "unknown"),
            "message": json.dumps(debug_result.get("errors", []), ensure_ascii=False)[:500] if not success else None,
            "trigger": "ai",
            "search_status": "pass" if "search" in stages else ("fail" if "search" in failed_stages else "skip"),
            "detail_status": "pass" if "detail" in stages else ("fail" if "detail" in failed_stages else "skip"),
            "toc_status": "pass" if "toc" in stages else ("fail" if "toc" in failed_stages else "skip"),
            "content_status": "pass" if "content" in stages else ("fail" if "content" in failed_stages else "skip"),
            "fix_applied": debug_result.get("fix_details", []),
            "duration_ms": int(debug_result.get("elapsed_seconds", 0) * 1000),
            "test_mode": "jar",
        })
    except Exception:
        pass


def _build_result_from_cache(
    cached: Dict[str, Any],
    source_obj: dict,
) -> Dict[str, Any]:
    """从数据库缓存构建结果字典（3.2: 命中已通过源时使用）。"""
    try:
        cached_source = json.loads(cached["source_json"]) if isinstance(cached["source_json"], str) else cached["source_json"]
    except (json.JSONDecodeError, TypeError):
        cached_source = source_obj

    return {
        "success": cached["last_test_status"] == "pass",
        "source_name": cached.get("source_name", ""),
        "source_url": cached.get("source_url", ""),
        "domain_key": cached.get("domain_key", ""),
        "stages_passed": [],
        "stages_failed": [],
        "errors": [],
        "confidence": "high",
        "db_action": "cache_hit_pass",
        "from_cache": True,
        "cached_source": cached_source,
        "cached_test_detail": cached.get("test_detail"),
        "fix_details": [],
    }


def _build_result_from_collector(
    collector: DebugCollector,
    source_obj: dict,
    elapsed: float,
    db_action: str = "test",
    fix_details: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """从 DebugCollector 构建结构化结果字典。"""
    site_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl") or ""
    success = collector.result.get("success", False) if collector.result else False
    summary = collector.result.get("summary", {}) if collector.result else {}

    # 计算可信度
    if collector.result and collector.source_obj:
        test_result = {
            "success": success,
            "stages": summary.get("stages", ""),
        }
        eval_result = evaluate_confidence(collector.source_obj, test_result)
        confidence = eval_result.get("level", "unknown").lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "medium" if success else "low"
    elif collector.result:
        if success:
            confidence = "medium" if collector.unverifiable_items else "high"
        else:
            confidence = "low"
    else:
        confidence = "unknown"

    return {
        "success": success,
        "source_name": source_obj.get("bookSourceName") or source_obj.get("sourceName", ""),
        "source_url": site_url,
        "stages_passed": collector.stages_passed,
        "stages_failed": collector.stages_failed,
        "errors": collector.errors,
        "summary": summary,
        "confidence": confidence,
        "elapsed_seconds": round(elapsed, 2),
        "db_action": db_action,
        "from_cache": False,
        "fix_details": fix_details or [],
    }


# ==================== 主调试流程 ====================

def _detect_type_from_obj(source_obj: dict) -> str:
    """从源对象字典检测源类型（JSON去重：不再 json.loads）。

    检测优先级：
    1. bookSourceUrl（书源特有字段）→ book
    2. sourceUrl + ruleArticles（订阅源特有组合）→ rss
    3. ruleSearch（两者都有，但书源更常见）→ book
    修复: 新订阅源同时有 ruleSearch 和 sourceUrl，先检查 sourceUrl 避免误判为书源
    """
    if "bookSourceUrl" in source_obj:
        return "book"
    if "sourceUrl" in source_obj and "ruleArticles" in source_obj:
        return "rss"
    if "sourceUrl" in source_obj:
        return "rss"
    if "ruleSearch" in source_obj:
        return "book"
    return "book"


def _execute_jvm_test(args, source_obj: dict, source_type: str) -> Tuple[DebugCollector, dict, float]:
    """执行 JVM 端到端测试，返回 (collector, final_source_obj, elapsed)。

    不调用 sys.exit()，用于 run_and_return() 的内部调用。
    """
    source_json = json.dumps(source_obj, ensure_ascii=False)
    site_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl") or ""
    _cookie_store: dict = {}

    collector = DebugCollector(source_obj=source_obj, site_url=site_url,
                               cookie_store=_cookie_store)
    elapsed = 0.0

    try:
        with RuleEngineClient(timeout=args.timeout) as client:
            ping_result = client.ping()
            if not ping_result.get("ok"):
                raise RuntimeError(f"JVM ping failed: {ping_result.get('error', 'unknown')}")

            start_time = time.time()

            if source_type == "book":
                client.debug_book_source(
                    source_json, args.key,
                    on_log=collector.on_log,
                    on_error=collector.on_error,
                    on_result=collector.on_result
                )
            else:
                client.debug_rss_source(
                    source_json, args.key,
                    on_log=collector.on_log,
                    on_error=collector.on_error,
                    on_result=collector.on_result
                )

            elapsed = time.time() - start_time

            # 多轮迭代修复
            _should_iterate = (
                args.max_iterations > 1
                and collector.errors
                and (not collector.result or not collector.result.get("success"))
            )
            if _should_iterate:
                collector, source_obj = iterative_repair_loop(
                    client, source_obj, args.key, source_type,
                    collector, args.max_iterations
                )

    except FileNotFoundError:
        collector.errors.append({
            "msg": "JAR 仿真服务端不可用", "stackTrace": None, "failedStage": None,
            "suggestion": None,
        })
    except RuntimeError as e:
        collector.errors.append({
            "msg": str(e), "stackTrace": None, "failedStage": None,
            "suggestion": None,
        })
    except Exception as e:
        collector.errors.append({
            "msg": f"严重错误: {e}", "stackTrace": None, "failedStage": None,
            "suggestion": None,
        })

    return collector, source_obj, elapsed


async def run_and_return(
    args,
    source_obj: dict,
    skip_db: bool = False,
    db_only: bool = False,
) -> Dict[str, Any]:
    """异步调试入口：返回结构化结果（不调用 sys.exit）。

    相比 run()，增加了数据库查询能力（3.1-3.5）：
    - 调试前查数据库同域名源（3.1）
    - 命中已通过源则跳过测试（3.2）
    - 命中失败源则重测+自动修复+更新数据库（3.3）
    - 修复失败标记需AI介入（3.4）
    - 未命中则正常测试后入库（3.5）

    Args:
        args: 参数对象（含 key/stage/timeout/max_iterations 等）
        source_obj: 源对象字典
        skip_db: 是否跳过数据库查询（3.7: --skip-db-lookup）
        db_only: 是否仅查数据库（3.8: --db-only）

    Returns:
        结构化结果字典，包含：
        - success: bool
        - stages_passed / stages_failed: list
        - errors: list
        - confidence: str
        - db_action: str（哪个数据库分支）
        - from_cache: bool
        - fix_details: list（修复详情）
        - needs_ai_intervention: bool（3.4: 修复失败时标记）
    """
    source_type = _detect_type_from_obj(source_obj)
    site_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", "")

    # 预校验：字段完整性
    validator = SourceValidator(source_obj, source_type)
    v_result = validator.validate()
    if not v_result["valid"]:
        return {
            "success": False,
            "stage": "precheck",
            "check_type": "field_integrity",
            "errors": [e.get("message", str(e)) for e in v_result["errors"]],
            "db_action": "test",
            "from_cache": False,
            "fix_details": [],
            "needs_ai_intervention": False,
        }

    # 预校验：规则语法
    prechecker = RulePrecheck(source_obj, source_type)
    p_result = prechecker.precheck()
    if not p_result["valid"]:
        return {
            "success": False,
            "stage": "precheck",
            "check_type": "rule_syntax",
            "errors": [e.get("message", str(e)) for e in p_result["errors"]],
            "db_action": "test",
            "from_cache": False,
            "fix_details": [],
            "needs_ai_intervention": False,
        }

    # 3.1: 数据库查询
    action, cached = await _check_database(source_obj, source_type, skip_db, db_only)

    # 3.2: 命中+测试通过 → 直接返回缓存结果
    if action == "cache_hit_pass":
        print(f"数据库命中已通过源，跳过测试 (domain={cached['domain_key']}, "
              f"source={cached['source_name']})")
        return _build_result_from_cache(cached, source_obj)

    # 3.8: --db-only 模式 - 仅返回数据库结果
    if action == "db_only_result":
        if cached:
            print(f"[--db-only] 数据库查询结果: domain={cached['domain_key']}, "
                  f"status={cached['last_test_status']}, source={cached['source_name']}")
            return _build_result_from_cache(cached, source_obj)
        else:
            return {
                "success": False,
                "db_action": "db_only_result",
                "from_cache": False,
                "message": "数据库中未找到同域名源",
                "fix_details": [],
                "needs_ai_intervention": False,
            }

    # 3.3: 命中+测试失败/未测试 → 取出源JSON → 测试 → 修复 → 重测 → 更新数据库
    if action == "cache_hit_fail":
        print(f"数据库命中未通过源 (domain={cached['domain_key']}, "
              f"status={cached['last_test_status']})，重新测试...")

        # 使用数据库中的源 JSON 进行重测
        test_obj = source_obj
        try:
            db_source = json.loads(cached["source_json"]) if isinstance(cached["source_json"], str) else cached["source_json"]
            if db_source:
                test_obj = db_source
        except (json.JSONDecodeError, TypeError):
            pass

        # 执行 JVM 测试
        collector, final_obj, elapsed = _execute_jvm_test(args, test_obj, source_type)

        # 测试成功 → 更新数据库
        if collector.result and collector.result.get("success"):
            confidence = collector.generate_report()
            result = _build_result_from_collector(collector, final_obj, elapsed,
                                                  db_action="cache_hit_fail")
            await _update_debug_result(cached["id"], result)
            return result

        # 测试失败 → 触发 auto_fixer
        print("重测失败，触发自动修复...")
        fix_details: List[Dict[str, Any]] = []
        fixed_obj = apply_auto_fix(test_obj, collector)
        if fixed_obj:
            # 修复后重测
            collector2, final_obj2, elapsed2 = _execute_jvm_test(args, fixed_obj, source_type)

            if collector2.result and collector2.result.get("success"):
                # 修复成功
                confidence = collector2.generate_report()
                fix_details.append({
                    "fix_type": "auto_fix",
                    "stage": collector.errors[0].get("failedStage", "") if collector.errors else "",
                    "before": json.dumps(test_obj, ensure_ascii=False)[:200],
                    "after": json.dumps(fixed_obj, ensure_ascii=False)[:200],
                    "diff": "; ".join(str(e) for e in collector.errors[:3]),
                    "success": True,
                })
                result = _build_result_from_collector(collector2, final_obj2, elapsed2,
                                                      db_action="cache_hit_fail",
                                                      fix_details=fix_details)
                await _update_debug_result(cached["id"], result)
                return result

        # 3.4: 修复失败 → 标记需 AI 介入
        print("自动修复失败，标记需 AI 介入")
        error_msgs = [e.get("msg", "") for e in collector.errors[:3]]
        suggestions = []
        for err in collector.errors:
            sug = err.get("suggestion")
            if sug:
                suggestions.append(sug.get("summary", ""))

        fix_details.append({
            "fix_type": "auto_fix",
            "stage": collector.errors[0].get("failedStage", "") if collector.errors else "",
            "before": json.dumps(test_obj, ensure_ascii=False)[:200],
            "after": json.dumps(fixed_obj, ensure_ascii=False)[:200] if fixed_obj else "",
            "diff": "; ".join(error_msgs),
            "success": False,
        })

        # 更新数据库标记失败
        fail_result = _build_result_from_collector(collector, test_obj, elapsed,
                                                    db_action="cache_hit_fail",
                                                    fix_details=fix_details)
        await _update_debug_result(cached["id"], fail_result)

        return {
            **fail_result,
            "needs_ai_intervention": True,
            "fix_suggestions": suggestions,
            "error_diagnosis": error_msgs,
        }

    # 3.5 / "test": 正常流程
    collector, final_obj, elapsed = _execute_jvm_test(args, source_obj, source_type)
    confidence = collector.generate_report()
    result = _build_result_from_collector(collector, final_obj, elapsed,
                                          db_action=action)

    # 3.5: 未命中 → 结果入库
    if action == "cache_miss":
        source_id = await _save_debug_result(source_obj, source_type, result)
        if source_id:
            print(f"调试结果已入库 (source_id={source_id})")

    return result


def _dict_to_debug_result(result: Dict[str, Any], source_obj: dict) -> DebugResultData:
    """将 run_and_return 的字典结果转换为 DebugResultData。"""
    source_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl", "")
    source_name = source_obj.get("bookSourceName") or source_obj.get("sourceName", "")
    source_type = _detect_type_from_obj(source_obj)
    stages_passed = result.get("stages_passed", [])
    stages_failed = result.get("stages_failed", [])
    elapsed = result.get("elapsed_seconds", 0)
    errors = result.get("errors", [])

    def _stage_status(stage: str) -> str:
        if stage in stages_passed:
            return "pass"
        if stage in stages_failed:
            return "fail"
        return "skip"

    return DebugResultData(
        source_url=source_url,
        source_name=source_name,
        source_type=source_type,
        status="pass" if result.get("success") else "fail",
        stage=stages_failed[0] if stages_failed else (stages_passed[-1] if stages_passed else ""),
        message=errors[0].get("msg", "") if errors else "",
        search_status=_stage_status("search"),
        detail_status=_stage_status("detail"),
        toc_status=_stage_status("toc"),
        content_status=_stage_status("content"),
        confidence=result.get("confidence", ""),
        test_mode="jar",
        device_jar_diff=None,
        fix_detail=result.get("fix_details"),
        duration_ms=int(elapsed * 1000),
        source_json=json.dumps(source_obj, ensure_ascii=False),
    )


async def run_and_return_v2(
    args,
    source_obj: dict,
    skip_db: bool = False,
    db_only: bool = False,
) -> DebugResultData:
    """3.10: 返回 DebugResultData 的调试入口。

    内部委托给 run_and_return()，将字典结果转换为 DebugResultData。
    供 DebugOrchestrator 使用。

    Args:
        args: 参数对象
        source_obj: 源对象字典
        skip_db: 是否跳过数据库查询
        db_only: 是否仅查数据库

    Returns:
        DebugResultData: 调试结果数据
    """
    result = await run_and_return(args, source_obj, skip_db=skip_db, db_only=db_only)
    return _dict_to_debug_result(result, source_obj)


def run(args, source_obj: dict) -> None:
    """主调试流程。

    JSON去重：source_obj 由调用方(debug-source.py)入口解析一次，此处直接使用。
    --timeout 参数：通过 args.timeout 传递给 RuleEngineClient。
    --skip-db-lookup / --db-only：3.7/3.8 新增参数，使用 getattr 安全读取。
    """
    source_json = json.dumps(source_obj, ensure_ascii=False)

    # 检测源类型（JSON去重：直接用 source_obj）
    source_type = _detect_type_from_obj(source_obj)

    # 3.7/3.8: 安全读取新增参数（向后兼容）
    skip_db = getattr(args, 'skip_db_lookup', False)
    db_only = getattr(args, 'db_only', False)

    print(f"源类型: {'书源' if source_type == 'book' else '订阅源'}")
    print(f"调试关键词: {args.key}")
    print(f"调试阶段: {args.stage}")

    # 预校验：字段完整性
    validator = SourceValidator(source_obj, source_type)
    v_result = validator.validate()
    if v_result["warnings"]:
        for w in v_result["warnings"]:
            print(f"  ⚠ 预校验警告: {w['message']}")
    if not v_result["valid"]:
        print("❌ 预校验失败: 字段完整性校验未通过")
        for e in v_result["errors"]:
            print(f"  ✗ {e['message']}")
        # 输出结构化错误，供 AI agent 解析后返回 Phase 2 修复规则
        structured_error = {
            "success": False,
            "stage": "precheck",
            "check_type": "field_integrity",
            "errors": [e.get("message", str(e)) for e in v_result["errors"]],
            "suggestion": "返回 Phase 2 修复规则后重试"
        }
        print(f"\n[PRECHECK_FAILED] {json.dumps(structured_error, ensure_ascii=False)}")
        sys.exit(1)

    # 预校验：规则语法
    prechecker = RulePrecheck(source_obj, source_type)
    p_result = prechecker.precheck()
    if p_result["warnings"]:
        for w in p_result["warnings"]:
            print(f"  ⚠ 规则语法警告: {w['message']}")
    if not p_result["valid"]:
        print("❌ 预校验失败: 规则语法校验未通过")
        for e in p_result["errors"]:
            print(f"  ✗ {e['message']}")
        # 输出结构化错误，供 AI agent 解析后返回 Phase 2 修复规则
        structured_error = {
            "success": False,
            "stage": "precheck",
            "check_type": "rule_syntax",
            "errors": [e.get("message", str(e)) for e in p_result["errors"]],
            "suggestion": "返回 Phase 2 修复规则后重试"
        }
        print(f"\n[PRECHECK_FAILED] {json.dumps(structured_error, ensure_ascii=False)}")
        sys.exit(1)

    site_url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl") or ""

    # 3.1: 数据库查询（同步包装，3.9: 降级时静默跳过）
    db_action = "test"
    db_cached = None
    if not skip_db and config.db_available:
        try:
            db_action, db_cached = asyncio.run(
                _check_database(source_obj, source_type, skip_db, db_only)
            )
        except Exception:
            db_action = "test"

    # 3.2: 命中已通过源 → 跳过测试
    if db_action == "cache_hit_pass" and db_cached:
        print(f"数据库命中已通过源，跳过测试 (domain={db_cached['domain_key']}, "
              f"source={db_cached['source_name']})")
        sys.exit(0)

    # 3.8: --db-only 模式 → 仅输出数据库信息
    if db_action == "db_only_result":
        if db_cached:
            print(f"[--db-only] 数据库查询结果:")
            print(f"  域名: {db_cached['domain_key']}")
            print(f"  源名: {db_cached['source_name']}")
            print(f"  状态: {db_cached['last_test_status']}")
            print(f"  失败阶段: {db_cached.get('last_test_stage', 'N/A')}")
            if db_cached.get('test_detail'):
                print(f"  详情: {json.dumps(db_cached['test_detail'], ensure_ascii=False)[:500]}")
        else:
            print("[--db-only] 数据库中未找到同域名源")
        sys.exit(0)

    # 3.3: 命中失败源 → 用数据库中的源 JSON 重测
    test_source_obj = source_obj
    if db_action == "cache_hit_fail" and db_cached:
        print(f"数据库命中未通过源 (domain={db_cached['domain_key']}, "
              f"status={db_cached['last_test_status']})，重新测试...")
        try:
            db_source = json.loads(db_cached["source_json"]) if isinstance(db_cached["source_json"], str) else db_cached["source_json"]
            if db_source:
                test_source_obj = db_source
                source_json = json.dumps(test_source_obj, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass

    # ==================== 阶段七集成（7.1-7.9） ====================
    _cookie_store: dict = {}

    # 7.5: Cookie 持久化管理
    if _COOKIE_MANAGER_AVAILABLE:
        try:
            store = PersistentCookieStore()
            _cookie_store = store.load_all()
            if _cookie_store:
                print(f"Cookie 管理: 已加载 {len(_cookie_store)} 个域名的持久化 Cookie")
            if args.import_cookies:
                imported = import_from_browser(args.import_cookies)
                if imported:
                    for domain, cookies in imported.items():
                        store.save(domain, cookies)
                    _cookie_store = store.load_all()
                    print(f"Cookie 管理: 从 {args.import_cookies} 导入 {len(imported)} 个域名")
                else:
                    print(f"Cookie 管理: {args.import_cookies} 解析失败或为空")
        except Exception as e:
            print(f"Cookie 管理: 加载异常 {e}")

    # 7.9: 智能HTTP客户端
    _smart_client = None
    if _SMART_HTTP_CLIENT_AVAILABLE and (args.proxy or args.ua):
        try:
            _smart_client = SmartHttpClient(proxy=args.proxy, ua=args.ua)
            if args.proxy:
                print(f"智能HTTP客户端: 已启用代理 {args.proxy}")
            if args.ua:
                print(f"智能HTTP客户端: 已设置自定义 UA")
        except ImportError as e:
            print(f"智能HTTP客户端: 不可用 ({e})")

    # 7.8: 知识库匹配
    knowledge_hit = False
    if _KNOWLEDGE_MATCHER_AVAILABLE and site_url:
        try:
            hit = match_site_features(site_url, "")
            if hit:
                knowledge_hit = True
                print(f"知识库匹配: 命中相似案例 (相似度 {hit.get('similarity', 0)})")
                if hit.get('solution'):
                    print(f"  参考方案: {hit['solution'][:200]}")
            else:
                print(f"知识库匹配: 无相似案例")
        except Exception as e:
            print(f"知识库匹配: 异常 {e}")

    # 方向4: 经验闭环 - 知识库未命中时用文件搜索降级
    if not knowledge_hit and not args.no_experience:
        source_name = source_obj.get("bookSourceName") or source_obj.get("sourceName") or ""
        exp_result = search_experience(site_url, source_name)
        if exp_result != "无相似案例":
            print(f"经验检索: {exp_result}")

    # 7.4: 加密自动分析（JSON去重：直接传 source_obj）
    _run_crypto_analysis(test_source_obj)

    # 7.7: 进度反馈 - 调试启动
    if _INTERACTIVE_GUIDE_AVAILABLE:
        report_progress("调试启动", 0, "准备启动 JVM 端到端调试")

    print(f"{'='*60}\n")

    # 启动 JVM 服务端
    collector = DebugCollector(source_obj=test_source_obj, site_url=site_url,
                               cookie_store=_cookie_store)

    try:
        with RuleEngineClient(timeout=args.timeout) as client:
            # JVM 可用性检测（ping）
            ping_result = client.ping()
            if not ping_result.get("ok"):
                raise RuntimeError(f"JVM ping failed: {ping_result.get('error', 'unknown')}")

            start_time = time.time()

            # 7.7: 进度反馈 - 端到端调试开始
            if _INTERACTIVE_GUIDE_AVAILABLE:
                report_progress("端到端调试", 20, "开始调用 JVM 调试")

            if source_type == "book":
                client.debug_book_source(
                    source_json, args.key,
                    on_log=collector.on_log,
                    on_error=collector.on_error,
                    on_result=collector.on_result
                )
            else:
                client.debug_rss_source(
                    source_json, args.key,
                    on_log=collector.on_log,
                    on_error=collector.on_error,
                    on_result=collector.on_result
                )

            elapsed = time.time() - start_time
            print(f"\n调试耗时: {elapsed:.2f}s")

            # 方向10：多轮迭代修复闭环
            _should_iterate = (
                args.max_iterations > 1
                and collector.errors
                and (not collector.result or not collector.result.get("success"))
            )
            if _should_iterate:
                print(f"\n{'='*60}")
                print(f"方向10：多轮迭代修复闭环（最大 {args.max_iterations} 轮）")
                print(f"{'='*60}")
                collector, source_obj = iterative_repair_loop(
                    client, test_source_obj, args.key, source_type,
                    collector, args.max_iterations
                )
                source_json = json.dumps(source_obj, ensure_ascii=False)

            # 生成验证报告（集成 evaluate_confidence）
            confidence = collector.generate_report()

            # 方向3：结构化输出 -- 导出JSON报告（JSON去重：直接用 source_obj）
            if args.output:
                report = {
                    "source_name": source_obj.get("bookSourceName") or source_obj.get("sourceName", ""),
                    "source_url": site_url,
                    "success": collector.result.get("success", False) if collector.result else False,
                    "stages_passed": collector.stages_passed,
                    "stages_failed": collector.stages_failed,
                    "errors": collector.errors,
                    "summary": collector.result.get("summary", {}) if collector.result else {},
                    "confidence": confidence,
                    "elapsed_seconds": round(elapsed, 2),
                }
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"\n结构化报告已导出: {args.output}")

            # 增强验证报告（JSON去重：直接传 source_obj）
            print_enhanced_report(source_obj)

            # 方向4: 经验闭环 - 测试后提取经验并写入（JSON去重：直接用 source_obj）
            if not args.no_experience and collector.result:
                test_result = {
                    "success": collector.result.get("success", False),
                    "stages": collector.result.get("summary", {}).get("stages", ""),
                }
                fix_info = {"error_type": "", "fix_method": "自动调试"}
                if collector.errors:
                    suggestion = collector.errors[0].get("suggestion", {})
                    fix_info["error_type"] = suggestion.get("error_type", "")
                    fix_info["fix_method"] = suggestion.get("category", "")
                try:
                    exp_mgr = ExperienceManager()
                    # 提取经验要素
                    debug_result_for_exp = {
                        "success": test_result["success"],
                        "error_type": fix_info["error_type"],
                        "fix_method": fix_info["fix_method"],
                        "fix_applied": bool(fix_info["error_type"]),
                    }
                    experience_draft = exp_mgr.extract(source_obj, debug_result_for_exp, confidence)
                    # 写入 pending 文件
                    exp_mgr.write_pending(source_obj, fix_info, test_result)
                    # 输出 [EXPERIENCE_PENDING] MCP 指令到 stdout，供 AI agent 消费
                    mcp_instruction = exp_mgr.write_to_basic_memory(experience_draft)
                    print(f"\n[EXPERIENCE_PENDING] {json.dumps(mcp_instruction, ensure_ascii=False)}")
                except Exception as e:
                    print(f"  ⚠ 经验写入失败: {e}")

            # 3.3/3.5: 数据库结果更新
            if config.db_available and not skip_db:
                try:
                    db_result = {
                        "success": collector.result.get("success", False) if collector.result else False,
                        "stages_passed": collector.stages_passed,
                        "stages_failed": collector.stages_failed,
                        "errors": collector.errors,
                        "confidence": confidence,
                        "elapsed_seconds": elapsed,
                        "key": args.key,
                    }
                    if db_action == "cache_hit_fail" and db_cached:
                        asyncio.run(_update_debug_result(db_cached["id"], db_result))
                    elif db_action == "cache_miss":
                        source_id = asyncio.run(_save_debug_result(
                            test_source_obj, source_type, db_result))
                        if source_id:
                            print(f"调试结果已入库 (source_id={source_id})")
                except Exception:
                    pass  # 3.9: 数据库异常时静默失败

            # 退出码
            if collector.result and collector.result.get("success"):
                sys.exit(0)
            elif collector.errors:
                sys.exit(1)  # 部分失败
            else:
                sys.exit(2)  # 严重错误

    except FileNotFoundError as e:
        # JVM JAR 缺失 → 自动降级到 Python 验证模式（REQ-S05）
        print(f"[WARN] JAR 仿真服务端不可用，降级到 Python 模式")
        print(f"  原因: {e}")
        print("  覆盖率 35-40%，可信度 medium，建议用 JAR 复验")
        _run_python_fallback(args, source_type)
    except RuntimeError as e:
        # JVM 启动失败 → 自动降级到 Python 验证模式（REQ-S05）
        err_msg = str(e)
        if any(kw in err_msg for kw in ("Java not found", "failed to start", "unexpected status", "ping failed", "startup timeout")):
            print(f"[WARN] JAR 仿真服务端不可用，降级到 Python 模式")
            print(f"  原因: {e}")
            print("  覆盖率 35-40%，可信度 medium，建议用 JAR 复验")
            _run_python_fallback(args, source_type)
        else:
            print(f"严重错误: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(2)
    except Exception as e:
        print(f"严重错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


def _run_python_fallback(args, source_type):
    """JVM 不可用时的 Python 降级模式：自动调用 verify-source.py（REQ-S05）"""
    import subprocess
    verify_script = os.path.join(str(config.scripts_dir), "verify-source.py")
    if not os.path.exists(verify_script):
        print(f"  ✗ 降级失败: verify-source.py 不存在")
        sys.exit(3)
    try:
        result = subprocess.run(
            [sys.executable, verify_script, "--source-json", args.source, "--type", source_type],
            capture_output=True, text=True, timeout=60
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"  ✗ 降级失败: {e}")
        sys.exit(3)
