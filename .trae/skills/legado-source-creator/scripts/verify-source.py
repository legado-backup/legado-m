#!/usr/bin/env python3
"""固化源完整性验证脚本 - 支持 JVM/Python 双模式"""
import argparse
import json
import os
import sys

# HtmlFetcher 集成（html_fetcher 已迁移至 legado_client/utils/）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from legado_client.utils.html_fetcher import HtmlFetcher
    _HTML_FETCHER_AVAILABLE = True
except ImportError:
    _HTML_FETCHER_AVAILABLE = False

# 必填字段
RSS_REQUIRED = ["sourceUrl", "sourceName", "type", "ruleArticles", "ruleTitle", "ruleLink"]
RSS_RECOMMENDED = ["sourceIcon", "sourceGroup", "ruleContent", "ruleNextPage", "enableJs", "header"]
BOOK_REQUIRED = ["bookSourceUrl", "bookSourceName", "bookSourceType", "ruleSearchUrl", "ruleBookName", "ruleBookUrl"]
BOOK_RECOMMENDED = ["bookSourceIcon", "bookSourceGroup", "ruleBookContent", "ruleTocUrl", "enableJs", "header"]


def _init_jvm_client(jar_path=None):
    """初始化 JVM 客户端（使用共享模块）"""
    try:
        tools_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from legado_client.utils.jvm_helpers import init_jvm_client
        return init_jvm_client(jar_path=jar_path)
    except ImportError:
        # 降级：jvm_helpers 不可用时使用 legado_client 包内的 rule_engine_client
        try:
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from legado_client.client.rule_engine_client import RuleEngineClient
            client = RuleEngineClient(jar_path=jar_path)
            client.start()
            return client, True
        except Exception as e:
            print(f"WARNING: JVM 不可用，降级到纯 Python(正则) 验证: {e}", file=sys.stderr)
            return None, False


def check_es6_jvm(client, js_code):
    """JVM 路径 - 使用 Rhino 实际执行 JS 代码检测 ES6 语法"""
    # 用 Rhino 尝试解析 JS 代码，Rhino 不支持 ES6 会报错
    test_js = f"""
    try {{
        eval({json.dumps(js_code)});
        'ES5_OK';
    }} catch(e) {{
        'ES6_ERROR:' + e.message;
    }}
    """
    result = client.eval_js(test_js)
    if result.get("ok"):
        rv = result.get("result", "")
        if "ES6_ERROR" in str(rv):
            return True, str(rv)  # ES6 语法检测到
        return False, rv  # ES5 兼容
    return None, result.get("error", "eval failed")


def check_es6_python(js_code):
    """Python 降级路径 - 使用正则匹配检测 ES6 语法"""
    es6_keywords = ["let ", "const ", "=>", "${", "for...of"]
    found = []
    for kw in es6_keywords:
        if kw in js_code:
            found.append(kw.strip())
    if found:
        return True, f"检测到 ES6 关键字: {', '.join(found)}"
    return False, "未检测到 ES6 关键字"


def identify_scenarios(source, source_type="rss"):
    """识别测试脚本能力不足的场景（分页加载/多页目录/动态加载正文）"""
    scenarios = []
    if source_type == "book":
        rule_search = source.get("ruleSearch", {})
        rule_toc = source.get("ruleToc", {})
        rule_content = source.get("ruleContent", {})
        search_url = source.get("searchUrl", "")
        if "{{page}}" in search_url or rule_search.get("nextPage"):
            scenarios.append({"scenario": "分页加载", "field": "ruleSearch.nextPage / searchUrl",
                              "capability": "limited", "note": "Python仿真器不支持分页迭代，需JVM端到端调试"})
        if rule_toc.get("nextTocUrl") or rule_toc.get("nextPage"):
            scenarios.append({"scenario": "多页目录", "field": "ruleToc.nextTocUrl / nextPage",
                              "capability": "limited", "note": "Python仿真器不支持多页目录合并，需JVM端到端调试"})
        content_rule = rule_content.get("content", "")
        if isinstance(content_rule, str) and ("@js:" in content_rule or "<js>" in content_rule or "ajax" in content_rule.lower()):
            scenarios.append({"scenario": "动态加载正文", "field": "ruleContent.content",
                              "capability": "limited", "note": "正文含JS/AJAX调用，Python仿真器无法执行，需JVM端到端调试"})
    elif source_type == "rss":
        rule_articles = source.get("ruleArticles", {})
        rule_content = source.get("ruleContent", {})
        if rule_articles.get("nextPage"):
            scenarios.append({"scenario": "分页加载", "field": "ruleArticles.nextPage",
                              "capability": "limited", "note": "Python仿真器不支持分页迭代，需JVM端到端调试"})
        content_rule = rule_content.get("content", "")
        if isinstance(content_rule, str) and ("@js:" in content_rule or "<js>" in content_rule or "ajax" in content_rule.lower()):
            scenarios.append({"scenario": "动态加载正文", "field": "ruleContent.content",
                              "capability": "limited", "note": "正文含JS/AJAX调用，Python仿真器无法执行，需JVM端到端调试"})
    return scenarios


