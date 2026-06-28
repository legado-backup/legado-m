#!/usr/bin/env python3
"""固化图片加密验证脚本 - 支持 JVM/Python 双模式"""
import argparse
import base64
import json
import os
import sys
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


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
            print(f"WARNING: JVM 不可用，降级到纯 Python 验证: {e}", file=sys.stderr)
            return None, False


def detect_image_format(data):
    """检测图片格式"""
    if data[:3] == b'\xff\xd8\xff':
        return "jpg"
    elif data[:8] == b'\x89PNG\r\n\x1a\n':
        return "png"
    elif data[:4] == b'RIFF':
        return "webp"
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return "gif"
    return "jpg"


def verify_image_jvm(client, raw_bytes, key, iv, algo, output_fmt, save_path):
    """JVM 验证路径 - 使用 hutool-crypto 解密（与 Legado 一致）"""
    b64_data = base64.b64encode(raw_bytes).decode('utf-8')

    jvm_result = client.decrypt(
        algo=algo,
        key=key,
        data=b64_data,
        iv=iv
    )

    if not jvm_result.get("ok"):
        return None, jvm_result.get("error", "unknown error")

    # 从 JVM 结果获取解密数据
    result_b64 = jvm_result.get("result", "")
    decrypted = base64.b64decode(result_b64)
    confidence = jvm_result.get("confidence", "high")
    ext = detect_image_format(decrypted)

    result = {
        "ok": True,
        "image_format": ext,
        "confidence": confidence,
        "verify_method": "JVM"
    }

    if output_fmt == "datauri":
        result["data_uri_length"] = len(f"data:image/{ext};base64,{result_b64}")
    elif output_fmt == "save" and save_path:
        with open(save_path, 'wb') as f:
            f.write(decrypted)
        result["saved"] = save_path

    return result, None


def verify_image_python(raw_bytes, key, iv, algo, output_fmt, save_path):
    """Python 降级路径 - 使用 pycryptodome"""
    key_bytes = key.encode('utf-8')
    iv_bytes = iv.encode('utf-8')

    if "ECB" in algo:
        cipher = AES.new(key_bytes, AES.MODE_ECB)
    else:
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)

    decrypted = cipher.decrypt(raw_bytes)
    try:
        decrypted = unpad(decrypted, AES.block_size)
    except ValueError:
        pass  # 可能不需要 unpad

    result_b64 = base64.b64encode(decrypted).decode('utf-8')
    ext = detect_image_format(decrypted)

    result = {
        "ok": True,
        "image_format": ext,
        "confidence": "medium",
        "verify_method": "Python"
    }

    if output_fmt == "datauri":
        data_uri = f"data:image/{ext};base64,{result_b64}"
        result["data_uri_length"] = len(data_uri)
    elif output_fmt == "save" and save_path:
        with open(save_path, 'wb') as f:
            f.write(decrypted)
        result["saved"] = save_path
    elif output_fmt == "base64":
        # 直接输出 base64
        return result_b64, None

    return result, None


def main():
    parser = argparse.ArgumentParser(description="Legado 图片加密验证工具")
    parser.add_argument("--url", required=True, help="图片 URL")
    parser.add_argument("--key", required=True, help="AES 密钥")
    parser.add_argument("--iv", required=True, help="AES IV")
    parser.add_argument("--algo", default="AES/CBC/PKCS5Padding", help="算法")
    parser.add_argument("--output", choices=["base64", "datauri", "save"], default="datauri", help="输出格式")
    parser.add_argument("--save-path", default=None, help="保存路径 (output=save 时)")
    parser.add_argument("--jvm", type=lambda x: x.lower() not in ('false', '0', 'no'), default=True,
                        help="使用 JVM 验证 (默认 True，自动检测可用性)")
    parser.add_argument("--jar-path", default=None,
                        help="RuleEngineServer JAR 路径 (默认: 自动搜索)")
    args = parser.parse_args()

    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36"}

    # JVM 客户端初始化
    jvm_client = None
    jvm_available = False
    if args.jvm:
        jar_path = getattr(args, 'jar_path', None)
        jvm_client, jvm_available = _init_jvm_client(jar_path=jar_path)

    try:
        # 1. 下载图片
        resp = requests.get(args.url, headers=headers, timeout=15)
        resp.raise_for_status()
        raw_bytes = resp.content

        if jvm_available:
            # JVM 验证路径
            output, error = verify_image_jvm(
                jvm_client, raw_bytes, args.key, args.iv, args.algo, args.output, args.save_path
            )
            if error:
                print(f"WARNING: JVM 图片解密失败，降级到 Python: {error}", file=sys.stderr)
                jvm_available = False
            else:
                if args.output == "base64" and isinstance(output, str):
                    print(output)
                else:
                    print(json.dumps(output, ensure_ascii=False))

        if not jvm_available:
            # Python 降级路径
            output, error = verify_image_python(
                raw_bytes, args.key, args.iv, args.algo, args.output, args.save_path
            )
            if error:
                print(json.dumps({"ok": False, "error": error, "verify_method": "Python"}, ensure_ascii=False))
                sys.exit(1)
            if args.output == "base64" and isinstance(output, str):
                print(output)
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
