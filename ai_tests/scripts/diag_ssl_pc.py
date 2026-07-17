#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SSL/TLS 握手诊断脚本（PC端控制变量实验A）

用途：从订阅源JSON读取sourceUrl，在PC端用Python ssl模块测试TLS握手
输出：仅输出技术结论（成功/失败、TLS版本、cipher），不输出域名/URL/IP

使用：
    python ai_tests/scripts/diag_ssl_pc.py <json路径>

设计原则：脱敏输出（符合output-safety.md）
"""
import json
import socket
import ssl
import sys
import urllib.parse
from pathlib import Path


def load_source_url(json_path: str) -> str:
    """从订阅源JSON读取sourceUrl字段（不输出）"""
    p = Path(json_path)
    if not p.exists():
        print(f"[ERROR] 文件不存在: {p}")
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 兼容单个对象或数组
    if isinstance(data, list):
        if not data:
            print("[ERROR] JSON数组为空")
            sys.exit(1)
        src = data[0]
    else:
        src = data
    url = src.get("sourceUrl") or src.get("sourceUrl")
    if not url:
        print("[ERROR] 未找到sourceUrl字段")
        sys.exit(1)
    return url


def test_tls_handshake(host: str, port: int, min_ver=None, max_ver=None, label: str = ""):
    """测试TLS握手，返回技术结论"""
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if min_ver is not None:
            ctx.minimum_version = min_ver
        if max_ver is not None:
            ctx.maximum_version = max_ver
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                ver = ssock.version()
                cipher = ssock.cipher()
                cipher_name = cipher[0] if cipher else "unknown"
                # 获取证书信息（不输出域名）
                cert = ssock.getpeercert(binary_form=False) or {}
                issuer_cn = ""
                if "issuer" in cert:
                    for tup in cert["issuer"]:
                        for k, v in tup:
                            if k == "commonName":
                                issuer_cn = v[:30]  # 截断
                return {
                    "result": "OK",
                    "label": label,
                    "tls_version": ver,
                    "cipher": cipher_name,
                    "issuer_cn": issuer_cn,
                }
    except ssl.SSLError as e:
        return {"result": "SSL_ERROR", "label": label, "error_type": type(e).__name__, "error_msg": str(e)[:120]}
    except socket.timeout:
        return {"result": "TIMEOUT", "label": label, "error_msg": "10s timeout"}
    except ConnectionResetError:
        return {"result": "CONN_RESET", "label": label, "error_msg": "connection reset"}
    except ConnectionRefusedError:
        return {"result": "CONN_REFUSED", "label": label, "error_msg": "connection refused"}
    except Exception as e:
        return {"result": "FAIL", "label": label, "error_type": type(e).__name__, "error_msg": str(e)[:120]}


def main():
    if len(sys.argv) < 2:
        print("用法: python diag_ssl_pc.py <json路径>")
        sys.exit(1)

    json_path = sys.argv[1]
    url = load_source_url(json_path)
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    if not host:
        print("[ERROR] URL解析失败，无hostname")
        sys.exit(1)

    # 脱敏输出：只显示host前2字符+长度
    print("=" * 60)
    print(f"[TARGET] host=({host[:2]}***, len={len(host)}), port={port}")
    print(f"[TARGET] scheme={parsed.scheme}")
    print("=" * 60)

    # 测试1：默认（系统选最优TLS版本）
    r1 = test_tls_handshake(host, port, label="默认(系统选)")
    # 测试2：强制TLS 1.2
    r2 = test_tls_handshake(host, port, min_ver=ssl.TLSVersion.TLSv1_2, max_ver=ssl.TLSVersion.TLSv1_2, label="TLS1.2")
    # 测试3：强制TLS 1.3
    r3 = test_tls_handshake(host, port, min_ver=ssl.TLSVersion.TLSv1_3, max_ver=ssl.TLSVersion.TLSv1_3, label="TLS1.3")

    print()
    print("=" * 60)
    print("[CONCLUSION] PC端Python ssl 模块握手结果：")
    print("=" * 60)
    for r in [r1, r2, r3]:
        label = r.get("label", "")
        result = r.get("result", "")
        if result == "OK":
            print(f"  [{label}] OK | TLS={r['tls_version']} | cipher={r['cipher']} | issuerCN={r['issuer_cn']}")
        else:
            err = r.get("error_msg", "")
            print(f"  [{label}] FAIL({result}) | {err}")

    print()
    print("=" * 60)
    print("[ANALYSIS] 推断：")
    print("=" * 60)
    # 全部成功：源站正常，问题在 WebView/网络环境
    # 全部失败或部分失败：可能是源站或网络问题
    success_count = sum(1 for r in [r1, r2, r3] if r.get("result") == "OK")
    if success_count == 3:
        print("  → PC端能成功握手，源站TLS配置正常")
        print("  → 问题在 WebView 版本（Chrome 68 太老）或模拟器网络环境（如GFW阻断SNI）")
        print("  → 排除'源站问题'假设")
    elif success_count == 0:
        print("  → PC端全部失败，可能是源站故障或网络环境阻断")
        print("  → 需进一步用代理对照测试")
    else:
        # 部分成功
        ok_versions = [r.get("tls_version") for r in [r1, r2, r3] if r.get("result") == "OK"]
        fail_labels = [r.get("label") for r in [r1, r2, r3] if r.get("result") != "OK"]
        print(f"  → 部分成功（成功版本: {ok_versions}, 失败: {fail_labels}）")
        print("  → 可能是TLS版本兼容性问题")


if __name__ == "__main__":
    main()