def validate_source(source, source_type="rss", jvm_client=None, jvm_available=False, fetch_html=False, cms_type=None):
    errors = []
    warnings = []
    info = []
    html_source = 'none'

    required = RSS_REQUIRED if source_type == "rss" else BOOK_REQUIRED
    recommended = RSS_RECOMMENDED if source_type == "rss" else BOOK_RECOMMENDED

    # 检查必填字段
    for field in required:
        val = source.get(field)
        if not val or (isinstance(val, str) and not val.strip()):
            errors.append(f"缺少必填字段: {field}")

    # 检查推荐字段
    for field in recommended:
        val = source.get(field)
        if not val or (isinstance(val, str) and not val.strip()):
            warnings.append(f"缺少推荐字段: {field}")

    # 检查常见陷阱
    if source.get("enableJs") and not source.get("header"):
        warnings.append("enableJs=true 但无 header，可能需要配置 UA")

    if source_type == "rss":
        if source.get("type") == 2 and not source.get("ruleContent"):
            errors.append("type=2(视频) 但无 ruleContent，视频 URL 无法提取")

        if source.get("loginCheckJs") and not source.get("loginCheckJs", "").rstrip().endswith("result"):
            errors.append("loginCheckJs 未以 result 结尾，可能导致 NPE 崩溃 (#12)")

        if source.get("searchUrl") and "{{page}}" not in source.get("searchUrl", ""):
            warnings.append("searchUrl 缺少 {{page}} 分页参数 (#45)")

    # 扩展陷阱检查（与79条陷阱清单对齐）
    # #42: sourceIcon 域名应与 sourceUrl 同域，或用 data:image
    source_icon = source.get("sourceIcon") or source.get("bookSourceIcon") or ""
    if source_icon and not source_icon.startswith("data:"):
        try:
            from urllib.parse import urlparse
            icon_host = urlparse(source_icon).netloc
            src_host = urlparse(source.get("sourceUrl", source.get("bookSourceUrl", ""))).netloc
            if icon_host and src_host and icon_host != src_host:
                warnings.append(f"sourceIcon 域名({icon_host})与 sourceUrl 域名({src_host})不一致 (#42)")
        except Exception:
            pass

    # #58: ruleContent 中 </js> 后跟 HTML 会被当 CSS 选择器解析
    rc = source.get("ruleContent", {})
    rc_content = rc.get("content", "") if isinstance(rc, dict) else (rc if isinstance(rc, str) else "")
    if isinstance(rc_content, str) and "</js>" in rc_content:
        after_js = rc_content.split("</js>", 1)[1].strip()
        if after_js and not after_js.startswith(("@js:", "<js>", "@CSS:")):
            errors.append("ruleContent 中 </js> 后跟 HTML，会被当 CSS 选择器解析 (#58)")

    # #72: searchUrl 的 <js> 块中不能用 {{key}}（AnalyzeUrl 先执行 JS 再替换模板变量）
    search_url = source.get("searchUrl") or source.get("ruleSearchUrl") or ""
    if isinstance(search_url, str) and "<js>" in search_url and "</js>" in search_url:
        js_part = search_url.split("<js>", 1)[1].split("</js>", 1)[0]
        if "{{key}}" in js_part:
            errors.append("searchUrl 的 <js> 块中使用了 {{key}}，AnalyzeUrl 先执行 JS 再替换模板变量 (#72)")

    # 检查 JS 规则中的 ES6 语法
    js_fields = ["ruleContent", "ruleImage", "ruleTitle", "ruleDescription", "loginCheckJs", "header"]
    for field in js_fields:
        val = source.get(field, "")
        if isinstance(val, str) and (val.startswith("@js:") or val.startswith("<js>")):
            js_code = val[4:] if val.startswith("@js:") else val[4:-5] if val.endswith("</js>") else val[5:]

            if jvm_available and jvm_client:
                # JVM 路径 - Rhino 实际执行检测
                is_es6, detail = check_es6_jvm(jvm_client, js_code)
                if is_es6:
                    errors.append(f"{field} 使用了 ES6 语法(Rhino验证): {detail}")
                else:
                    info.append(f"{field} JS 语法通过 Rhino 验证")
            else:
                # Python 降级路径 - 正则匹配
                is_es6, detail = check_es6_python(js_code)
                if is_es6:
                    errors.append(f"{field} 使用了 ES6 语法(正则检测): {detail}")

    # HTML 来源检测（通过 HtmlFetcher 回退链）
    source_url = source.get("sourceUrl", source.get("bookSourceUrl", ""))
    if fetch_html and _HTML_FETCHER_AVAILABLE and source_url:
        try:
            fetcher = HtmlFetcher()
            result = fetcher.fetch(source_url, cms_type=cms_type)
            if result.ok:
                html_source = result.source
                info.append(f"HTML 获取成功，来源: {result.source}")
                # 检测 CF 保护
                if HtmlFetcher._is_cf_challenge(result.html):
                    warnings.append("网站受 Cloudflare 保护，直接访问可能失败")
            else:
                html_source = 'failed'
                warnings.append(f"HTML 获取失败，回退日志: {'; '.join(result.log[-2:])}")
        except Exception as e:
            html_source = 'failed'
            warnings.append(f"HtmlFetcher 调用异常: {str(e)[:80]}")

    scenarios = identify_scenarios(source, source_type)
    verify_method = "JVM" if jvm_available else "Python"
    return {"errors": errors, "warnings": warnings, "info": info, "verify_method": verify_method, "html_source": html_source, "scenarios": scenarios}

