#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RuleEngineClient - Python 端与 RuleEngineServer 通信
MVP4: 支持 evalJS + evalCSS + decrypt/encrypt + analyzeRule/analyzeElements 命令

迁移自 tools/rule_engine_client.py，JAR 路径查找改用 legado_client.utils.config.Config。
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from typing import Optional

from legado_client.utils.config import config


class RuleEngineClient:
    def __init__(self, jar_path: Optional[str] = None, timeout: int = 30):
        self.process: Optional[subprocess.Popen] = None
        self.modules: list = []
        self.version: str = "unknown"
        self.timeout: int = timeout

        if jar_path is None:
            jar_path = config.jar_path

        self.jar_path: str = jar_path

    @staticmethod
    def _find_jar() -> str:
        """多路径回退搜索 JAR 文件（委托给 Config）"""
        return config.jar_path

    @staticmethod
    def _find_java() -> Optional[str]:
        """检测 JDK/JRE 可用性"""
        return config.find_java()

    def start(self) -> None:
        """启动 RuleEngineServer 进程"""
        if not os.path.exists(self.jar_path):
            raise FileNotFoundError(
                f"JAR not found: {self.jar_path}\n"
                f"Searched paths: tools/legado-jvm/build/libs/legado-jvm.jar, legado-rule-engine-mvp4.jar, mvp3.jar, mvp2.jar, mvp1.jar\n"
                f"Tip: Build with 'cd tools/legado-jvm && gradlew.bat build' or copy JAR to tools/"
            )

        java_cmd = self._find_java()
        if not java_cmd:
            raise RuntimeError(
                "Java not found. Install JDK 17+ and set JAVA_HOME or add java to PATH"
            )

        cmd = [
            java_cmd,
            "-Dfile.encoding=UTF-8",
            "-Dsun.stdout.encoding=UTF-8",
            "-Dsun.stderr.encoding=UTF-8",
            "-jar", self.jar_path
        ]

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            bufsize=1  # 行缓冲
        )

        # 读取启动信息（30s超时检测，超时则kill进程）
        startup_line_box: list = [None]
        def _read_startup():
            try:
                startup_line_box[0] = self.process.stdout.readline().strip()
            except Exception:
                startup_line_box[0] = ""

        reader_thread = threading.Thread(target=_read_startup, daemon=True)
        reader_thread.start()
        reader_thread.join(timeout=30)

        if reader_thread.is_alive():
            # 简化说明: 30s内未收到ready信号，kill进程 | 已知上限: 无 | 升级路径: 无
            self.process.kill()
            try:
                self.process.wait(timeout=3)
            except Exception:
                pass
            self.process = None
            raise RuntimeError("RuleEngineServer startup timeout (30s)")

        startup_line = startup_line_box[0]
        if not startup_line:
            raise RuntimeError("RuleEngineServer failed to start")

        startup_info = json.loads(startup_line)
        if startup_info.get("status") != "ready":
            raise RuntimeError(f"RuleEngineServer unexpected status: {startup_info}")

        self.modules = startup_info.get("modules", [])
        self.version = startup_info.get("version", "unknown")
        print(f"[RuleEngineClient] Server started: version={self.version}, modules={self.modules}")

    def _readline_with_timeout(self, timeout: int = 30) -> str:
        """带超时的 readline，防止 JVM 挂起导致无限等待。

        Args:
            timeout: 超时秒数，默认 30s

        Returns:
            str: 读取到的行（已 strip），超时返回 ""

        Raises:
            TimeoutError: JVM 挂起超时时抛出，并 kill 进程
        """
        line_box: list = [None]
        def _read():
            try:
                line_box[0] = self.process.stdout.readline()
            except Exception:
                line_box[0] = ""

        reader = threading.Thread(target=_read, daemon=True)
        reader.start()
        reader.join(timeout=timeout)

        if reader.is_alive():
            # JVM 挂起，kill 进程
            self.process.kill()
            try:
                self.process.wait(timeout=3)
            except Exception:
                pass
            self.process = None
            raise TimeoutError(f"RuleEngineServer response timeout ({timeout}s)")

        return (line_box[0] or "").strip()

    def _send(self, cmd_dict: dict) -> dict:
        """发送命令并接收响应"""
        if self.process is None or self.process.poll() is not None:
            return {"ok": False, "error": "Server not running"}

        cmd_json = json.dumps(cmd_dict, ensure_ascii=False)
        self.process.stdin.write(cmd_json + "\n")
        self.process.stdin.flush()

        response_line = self._readline_with_timeout(timeout=30)
        if not response_line:
            return {"ok": False, "error": "Empty response from server"}

        return json.loads(response_line)

    def ping(self) -> dict:
        """检查服务器是否存活"""
        return self._send({"cmd": "ping"})

    def eval_js(self, js_code: str, context: str = "") -> dict:
        """执行 JS 代码"""
        return self._send({
            "cmd": "evalJS",
            "code": js_code,
            "context": context
        })

    def eval_css(self, html: str, selector: str) -> dict:
        """
        [已弃用] 使用 jsoup 执行 CSS 选择器查询（请使用 debug_book_source 替代）

        Args:
            html: HTML 字符串
            selector: CSS 选择器（标准 CSS 选择器）

        Returns:
            dict: {
                "status": "ok" | "error",
                "results": [{"text": "...", "html": "...", "attributes": {...}, "tagName": "...", "className": "...", "id": "..."}, ...],
                "count": int,
                "selector": str,
                "confidence": "high" | "medium" | "low"
            }

        限制说明:
            - evalCSS 仅支持标准 CSS 选择器
            - 不支持 Legado 自定义索引语法（如 tag.div.0, tag.div!0）
            - 不支持 Legado 组合逻辑（&& / || / %%）
            - 如需完整规则解析（含自定义索引+组合逻辑），请使用 analyze_rule() 方法（MVP4）
        """
        return self._send({
            "cmd": "evalCSS",
            "html": html,
            "selector": selector
        })

    def analyze_rule(self, content: str, rule: str, base_url: str = "") -> dict:
        """
        [已弃用] 使用 Legado AnalyzeRule 完整规则解析（请使用 debug_book_source 替代）

        Args:
            content: HTML/JSON/XML 内容字符串
            rule: Legado 规则字符串，支持:
                - Default (JSoup): tag.div.0@text, class.article@tag.p!0@text, @CSS:div.title
                - JSON: $.data.list, $[0].name, @Json:$.data
                - XPath: //div[@class='title']/text(), @XPath://div
                - JS: <js>...</js>, @js:...
                - 组合逻辑: && (交集), || (回退), %% (差集)
                - 自定义索引: tag.div.0, tag.div!0, tag.div[-1], tag.div[0:3]
            base_url: 基础 URL（用于相对 URL 解析，可选）

        Returns:
            dict: {
                "status": "ok" | "error",
                "results": ["...", ...],
                "count": int,
                "rule": str,
                "mode": "Default" | "Json" | "XPath" | "CSS" | "Js" | "Default+Combo",
                "confidence": "high" | "medium" | "low"
            }
        """
        cmd = {
            "cmd": "analyzeRule",
            "content": content,
            "rule": rule
        }
        if base_url:
            cmd["baseUrl"] = base_url
        return self._send(cmd)

    def analyze_elements(self, content: str, rule: str, base_url: str = "") -> dict:
        """
        [已弃用] 使用 Legado AnalyzeRule 获取元素列表（请使用 debug_book_source 替代）

        Args:
            content: HTML/JSON/XML 内容字符串
            rule: Legado 规则字符串（同 analyze_rule）
            base_url: 基础 URL（可选）

        Returns:
            dict: {
                "status": "ok" | "error",
                "results": [
                    {
                        "text": "...",
                        "html": "...",
                        "ownText": "...",
                        "attributes": {...},
                        "tagName": "...",
                        "className": "...",
                        "id": "..."
                    },
                    ...
                ],
                "count": int,
                "rule": str,
                "mode": str,
                "confidence": "high" | "medium" | "low"
            }
        """
        cmd = {
            "cmd": "analyzeElements",
            "content": content,
            "rule": rule
        }
        if base_url:
            cmd["baseUrl"] = base_url
        return self._send(cmd)

    def decrypt(self, algo: str, key: str, data: str, iv: str = "",
                key_encoding: str = "utf8", iv_encoding: str = "utf8",
                data_encoding: str = "base64") -> dict:
        """
        [已弃用] 使用 hutool-crypto 解密数据（请使用 debug-source.py 的加密分析功能替代）

        Args:
            algo: 加密算法，如 "AES/CBC/PKCS5Padding", "AES/ECB/PKCS5Padding",
                  "DES/CBC/PKCS5Padding", "DES/ECB/PKCS5Padding"
            key: 密钥（根据 key_encoding 解码）
            data: 密文数据（根据 data_encoding 解码，默认 base64）
            iv: 初始化向量（可选，ECB 模式不需要）
            key_encoding: 密钥编码方式 "utf8"/"hex"/"base64"，默认 "utf8"
            iv_encoding: IV 编码方式 "utf8"/"hex"/"base64"，默认 "utf8"
            data_encoding: 数据编码方式 "utf8"/"hex"/"base64"，默认 "base64"

        Returns:
            dict: {
                "ok": bool,
                "status": "ok" | "error",
                "result": "base64编码的明文",
                "resultHex": "hex编码的明文",
                "resultUtf8": "UTF-8明文（如果可解码）",
                "confidence": "high" | "medium" | "low",
                "algo": str
            }
        """
        cmd = {
            "cmd": "decrypt",
            "algo": algo,
            "key": key,
            "data": data,
            "keyEncoding": key_encoding,
            "ivEncoding": iv_encoding,
            "dataEncoding": data_encoding
        }
        if iv:
            cmd["iv"] = iv
        return self._send(cmd)

    def encrypt(self, algo: str, key: str, data: str, iv: str = "",
                key_encoding: str = "utf8", iv_encoding: str = "utf8",
                data_encoding: str = "utf8") -> dict:
        """
        [已弃用] 使用 hutool-crypto 加密数据（请使用 debug-source.py 的加密分析功能替代）

        Args:
            algo: 加密算法，如 "AES/CBC/PKCS5Padding", "AES/ECB/PKCS5Padding",
                  "DES/CBC/PKCS5Padding", "DES/ECB/PKCS5Padding"
            key: 密钥（根据 key_encoding 解码）
            data: 明文数据（根据 data_encoding 解码，默认 utf8）
            iv: 初始化向量（可选，ECB 模式不需要）
            key_encoding: 密钥编码方式 "utf8"/"hex"/"base64"，默认 "utf8"
            iv_encoding: IV 编码方式 "utf8"/"hex"/"base64"，默认 "utf8"
            data_encoding: 数据编码方式 "utf8"/"hex"/"base64"，默认 "utf8"

        Returns:
            dict: {
                "ok": bool,
                "status": "ok" | "error",
                "result": "base64编码的密文",
                "resultHex": "hex编码的密文",
                "confidence": "high" | "medium" | "low",
                "algo": str
            }
        """
        cmd = {
            "cmd": "encrypt",
            "algo": algo,
            "key": key,
            "data": data,
            "keyEncoding": key_encoding,
            "ivEncoding": iv_encoding,
            "dataEncoding": data_encoding
        }
        if iv:
            cmd["iv"] = iv
        return self._send(cmd)

    # ==================== 端到端调试命令 ====================

    def analyze_url(self, url: str, key: Optional[str] = None,
                    page: Optional[int] = None, source_json: Optional[str] = None,
                    base_url: str = "") -> dict:
        """
        [已弃用] URL 解析（AnalyzeUrl 移植版）（请使用 debug_book_source 替代）

        Args:
            url: 待解析的 URL 规则字符串
            key: 搜索关键词（可选，用于 {{key}} 替换）
            page: 页码（可选，用于 {{page}} 替换）
            source_json: BookSource JSON 字符串（可选，提供 header/cookie 上下文）
            base_url: 基础 URL（可选，用于相对 URL 解析）

        Returns:
            dict: {
                "ok": bool,
                "url": 解析后的最终 URL,
                "method": "GET" | "POST",
                "headerMap": {...},
                "responseUrl": 实际请求 URL,
                "responseCode": HTTP 状态码,
                "responseBody": 响应体,
                "callTime": 耗时(ms),
                "confidence": "high" | "unverifiable" | "low"
            }
        """
        cmd: dict = {"cmd": "analyzeUrl", "url": url}
        if key:
            cmd["key"] = key
        if page is not None:
            cmd["page"] = page
        if source_json:
            cmd["sourceJson"] = source_json
        if base_url:
            cmd["baseUrl"] = base_url
        return self._send(cmd)

    def debug_book_source(self, source_json: str, key: str,
                          on_log=None, on_error=None, on_result=None) -> dict:
        """
        书源端到端调试（流式输出）

        调试链路: search → detail → toc → content

        Args:
            source_json: BookSource JSON 字符串
            key: 搜索关键词或阶段标识
                - 普通关键词: 完整链路（搜索→详情→目录→正文）
                - http://...: 仅详情页调试
                - ++url: 仅目录页调试
                - --url: 仅正文页调试
            on_log: 日志回调 (state, msg, html) -> None
            on_error: 错误回调 (msg, stack_trace, failed_stage) -> None
            on_result: 结果回调 (success, summary) -> None

        Returns:
            dict: 最终的 result 或 error 消息
        """
        return self._send_streaming(
            {"cmd": "debugBookSource", "sourceJson": source_json, "key": key},
            on_log, on_error, on_result
        )

    def debug_rss_source(self, source_json: str, key: str,
                          on_log=None, on_error=None, on_result=None) -> dict:
        """
        订阅源端到端调试（流式输出）

        调试链路: sort → content

        Args:
            source_json: RssSource JSON 字符串
            key: 搜索关键词或 URL
                - 普通关键词: 完整链路（列表→内容）
                - http://...: 仅内容页调试
            on_log: 日志回调 (state, msg, html) -> None
            on_error: 错误回调 (msg, stack_trace, failed_stage) -> None
            on_result: 结果回调 (success, summary) -> None

        Returns:
            dict: 最终的 result 或 error 消息
        """
        return self._send_streaming(
            {"cmd": "debugRssSource", "sourceJson": source_json, "key": key},
            on_log, on_error, on_result
        )

    def batch_debug(self, sources: list, source_type: str = "rss",
                    on_progress=None, on_complete=None,
                    webview_handler=None) -> Optional[dict]:
        """
        批量调试多个源（流式输出）

        Args:
            sources: 源列表，每个元素为 {"sourceJson": "...", "key": "..."}
            source_type: "rss" 或 "book"
            on_progress: 进度回调 (current, total, source_name, result) -> None
                result: dict，包含 success/needsWebView/needsUserIntervention/summary/errorStage
            on_complete: 完成回调 (results, success_count, total_count) -> None
            webview_handler: WebViewHandler 实例，用于处理 needsWebView 的源

        Returns:
            dict: 最终的 batch_complete 消息
        """
        if self.process is None or self.process.poll() is not None:
            return {"ok": False, "error": "Server not running"}

        cmd = {
            "cmd": "batch",
            "sourceType": source_type,
            "sources": sources
        }
        cmd_json = json.dumps(cmd, ensure_ascii=False)
        self.process.stdin.write(cmd_json + "\n")
        self.process.stdin.flush()

        final_result: Optional[dict] = None
        while True:
            line = self._readline_with_timeout(timeout=30)
            if not line:
                break

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "batch_progress":
                if on_progress:
                    try:
                        result = {
                            "success": msg.get("success", False),
                            "needsWebView": msg.get("needsWebView", False),
                            "needsUserIntervention": msg.get("needsUserIntervention", False),
                        }
                        on_progress(
                            msg.get("current", 0),
                            msg.get("total", 0),
                            msg.get("sourceName", ""),
                            result
                        )
                    except Exception:
                        pass
            elif msg_type == "batch_complete":
                results = msg.get("results", [])
                success_count = msg.get("successCount", 0)
                total_count = msg.get("totalCount", 0)

                # 处理 needsWebView 的源
                if webview_handler:
                    for result in results:
                        if result.get("needsWebView"):
                            self._handle_webview_source(result, webview_handler, source_type)

                if on_complete:
                    try:
                        on_complete(results, success_count, total_count)
                    except Exception:
                        pass
                final_result = msg
                break

        return final_result

    def _handle_webview_source(self, result: dict, webview_handler, source_type: str) -> None:
        """
        处理需要 WebView 渲染的源

        根据 webViewRequests 类型调用 webview_handler 对应方法，
        将渲染后 HTML 传回 JAR 用 analyze_rule 解析。

        Args:
            result: batch 结果中的单个源结果 dict
            webview_handler: WebViewHandler 实例
            source_type: "rss" 或 "book"
        """
        requests = result.get("webViewRequests", [])
        if not requests:
            return

        source_name = result.get("sourceName", "unknown")
        print(f"  [WebView] 处理源: {source_name}, 请求数: {len(requests)}")

        for req in requests:
            try:
                render_result = webview_handler.handle_webview_request(req)
                if render_result["success"]:
                    print(f"  [WebView] 渲染成功: {source_name}, HTML长度={len(render_result.get('html', ''))}")
                    # 渲染后 HTML 传回 JAR 用 analyze_rule 解析
                    # 简化说明: 当前仅标记为已渲染，完整解析需要源规则信息 | 已知上限: 未传回 JAR 解析 | 升级路径: 调用 self.analyze_rule(html, rule)
                    result["webviewRendered"] = True
                    result["webviewHtmlLength"] = len(render_result.get("html", ""))
                else:
                    print(f"  [WebView] 渲染失败: {source_name}, error={render_result.get('error')}")
                    result["webviewRendered"] = False
                    result["webviewError"] = render_result.get("error", "")
            except Exception as e:
                print(f"  [WebView] 处理异常: {source_name}, error={e}")
                result["webviewRendered"] = False
                result["webviewError"] = str(e)

    def _send_streaming(self, cmd_dict: dict, on_log=None,
                        on_error=None, on_result=None) -> dict:
        """发送流式命令，逐行读取响应直到 result 或 error"""
        if self.process is None or self.process.poll() is not None:
            return {"ok": False, "error": "Server not running"}

        cmd_json = json.dumps(cmd_dict, ensure_ascii=False)
        self.process.stdin.write(cmd_json + "\n")
        self.process.stdin.flush()

        final_result: dict = {}
        while True:
            line = self._readline_with_timeout(timeout=30)
            if not line:
                break

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "log":
                if on_log:
                    try:
                        on_log(msg.get("state", 1), msg.get("msg", ""), msg.get("html"))
                    except Exception:
                        pass  # 回调异常不影响结果读取
            elif msg_type == "error":
                if on_error:
                    try:
                        on_error(msg.get("msg", ""), msg.get("stackTrace"), msg.get("failedStage"))
                    except Exception:
                        pass
                final_result = msg
                break
            elif msg_type == "result":
                if on_result:
                    try:
                        on_result(msg.get("success", False), msg.get("summary", {}))
                    except Exception:
                        pass
                final_result = msg
                break

        return final_result

    def shutdown(self) -> None:
        """关闭服务器"""
        try:
            self._send({"cmd": "shutdown"})
        except Exception:
            pass
        finally:
            if self.process:
                try:
                    self.process.kill()
                    self.process.wait(timeout=3)
                except Exception:
                    pass
                self.process = None

    def is_alive(self) -> bool:
        """检查进程是否存活"""
        return self.process is not None and self.process.poll() is None

    def __enter__(self) -> "RuleEngineClient":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.shutdown()


