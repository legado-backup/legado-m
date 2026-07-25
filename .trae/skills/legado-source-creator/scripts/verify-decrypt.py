#!/usr/bin/env python3
"""固化解密验证脚本 - 支持 JVM/Python 双模式"""
import argparse
import base64
import hashlib
import json
import os
import sys
from Crypto.Cipher import AES, DES
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


def decrypt_aes_cbc(data, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(data)
    try:
        return unpad(decrypted, AES.block_size)
    except ValueError:
        return decrypted

def decrypt_aes_ecb(data, key):
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(data)
    try:
        return unpad(decrypted, AES.block_size)
    except ValueError:
        return decrypted

def decrypt_des_cbc(data, key, iv):
    cipher = DES.new(key, DES.MODE_CBC, iv)
    decrypted = cipher.decrypt(data)
    try:
        return unpad(decrypted, DES.block_size)
    except ValueError:
        return decrypted

def decrypt_python(algo, key_str, iv_str, data_b64):
    """纯 Python 解密路径"""
    key_bytes = key_str.encode('utf-8')
    iv_bytes = iv_str.encode('utf-8') if iv_str else None
    data_bytes = base64.b64decode(data_b64)

    if algo == "AES/CBC/PKCS5Padding":
        if not iv_bytes:
            raise ValueError("AES/CBC requires IV")
        result = decrypt_aes_cbc(data_bytes, key_bytes, iv_bytes)
    elif algo == "AES/ECB/PKCS5Padding":
        result = decrypt_aes_ecb(data_bytes, key_bytes)
    elif algo == "DES/CBC/PKCS5Padding":
        if not iv_bytes:
            raise ValueError("DES/CBC requires IV")
        result = decrypt_des_cbc(data_bytes, key_bytes[:8], iv_bytes[:8])
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")

    return result

def main():
    parser = argparse.ArgumentParser(description="Legado 解密验证工具")
    parser.add_argument("--algo", required=True, help="算法 (AES/CBC/PKCS5Padding, AES/ECB/PKCS5Padding, DES/CBC/PKCS5Padding)")
    parser.add_argument("--key", required=True, help="密钥 (字符串)")
    parser.add_argument("--iv", default=None, help="IV (字符串，可选)")
    parser.add_argument("--data", required=True, help="待解密数据 (Base64编码)")
    parser.add_argument("--mode", choices=["decrypt", "decryptStr"], default="decrypt", help="解密模式")
    parser.add_argument("--output", choices=["hex", "base64", "text", "auto"], default="auto", help="输出格式")
    parser.add_argument("--jvm", type=lambda x: x.lower() not in ('false', '0', 'no'), default=True,
                        help="使用 JVM 验证 (默认 True，自动检测可用性)")
    parser.add_argument("--jar-path", default=None,
                        help="RuleEngineServer JAR 路径 (默认: 自动搜索)")
    args = parser.parse_args()

    # JVM 客户端初始化
    jvm_client = None
    jvm_available = False
    if args.jvm:
        jar_path = getattr(args, 'jar_path', None)
        jvm_client, jvm_available = _init_jvm_client(jar_path=jar_path)

    try:
        if jvm_available:
            # JVM 验证路径 - 使用 hutool-crypto（与 Legado 一致）
            jvm_result = jvm_client.decrypt(
                algo=args.algo,
                key=args.key,
                data=args.data,
                iv=args.iv or ""
            )

            if jvm_result.get("ok"):
                # JVM 解密成功
                result_utf8 = jvm_result.get("resultUtf8", "")
                result_b64 = jvm_result.get("result", "")
                confidence = jvm_result.get("confidence", "high")
                verify_method = "JVM"

                # 格式化输出
                if args.mode == "decryptStr":
                    output = result_utf8
                elif args.output == "hex":
                    output = jvm_result.get("resultHex", "")
                elif args.output == "base64":
                    output = result_b64
                elif args.output == "text":
                    output = result_utf8
                else:  # auto
                    output = result_utf8 if result_utf8 else result_b64

                print(json.dumps({
                    "ok": True,
                    "result": output,
                    "result_type": "str" if args.mode == "decryptStr" else "bytes",
                    "confidence": confidence,
                    "verify_method": verify_method
                }, ensure_ascii=False))
            else:
                # JVM 解密失败，降级到 Python
                print(f"WARNING: JVM 解密失败，降级到 Python: {jvm_result.get('error', 'unknown')}", file=sys.stderr)
                jvm_available = False

        if not jvm_available:
            # Python 降级路径
            result = decrypt_python(args.algo, args.key, args.iv, args.data)

            if args.mode == "decryptStr":
                output = result.decode('utf-8', errors='replace')
            elif args.output == "hex":
                output = result.hex()
            elif args.output == "base64":
                output = base64.b64encode(result).decode('utf-8')
            elif args.output == "text":
                output = result.decode('utf-8', errors='replace')
            else:  # auto
                try:
                    output = result.decode('utf-8')
                    if not output.isprintable():
                        raise ValueError()
                except:
                    output = base64.b64encode(result).decode('utf-8')

            print(json.dumps({
                "ok": True,
                "result": output,
                "result_type": "str" if args.mode == "decryptStr" else "bytes",
                "confidence": "medium",
                "verify_method": "Python"
            }, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": str(e),
            "confidence": "medium",
            "verify_method": "JVM" if jvm_available else "Python"
        }, ensure_ascii=False))
        sys.exit(1)
    finally:
        if jvm_client:
            jvm_client.shutdown()

if __name__ == "__main__":
    main()