def main():
    parser = argparse.ArgumentParser(description="Legado 源完整性验证工具")
    parser.add_argument("--source-json", required=True, help="源 JSON 文件路径")
    parser.add_argument("--type", choices=["rss", "book"], default="rss", help="源类型")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--jvm", type=lambda x: x.lower() not in ('false', '0', 'no'), default=True,
                        help="使用 JVM 验证 (默认 True，自动检测可用性)")
    parser.add_argument("--jar-path", default=None,
                        help="RuleEngineServer JAR 路径 (默认: 自动搜索)")
    parser.add_argument('--fetch-html', action='store_true', help='启用HTML获取回退链')
    parser.add_argument('--cms-type', type=str, default=None, help='指定CMS类型（跳过自动检测）')
    args = parser.parse_args()

    fetch_html = args.fetch_html and _HTML_FETCHER_AVAILABLE
    if args.fetch_html and not _HTML_FETCHER_AVAILABLE:
        print("WARNING: --fetch-html 已指定但 HtmlFetcher 不可用（缺少 requests 库）", file=sys.stderr)

    # JVM 客户端初始化
    jvm_client = None
    jvm_available = False
    if args.jvm:
        jar_path = getattr(args, 'jar_path', None)
        jvm_client, jvm_available = _init_jvm_client(jar_path=jar_path)

    try:
        with open(args.source_json, 'r', encoding='utf-8') as f:
            sources = json.load(f)

        if not isinstance(sources, list):
            sources = [sources]

        all_results = []
        total_errors = 0
        total_warnings = 0

        for i, source in enumerate(sources):
            name = source.get("sourceName", source.get("bookSourceName", f"Source #{i}"))
            result = validate_source(source, args.type, jvm_client, jvm_available, fetch_html=fetch_html, cms_type=args.cms_type)
            result["name"] = name
            all_results.append(result)
            total_errors += len(result["errors"])
            total_warnings += len(result["warnings"])

        verify_method = "JVM" if jvm_available else "Python"
        output = {
            "ok": total_errors == 0,
            "total_sources": len(sources),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "results": all_results,
            "verify_method": verify_method,
            "confidence": "high" if jvm_available else "medium",
            "html_fetcher_enabled": fetch_html,
        }

        if args.output == "text":
            print(f"验证方式: {verify_method} (可信度: {output['confidence']})")
            if fetch_html:
                print(f"HTML获取回退链: 已启用 (cms_type={args.cms_type or 'auto'})")
            for r in all_results:
                print(f"\n=== {r['name']} ===")
                if r.get('html_source', 'none') != 'none':
                    print(f"  HTML来源: {r['html_source']}")
                for e in r["errors"]:
                    print(f"  ERROR: {e}")
                for w in r["warnings"]:
                    print(f"  WARN: {w}")
                for info in r.get("info", []):
                    print(f"  INFO: {info}")
                for sc in r.get("scenarios", []):
                    print(f"  场景: {sc['scenario']} ({sc['field']}) - {sc['note']}")
        else:
            print(json.dumps(output, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": str(e),
            "verify_method": "JVM" if jvm_available else "Python"
        }, ensure_ascii=False))
        sys.exit(1)
    finally:
        if jvm_client:
            jvm_client.shutdown()

if __name__ == "__main__":
    main()
