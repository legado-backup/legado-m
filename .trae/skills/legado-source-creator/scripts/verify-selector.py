#!/usr/bin/env python3
"""固化选择器验证脚本 - 支持 JVM/Python 双模式"""
import argparse
import json
import os
import sys
import requests
from bs4 import BeautifulSoup


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
            print(f"WARNING: JVM 不可用，降级到纯 Python(BS4) 验证: {e}", file=sys.stderr)
            return None, False


def verify_selector_jvm(client, html, selector, mode, attr=None):
    """JVM 验证路径 - 使用 jsoup CSS 选择器（与 Legado 一致）"""
    result = client.eval_css(html, selector)

    if result.get("status") == "error":
        return None, result.get("error", "unknown error")

    elements = result.get("results", [])
    confidence = result.get("confidence", "high")

    results = []
    for el in elements:
        if mode == "text":
            results.append(el.get("text", ""))
        elif mode == "attr":
            results.append(el.get("attributes", {}).get(attr, ""))
        elif mode == "html":
            results.append(el.get("html", ""))
        else:  # css
            results.append({
                "tag": el.get("tagName", ""),
                "text": el.get("text", "")[:100],
                "attrs": el.get("attributes", {})
            })

    return {
        "ok": True,
        "count": result.get("count", len(results)),
        "results": results[:20],
        "confidence": confidence,
        "verify_method": "JVM",
        "note": "jsoup 选择器与 Legado 运行时一致"
    }, None


def verify_selector_python(html, selector, mode, attr=None):
    """Python 降级路径 - 使用 BS4"""
    soup = BeautifulSoup(html, 'html.parser')
    elements = soup.select(selector)

    results = []
    for el in elements:
        if mode == "text":
            results.append(el.get_text(strip=True))
        elif mode == "attr":
            results.append(el.get(attr, ""))
        elif mode == "html":
            results.append(str(el))
        else:
            results.append({
                "tag": el.name,
                "text": el.get_text(strip=True)[:100],
                "attrs": dict(el.attrs) if el.attrs else {}
            })

    return {
        "ok": True,
        "count": len(results),
        "results": results[:20],
        "confidence": "medium",
        "verify_method": "Python",
        "note": "BS4 选择器与 jsoup 基本一致，但伪类(:has/:not)支持可能不同"
    }


def main():
    parser = argparse.ArgumentParser(description="Legado CSS 选择器验证工具")
    parser.add_argument("--url", required=True, help="目标 URL")
    parser.add_argument("--selector", required=True, help="CSS 选择器")
    parser.add_argument("--mode", choices=["css", "text", "attr", "html"], default="css", help="提取模式")
    parser.add_argument("--attr", default=None, help="提取属性名 (mode=attr 时)")
    parser.add_argument("--header", default=None, help="额外 Header (JSON格式)")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--jvm", type=lambda x: x.lower() not in ('false', '0', 'no'), default=True,
                        help="使用 JVM 验证 (默认 True，自动检测可用性)")
    parser.add_argument("--jar-path", default=None,
                        help="RuleEngineServer JAR 路径 (默认: 自动搜索)")
    args = parser.parse_args()

    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36"}
    if args.header:
        try:
            headers.update(json.loads(args.header))
        except:
            pass

    # JVM 客户端初始化
    jvm_client = None
    jvm_available = False
    if args.jvm:
        jar_path = getattr(args, 'jar_path', None)
        jvm_client, jvm_available = _init_jvm_client(jar_path=jar_path)

    try:
        resp = requests.get(args.url, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        if jvm_available:
            # JVM 验证路径
            output, error = verify_selector_jvm(jvm_client, html, args.selector, args.mode, args.attr)
            if error:
                print(f"WARNING: JVM 选择器验证失败，降级到 Python: {error}", file=sys.stderr)
                jvm_available = False
            else:
                if args.output == "text":
                    for r in output["results"][:20]:
                        print(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))
                else:
                    print(json.dumps(output, ensure_ascii=False, default=str))

        if not jvm_available:
            # Python 降级路径
            output = verify_selector_python(html, args.selector, args.mode, args.attr)
            if args.output == "text":
                for r in output["results"][:20]:
                    print(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))
            else:
                print(json.dumps(output, ensure_ascii=False, default=str))

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