if __name__ == "__main__":
    # 简单测试
    with RuleEngineClient() as client:
        # 测试1: ping
        print("ping:", client.ping())

        # 测试2: 简单 JS
        result = client.eval_js("1 + 1")
        print("1+1:", result)

        # 测试3: ES5 限制检测
        result = client.eval_js("var x = 1; x + 1;")
        print("var x:", result)

        # 测试4: java.put/get
        result = client.eval_js('java.put("test_key", "test_value"); java.get("test_key");')
        print("put/get:", result)

        # 测试5: 可信度评估
        result = client.eval_js('java.ajax("https://example.com/");')
        print("ajax:", result)

        # 测试6: evalCSS - 基本选择器
        html = '<html><body><div class="article"><p>Hello</p><p>World</p></div></body></html>'
        result = client.eval_css(html, "div.article p")
        print("evalCSS basic:", result)

        # 测试7: evalCSS - 属性选择器
        html2 = '<html><body><a href="/page1">Link1</a><a href="/page2">Link2</a></body></html>'
        result = client.eval_css(html2, "a[href]")
        print("evalCSS attr:", result)

        # 测试8: evalCSS - confidence 评估（@css: 前缀）
        result = client.eval_css(html, "@css:div.article p")
        print("evalCSS @css: (medium confidence):", result)

        # 测试9: evalCSS - 组合逻辑（low confidence）
        result = client.eval_css(html, "div.article&&p")
        print("evalCSS && (low confidence):", result)

        # 测试10: decrypt - AES/CBC/PKCS5Padding（Mirages 主题 key/iv）
        # 先用 encrypt 加密一段明文，再用 decrypt 解密验证
        test_plain = "Hello Legado MVP3!"
        enc_result = client.encrypt(
            algo="AES/CBC/PKCS5Padding",
            key="f5d965df75336270",
            iv="97b60394abc2fbe1",
            data=test_plain
        )
        print("encrypt AES-CBC:", enc_result)

        if enc_result.get("ok"):
            dec_result = client.decrypt(
                algo="AES/CBC/PKCS5Padding",
                key="f5d965df75336270",
                iv="97b60394abc2fbe1",
                data=enc_result["result"]
            )
            print("decrypt AES-CBC:", dec_result)
            if dec_result.get("ok") and dec_result.get("resultUtf8") == test_plain:
                print("✅ encrypt/decrypt round-trip PASSED!")
            else:
                print("❌ encrypt/decrypt round-trip FAILED!")

        # 测试11: decrypt - AES/ECB/PKCS5Padding（无 IV）
        enc_result2 = client.encrypt(
            algo="AES/ECB/PKCS5Padding",
            key="1234567890123456",
            data="ECB test data"
        )
        print("encrypt AES-ECB:", enc_result2)

        if enc_result2.get("ok"):
            dec_result2 = client.decrypt(
                algo="AES/ECB/PKCS5Padding",
                key="1234567890123456",
                data=enc_result2["result"]
            )
            print("decrypt AES-ECB:", dec_result2)

        # ========== MVP4 测试 ==========

        # 测试12: analyzeRule - tag.div.0@text
        html = '<html><body><div>First</div><div>Second</div><div>Third</div></body></html>'
        result = client.analyze_rule(html, "tag.div.0@text")
        print("analyzeRule tag.div.0@text:", result)

        # 测试13: analyzeRule - tag.div!0@text（排除第0个）
        result = client.analyze_rule(html, "tag.div!0@text")
        print("analyzeRule tag.div!0@text:", result)

        # 测试14: analyzeRule - tag.div[-1]@text（最后一个）
        result = client.analyze_rule(html, "tag.div[-1]@text")
        print("analyzeRule tag.div[-1]@text:", result)

        # 测试15: analyzeRule - class.article@tag.p!0@text（多级规则）
        html2 = '<html><body><div class="article"><p>Para1</p><p>Para2</p><p>Para3</p></div></body></html>'
        result = client.analyze_rule(html2, "class.article@tag.p!0@text")
        print("analyzeRule class.article@tag.p!0@text:", result)

        # 测试16: analyzeRule - && 组合逻辑
        html3 = '<html><body><span class="title">Title</span><span class="content">Content</span></body></html>'
        result = client.analyze_rule(html3, "class.title@text&&class.content@text")
        print("analyzeRule &&:", result)

        # 测试17: analyzeRule - || 回退逻辑
        html4 = '<html><body><a class="a" href="/page1">Link1</a><a class="b" href="/page2">Link2</a></body></html>'
        result = client.analyze_rule(html4, "class.a@href||class.b@href")
        print("analyzeRule ||:", result)

        # 测试18: analyzeRule - JSONPath
        json_content = '{"data":{"list":[{"name":"Alice"},{"name":"Bob"}]}}'
        result = client.analyze_rule(json_content, "$.data.list[*].name")
        print("analyzeRule JSONPath:", result)

        # 测试19: analyzeElements - 获取元素列表
        result = client.analyze_elements(html2, "class.article@tag.p")
        print("analyzeElements:", result)
