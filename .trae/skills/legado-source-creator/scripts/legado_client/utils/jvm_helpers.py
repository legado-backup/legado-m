"""
jvm_helpers - JVM 仿真器共享工具模块

提供统一的 JVM 初始化、参数解析、降级处理功能，
消除 verify-decrypt/verify-selector/verify-image/verify-source/analyze-site
中的 _init_jvm_client() 代码重复。
"""
import os
import sys
import argparse


def add_jvm_args(parser):
    """为 argparse 添加 --jvm 和 --jar-path 参数"""
    parser.add_argument(
        "--jvm", type=lambda x: x.lower() not in ('false', '0', 'no'),
        default=True,
        help="是否使用 JVM 仿真器验证 (默认: True, 传 --jvm false 关闭)"
    )
    parser.add_argument(
        "--jar-path", default=None,
        help="RuleEngineServer JAR 路径 (默认: 自动搜索 tools/ 目录)"
    )


def init_jvm_client(jar_path=None):
    """
    初始化 RuleEngineClient，自动处理 JDK 检测和降级。

    Args:
        jar_path: 可选的 JAR 路径，None 时使用 RuleEngineClient 默认搜索

    Returns:
        (client, jvm_available): client 为 RuleEngineClient 实例或 None，
                                  jvm_available 为 bool
    """
    try:
        tools_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools')
        )
        # 确保 tools/ 在 sys.path 中
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)

        from legado_client.client.rule_engine_client import RuleEngineClient
        client = RuleEngineClient(jar_path=jar_path)
        client.start()
        return client, True
    except FileNotFoundError as e:
        print(f"WARNING: JAR 文件未找到，降级到纯 Python 验证: {e}", file=sys.stderr)
        print("Tip: 使用 --jar-path 指定 JAR 路径，或构建: cd tools/legado-jvm && gradlew.bat fatJar",
              file=sys.stderr)
        return None, False
    except RuntimeError as e:
        if "Java not found" in str(e):
            print(f"WARNING: Java 未安装，降级到纯 Python 验证: {e}", file=sys.stderr)
        else:
            print(f"WARNING: JVM 启动失败，降级到纯 Python 验证: {e}", file=sys.stderr)
        return None, False
    except Exception as e:
        print(f"WARNING: JVM 不可用，降级到纯 Python 验证: {e}", file=sys.stderr)
        return None, False


def assess_confidence(rule_type, jvm_available, rule_content=""):
    """
    评估规则验证的可信度。

    Args:
        rule_type: 规则类型 ("css", "js", "decrypt", "encrypt", "xpath", "jsonpath", "regex")
        jvm_available: 是否使用 JVM 验证
        rule_content: 规则内容（用于检测 Cookie/Header 依赖）

    Returns:
        (confidence, note): confidence 为 "high"/"medium"/"low"/"unverifiable",
                            note 为说明文字
    """
    if not jvm_available:
        # Python 仿真模式
        if rule_type in ("css", "regex", "jsonpath", "xpath"):
            return "medium", "Python仿真（非jsoup/lxml原生实现）"
        elif rule_type in ("js", "decrypt", "encrypt"):
            return "low", "Python仿真无法执行JS/加密，仅语法检查"
        return "low", "Python仿真"

    # JVM 验证模式
    if rule_type in ("css", "regex", "jsonpath", "xpath"):
        return "high", "JVM验证通过"
    elif rule_type in ("decrypt", "encrypt"):
        return "high", "hutool-crypto验证通过"
    elif rule_type == "analyze_rule":
        # MVP4 AnalyzeRule 完整规则解析（逻辑与Kotlin assessAnalyzeConfidence对齐）
        content_lower = rule_content.lower()
        if "webview" in content_lower or "webjs" in content_lower:
            return "unverifiable", "规则依赖WebView，无法本地验证"
        if "<js>" in content_lower or "@js:" in content_lower:
            return "medium", "规则含JS代码，MockJsExtensions行为可能与真机不同"
        # XPath/JSONPath/CSS/Default+Combo 在 JVM 中通过 JsoupXpath/JSON/AnalyzeByJSoup 验证，可信度高
        return "high", "AnalyzeRule完整规则解析验证通过"
    elif rule_type == "js":
        # 检查 JS 中的依赖
        content_lower = rule_content.lower()
        # 主动检测 ES6 语法：Rhino Mozilla 扩展允许 let/const，但 Legado 真机不支持
        import re
        has_es6 = bool(re.search(r'\blet\b', rule_content)) or \
                  bool(re.search(r'\bconst\b', rule_content)) or \
                  '=>' in rule_content or \
                  '`' in rule_content
        if "webview" in content_lower or "webjs" in content_lower:
            return "unverifiable", "依赖WebView，无法本地验证"
        if has_es6:
            return "low", "含ES6语法(let/const/=>/模板字符串)，Legado真机不支持"
        if "ajax" in content_lower:
            if "cookie" in content_lower or "header" in content_lower:
                return "low", "依赖ajax()+Cookie/Header，Mock不自动携带"
            return "medium", "依赖ajax()，Mock不携带Cookie/Header"
        return "high", "纯逻辑JS，JVM验证通过"

    return "medium", "未知规则类型"
