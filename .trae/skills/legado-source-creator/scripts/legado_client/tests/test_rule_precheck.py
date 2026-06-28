#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RulePrecheck 单元测试。

同时支持：
- `python test_rule_precheck.py` 独立运行
- `pytest test_rule_precheck.py` 运行

被测模块：analyzer/rule_precheck.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzer.rule_precheck import RulePrecheck, precheck_rules


# ========== 5 种规则类型语法检查 - 正常用例 ==========

def test_valid_css_rule():
    """@CSS: 合法选择器通过。"""
    src = {"ruleSearch": {"bookList": "@CSS:.book-item"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True
    assert result["errors"] == []


def test_valid_xpath_rule():
    """@XPath: 合法路径通过。"""
    src = {"ruleSearch": {"bookList": "@XPath://div[@class='item']"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_json_rule():
    """@Json: 合法 JSONPath 通过。"""
    src = {"ruleSearch": {"bookList": "@Json:$.data.list[*]"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_json_rule_case_insensitive():
    """@json: 忽略大小写识别为 JSONPath（源码 startsWith 第二参数 true）。"""
    src = {"ruleSearch": {"bookList": "@json:$.data.list"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_js_rule_at_js():
    """@js: 合法 ES5 JS 通过。"""
    src = {"ruleContent": {"content": "@js:var x = 1; result;"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_js_rule_tag():
    """<js>...</js> 合法 JS 通过。"""
    src = {"ruleContent": {"content": "<js>var x = 1; result;</js>"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_default_css():
    """无前缀默认 CSS（jsoup 语法）通过。"""
    src = {"ruleSearch": {"bookList": ".book-item"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_var_rule_put():
    """@put: 变量规则通过。"""
    src = {"ruleSearch": {"bookList": "@put:{key:value}"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_valid_var_rule_get():
    """@get: 变量规则通过。"""
    src = {"ruleSearch": {"bookList": "@get:{key}"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


def test_regex_treated_as_default_css():
    """正则风格规则（无 @regex 前缀）被识别为默认 CSS。

    源码 AnalyzeRule.kt 不存在 <regex> 前缀，正则表达式字符串会被当作默认 CSS 处理。
    本测试验证该源码行为：只要括号引号匹配，即通过语法检查。
    """
    src = {"ruleSearch": {"bookList": "^\\d+$"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True


# ========== 5 种规则类型语法检查 - 异常用例 ==========

def test_css_unmatched_bracket():
    """CSS 括号不匹配触发 ERROR。"""
    src = {"ruleSearch": {"bookList": "@CSS:.item(a"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False
    assert any(e["field"] == "ruleSearch.bookList" for e in result["errors"])


def test_xpath_unmatched_quote():
    """XPath 引号未闭合触发 ERROR。"""
    src = {"ruleSearch": {"bookList": "@XPath://div[@class='item]"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False


def test_json_missing_dollar():
    """JSONPath 不以 $ 开头触发 ERROR。"""
    src = {"ruleSearch": {"bookList": "@Json:data.list"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False
    assert any("应以 $ 开头" in e["message"] for e in result["errors"])


def test_js_unmatched_paren():
    """@js: JS 括号不匹配触发 ERROR。"""
    src = {"ruleContent": {"content": "@js:func(a"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False


def test_js_unclosed_tag():
    """<js> 标签内括号不匹配触发 ERROR。"""
    src = {"ruleContent": {"content": "<js>func(a</js>"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False


def test_default_css_unmatched_bracket():
    """默认 CSS（无前缀）括号不匹配触发 ERROR。"""
    src = {"ruleSearch": {"bookList": ".item(a"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False


def test_var_unmatched_bracket():
    """@put: 变量规则括号不匹配触发 ERROR。"""
    src = {"ruleSearch": {"bookList": "@put:{key:value"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is False


# ========== Rhino 兼容性检测 ==========

def test_rhino_let_keyword():
    """let 关键字触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:let x = 1;"}}
    result = RulePrecheck(src, "book").precheck()
    assert any("let" in w["message"] for w in result["warnings"])


def test_rhino_const_keyword():
    """const 关键字触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:const x = 1;"}}
    result = RulePrecheck(src, "book").precheck()
    assert any("const" in w["message"] for w in result["warnings"])


def test_rhino_arrow_function():
    """箭头函数 => 触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:var f = (x) => x + 1;"}}
    result = RulePrecheck(src, "book").precheck()
    assert any("箭头函数" in w["message"] for w in result["warnings"])


def test_rhino_template_string():
    """模板字符串反引号触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:var s = `hello`;"}}
    result = RulePrecheck(src, "book").precheck()
    assert any("模板字符串" in w["message"] for w in result["warnings"])


def test_rhino_async_await():
    """async/await 触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:async function f(){ await g(); }"}}
    result = RulePrecheck(src, "book").precheck()
    warns = [w["message"] for w in result["warnings"]]
    assert any("async" in m for m in warns)
    assert any("await" in m for m in warns)


def test_rhino_fetch_promise():
    """fetch/Promise 触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:fetch('url'); new Promise(function(){});"}}
    result = RulePrecheck(src, "book").precheck()
    warns = [w["message"] for w in result["warnings"]]
    assert any("fetch" in m for m in warns)
    assert any("Promise" in m for m in warns)


def test_rhino_clean_js_no_warning():
    """无 ES6 语法的 ES5 JS 不触发 Rhino 兼容性警告。"""
    src = {"ruleContent": {"content": "@js:var x = 1; function f(){ return x; }"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["warnings"] == []


def test_rhino_warning_only_for_js_rule():
    """Rhino 兼容性警告仅对 JS 规则生效，CSS 规则含 'let' 子串不报警告。"""
    # CSS 规则 .letter 含 "let" 子串，但 rule_type=css 不调用 Rhino 检查
    src = {"ruleSearch": {"bookList": "@CSS:.letter"}}
    result = RulePrecheck(src, "book").precheck()
    assert result["warnings"] == []


# ========== 便捷函数与边界 ==========

def test_precheck_rules_function():
    """模块级便捷函数与类方法结果一致。"""
    src = {"ruleContent": {"content": "@js:var x = 1;"}}
    r1 = precheck_rules(src, "book")
    r2 = RulePrecheck(src, "book").precheck()
    assert r1 == r2


def test_empty_fields_skipped():
    """空字段跳过语法检查（由 SourceValidator 负责非空校验）。"""
    src = {
        "ruleSearch": {"bookList": ""},
        "ruleContent": {"content": None},
    }
    result = RulePrecheck(src, "book").precheck()
    assert result["valid"] is True
    assert result["errors"] == []


def test_none_source_object():
    """None 对象不抛异常。"""
    result = RulePrecheck(None, "book").precheck()
    assert result["valid"] is True


def test_rss_source_precheck():
    """RSS 源规则字段校验通过。"""
    src = {"ruleArticles": "@CSS:.item", "ruleTitle": ".title"}
    result = RulePrecheck(src, "rss").precheck()
    assert result["valid"] is True


def test_rss_invalid_rule():
    """RSS 源规则语法错误触发 ERROR。"""
    src = {"ruleArticles": "@CSS:.item(a"}
    result = RulePrecheck(src, "rss").precheck()
    assert result["valid"] is False
    assert any(e["field"] == "ruleArticles" for e in result["errors"])


def test_rss_rhino_warning():
    """RSS 源 JS 规则同样触发 Rhino 兼容性警告。"""
    src = {"ruleContent": "@js:let x = 1;"}
    result = RulePrecheck(src, "rss").precheck()
    assert any("let" in w["message"] for w in result["warnings"])


# ========== main 入口 ==========

if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n总计: {len(tests)} | 通过: {passed} | 失败: {failed}")
    sys.exit(0 if failed == 0 else 1)
