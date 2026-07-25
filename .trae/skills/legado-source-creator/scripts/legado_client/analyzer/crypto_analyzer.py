#!/usr/bin/env python3
"""加密自动分析模块 - 扫描JS代码中的加密调用，生成Legado书源解密代码模板

基于 Legado createSymmetricCrypto API，自动识别 CryptoJS 调用模式并生成等效的 Legado JS 代码。

支持的加密类型：
- 对称加密：AES/DES/3DES/RC4/Rabbit（encrypt/decrypt）
- 摘要算法：MD5/SHA1/SHA256/SHA512
- HMAC：HmacMD5/HmacSHA256/HmacSHA512
- 编码：Base64/Hex/Utf8

参考文档：
- references/source-analysis/js-extensions-crypto.md
- references/js-patterns/crypto-patterns.md
- references/troubleshooting/crypto-traps.md
"""
import re


# ── 辅助函数 ──────────────────────────────────────────────

def _extract_call_args(text, paren_pos):
    """从 paren_pos 位置的 '(' 开始，提取匹配的括号内容（处理嵌套）"""
    depth = 0
    i = paren_pos
    while i < len(text):
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[paren_pos + 1:i], i
        i += 1
    return None, -1


def _split_args(args_str):
    """分割参数列表，处理嵌套的括号/花括号/引号"""
    args = []
    current = ''
    depth = 0
    in_string = False
    string_char = None
    i = 0
    while i < len(args_str):
        c = args_str[i]
        if in_string:
            current += c
            if c == string_char and (i == 0 or args_str[i - 1] != '\\'):
                in_string = False
        elif c in ('"', "'", '`'):
            in_string = True
            string_char = c
            current += c
        elif c in ('(', '{', '['):
            depth += 1
            current += c
        elif c in (')', '}', ']'):
            depth -= 1
            current += c
        elif c == ',' and depth == 0:
            args.append(current.strip())
            current = ''
        else:
            current += c
        i += 1
    if current.strip():
        args.append(current.strip())
    return args


def _resolve_value(js_code, expr):
    """解析表达式值，返回 (value, source_type)

    支持三种来源：
    1. hardcoded - 硬编码字符串
    2. utf8_parse - CryptoJS.enc.Utf8.parse("key")（WordArray密钥）
    3. variable - 变量引用（搜索 var/const/let 定义）
    4. function_call - 函数返回值（需人工确认）
    """
    expr = expr.strip()
    if not expr:
        return None, 'empty'

    # 1. 硬编码字符串
    str_match = re.match(r'^["\']([^"\']*)["\']', expr)
    if str_match:
        return str_match.group(1), 'hardcoded'

    # 2. CryptoJS.enc.Utf8.parse("key") - WordArray密钥
    utf8_match = re.match(r'CryptoJS\.enc\.Utf8\.parse\(\s*["\']([^"\']*)["\']\s*\)', expr)
    if utf8_match:
        return utf8_match.group(1), 'utf8_parse'

    # 3. CryptoJS.enc.Hex.parse("hex")
    hex_match = re.match(r'CryptoJS\.enc\.Hex\.parse\(\s*["\']([^"\']*)["\']\s*\)', expr)
    if hex_match:
        return hex_match.group(1), 'hex_parse'

    # 4. 变量引用 - 搜索定义
    var_match = re.match(r'^([a-zA-Z_$][\w$]*)$', expr)
    if var_match:
        var_name = var_match.group(1)
        for pat in [
            rf'(?:var|const|let)\s+{re.escape(var_name)}\s*=\s*["\']([^"\']*)["\']',
            rf'(?:var|const|let)\s+{re.escape(var_name)}\s*=\s*CryptoJS\.enc\.Utf8\.parse\(\s*["\']([^"\']*)["\']\s*\)',
            rf'(?:var|const|let)\s+{re.escape(var_name)}\s*=\s*CryptoJS\.enc\.Hex\.parse\(\s*["\']([^"\']*)["\']\s*\)',
        ]:
            dm = re.search(pat, js_code)
            if dm:
                return dm.group(1), 'variable'
        return None, 'variable_unresolved'

    # 5. 函数调用
    if re.match(r'^[a-zA-Z_$][\w$]*\s*\(', expr):
        return None, 'function_call'

    return None, 'unknown'


# ── 核心函数 ──────────────────────────────────────────────

# 加密调用匹配模式: (正则, type, operation)
_CRYPTO_PATTERNS = [
    (r'CryptoJS\.AES\.encrypt', 'AES', 'encrypt'),
    (r'CryptoJS\.AES\.decrypt', 'AES', 'decrypt'),
    (r'CryptoJS\.DES\.encrypt', 'DES', 'encrypt'),
    (r'CryptoJS\.DES\.decrypt', 'DES', 'decrypt'),
    (r'CryptoJS\.TripleDES\.encrypt', '3DES', 'encrypt'),
    (r'CryptoJS\.TripleDES\.decrypt', '3DES', 'decrypt'),
    (r'CryptoJS\.RC4\.encrypt', 'RC4', 'encrypt'),
    (r'CryptoJS\.RC4\.decrypt', 'RC4', 'decrypt'),
    (r'CryptoJS\.Rabbit\.encrypt', 'Rabbit', 'encrypt'),
    (r'CryptoJS\.Rabbit\.decrypt', 'Rabbit', 'decrypt'),
    (r'CryptoJS\.MD5\b', 'MD5', 'digest'),
    (r'CryptoJS\.SHA1\b', 'SHA1', 'digest'),
    (r'CryptoJS\.SHA224\b', 'SHA224', 'digest'),
    (r'CryptoJS\.SHA256\b', 'SHA256', 'digest'),
    (r'CryptoJS\.SHA384\b', 'SHA384', 'digest'),
    (r'CryptoJS\.SHA512\b', 'SHA512', 'digest'),
    (r'CryptoJS\.HmacMD5\b', 'HmacMD5', 'digest'),
    (r'CryptoJS\.HmacSHA1\b', 'HmacSHA1', 'digest'),
    (r'CryptoJS\.HmacSHA256\b', 'HmacSHA256', 'digest'),
    (r'CryptoJS\.HmacSHA512\b', 'HmacSHA512', 'digest'),
    (r'CryptoJS\.enc\.Base64\.stringify', 'Base64', 'encode'),
    (r'CryptoJS\.enc\.Base64\.parse', 'Base64', 'decode'),
    (r'CryptoJS\.enc\.Utf8\.parse', 'Utf8', 'parse'),
    (r'CryptoJS\.enc\.Hex\.stringify', 'Hex', 'encode'),
    (r'CryptoJS\.enc\.Hex\.parse', 'Hex', 'decode'),
    (r'java\.createSymmetricCrypto', 'createSymmetricCrypto', 'create'),
    (r'java\.md5Encode', 'MD5', 'digest'),
    (r'java\.base64Encode', 'Base64', 'encode'),
    (r'java\.base64Decode', 'Base64', 'decode'),
]


def scan_crypto_calls(js_code):
    """扫描JS代码中的加密函数调用

    Args:
        js_code: JS 代码文本

    Returns:
        list[dict]: 每项包含 type/operation/raw/args/position
    """
    calls = []
    for pattern, ctype, operation in _CRYPTO_PATTERNS:
        for m in re.finditer(pattern, js_code):
            # 找到调用后的 '('
            paren_pos = js_code.find('(', m.end())
            if paren_pos == -1:
                continue
            # 括号和函数名之间只允许空白
            between = js_code[m.end():paren_pos]
            if between.strip():
                continue
            args_str, end_pos = _extract_call_args(js_code, paren_pos)
            if args_str is None:
                continue
            calls.append({
                'type': ctype,
                'operation': operation,
                'raw': js_code[m.start():end_pos + 1],
                'args': _split_args(args_str),
                'position': m.start(),
            })
    calls.sort(key=lambda x: x['position'])
    return calls


def extract_key(js_code, call):
    """提取 key/iv/salt 参数

    支持三种来源：硬编码、变量引用、函数返回值

    Args:
        js_code: 完整 JS 代码（用于搜索变量定义）
        call: scan_crypto_calls 返回的调用 dict

    Returns:
        dict: {key, iv, key_source, iv_source}
    """
    args = call.get('args', [])
    result = {'key': None, 'iv': None, 'key_source': None, 'iv_source': None}

    # 对称加密: encrypt(plaintext, key, [options])
    if call['type'] in ('AES', 'DES', '3DES', 'RC4', 'Rabbit') and len(args) >= 2:
        result['key'], result['key_source'] = _resolve_value(js_code, args[1])
        # options 对象中可能含 iv
        if len(args) >= 3:
            options = args[2]
            iv_match = re.search(r'iv\s*:\s*([^,}]+)', options)
            if iv_match:
                result['iv'], result['iv_source'] = _resolve_value(js_code, iv_match.group(1))

    # createSymmetricCrypto(transformation, key, iv)
    elif call['type'] == 'createSymmetricCrypto' and len(args) >= 2:
        result['key'], result['key_source'] = _resolve_value(js_code, args[1])
        if len(args) >= 3:
            result['iv'], result['iv_source'] = _resolve_value(js_code, args[2])

    return result


def determine_mode(call_type, iv, options_str=None):
    """判断 ECB/CBC/CTR/GCM 模式

    基于 IV 是否存在和 padding 类型判断

    Args:
        call_type: 加密类型 (AES/DES/3DES/RC4)
        iv: IV 值，None 表示无 IV
        options_str: 可选，CryptoJS 第三个参数对象文本

    Returns:
        dict: {mode, padding, transformation, iv}
    """
    mode = 'ECB'
    padding = 'PKCS5Padding'

    if options_str:
        # 从 options 提取 mode
        mode_match = re.search(r'mode\s*:\s*CryptoJS\.mode\.(\w+)', options_str)
        if mode_match:
            mode = mode_match.group(1).upper()
        # 从 options 提取 padding
        pad_match = re.search(r'padding\s*:\s*CryptoJS\.pad\.(\w+)', options_str)
        if pad_match:
            pad = pad_match.group(1)
            if pad == 'Pkcs7':
                padding = 'PKCS5Padding'
            elif pad in ('ZeroPadding', 'NoPadding'):
                padding = 'NoPadding'
            elif pad == 'Iso10126':
                padding = 'PKCS5Padding'

    # 有 IV 但没指定 mode → 默认 CBC（CryptoJS 默认）
    if iv and mode == 'ECB':
        mode = 'CBC'
    # ECB 模式忽略 IV
    if mode == 'ECB':
        iv = None

    # 构建 transformation
    algo = 'DESede' if call_type == '3DES' else call_type
    transformation = f'{algo}/{mode}/{padding}'

    return {
        'mode': mode,
        'padding': padding,
        'transformation': transformation,
        'iv': iv,
    }


def generate_decrypt_code(call_type, key, iv, mode):
    """生成 createSymmetricCrypto 调用代码模板

    生成的模板可直接用于书源 ruleContent。

    Args:
        call_type: 加密类型 (AES/DES/3DES)
        key: 密钥值
        iv: IV 值 (ECB 为 None)
        mode: determine_mode 返回的 dict

    Returns:
        dict: {text_decrypt, binary_decrypt, transformation}
    """
    transformation = mode.get('transformation', f'{call_type}/CBC/PKCS5Padding')
    # 优先用 mode 中经过 ECB 检查的 iv
    effective_iv = mode.get('iv', iv)
    key_str = f"'{key}'" if key else "'YOUR_KEY_HERE'"
    iv_str = f"'{effective_iv}'" if effective_iv else 'null'

    text_template = (
        f"// Legado 解密代码模板 - 文本内容\n"
        f"var crypto = java.createSymmetricCrypto('{transformation}', {key_str}, {iv_str});\n"
        f"var decrypted = crypto.decryptStr(encryptedData);\n"
        f"result = decrypted;"
    )

    binary_template = (
        f"// Legado 解密代码模板 - 二进制内容（图片/视频）\n"
        f"var crypto = java.createSymmetricCrypto('{transformation}', {key_str}, {iv_str});\n"
        f"// ⚠️ 图片/视频解密必须用 decrypt() 而非 decryptStr()\n"
        f"var decBytes = crypto.decrypt(encryptedBase64);\n"
        f"var b64 = Packages.android.util.Base64.encodeToString(decBytes, 2);\n"
        f"result = 'data:image/png;base64,' + b64;"
    )

    return {
        'text_decrypt': text_template,
        'binary_decrypt': binary_template,
        'transformation': transformation,
    }


def _generate_summary(analyses):
    """生成分析摘要"""
    types = set(a['type'] for a in analyses)
    has_symmetric = types & {'AES', 'DES', '3DES', 'RC4', 'Rabbit'}
    has_digest = types & {'MD5', 'SHA1', 'SHA256', 'SHA384', 'SHA512'}
    has_hmac = types & {'HmacMD5', 'HmacSHA1', 'HmacSHA256', 'HmacSHA512'}
    has_encoding = types & {'Base64', 'Hex', 'Utf8'}

    parts = []
    if has_symmetric:
        parts.append(f"对称加密: {', '.join(sorted(has_symmetric))}")
    if has_digest:
        parts.append(f"摘要: {', '.join(sorted(has_digest))}")
    if has_hmac:
        parts.append(f"HMAC: {', '.join(sorted(has_hmac))}")
    if has_encoding:
        parts.append(f"编码: {', '.join(sorted(has_encoding))}")
    return '; '.join(parts) if parts else '未知'


def analyze_encryption(js_code, html=None):
    """主函数：输出完整加密分析报告

    Args:
        js_code: JS 代码文本
        html: 可选，HTML 文本（提取内联 script 一并分析）

    Returns:
        dict: 完整加密分析报告，含 has_encryption/call_count/calls/summary
    """
    # 合并 JS 代码（如果提供了 HTML，提取其中的 script 内容）
    full_code = js_code
    if html:
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        full_code = js_code + '\n' + '\n'.join(scripts)

    calls = scan_crypto_calls(full_code)
    if not calls:
        return {
            'has_encryption': False,
            'call_count': 0,
            'calls': [],
            'message': '未检测到加密调用',
        }

    analyses = []
    for call in calls:
        key_info = extract_key(full_code, call)

        # createSymmetricCrypto 的 transformation 在第一个参数中
        if call['type'] == 'createSymmetricCrypto' and len(call.get('args', [])) >= 1:
            transformation = call['args'][0].strip().strip("'\"")
            parts = transformation.split('/')
            mode_info = {
                'mode': parts[1] if len(parts) >= 2 else 'ECB',
                'padding': parts[2] if len(parts) >= 3 else 'PKCS5Padding',
                'transformation': transformation,
                'iv': key_info['iv'],
            }
        else:
            options_str = call['args'][2] if len(call.get('args', [])) >= 3 else None
            mode_info = determine_mode(call['type'], key_info['iv'], options_str)

        # 只为对称加密生成解密代码模板
        decrypt_code = None
        if call['operation'] in ('encrypt', 'decrypt') and call['type'] in ('AES', 'DES', '3DES', 'RC4', 'Rabbit'):
            decrypt_code = generate_decrypt_code(
                call['type'], key_info['key'], mode_info['iv'], mode_info
            )

        analyses.append({
            'type': call['type'],
            'operation': call['operation'],
            'key': key_info['key'],
            'key_source': key_info['key_source'],
            'iv': key_info['iv'],
            'iv_source': key_info['iv_source'],
            'mode': mode_info['mode'],
            'padding': mode_info['padding'],
            'transformation': mode_info['transformation'],
            'decrypt_code': decrypt_code,
            'raw_call': call['raw'],
        })

    return {
        'has_encryption': True,
        'call_count': len(calls),
        'calls': analyses,
        'summary': _generate_summary(analyses),
    }


# ── 自检 ──────────────────────────────────────────────────

if __name__ == '__main__':
    # 正常用例：AES-CBC 加密，密钥通过变量+Utf8.parse
    js1 = '''
    var key = CryptoJS.enc.Utf8.parse("1234567890123456");
    var iv = CryptoJS.enc.Utf8.parse("6543210987654321");
    var encrypted = CryptoJS.AES.encrypt("hello", key, {mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7, iv: iv});
    '''
    r1 = analyze_encryption(js1)
    assert r1['has_encryption'] is True
    aes_calls = [c for c in r1['calls'] if c['type'] == 'AES']
    assert len(aes_calls) == 1
    assert aes_calls[0]['key'] == '1234567890123456'
    assert aes_calls[0]['mode'] == 'CBC'
    assert aes_calls[0]['iv'] == '6543210987654321'
    assert aes_calls[0]['decrypt_code'] is not None

    # 边界用例：DES-ECB 无 IV，硬编码密钥
    js2 = 'CryptoJS.DES.encrypt("text", "8charkey", {mode: CryptoJS.mode.ECB, padding: CryptoJS.pad.Pkcs7})'
    r2 = analyze_encryption(js2)
    assert r2['has_encryption'] is True
    des_calls = [c for c in r2['calls'] if c['type'] == 'DES']
    assert len(des_calls) == 1
    assert des_calls[0]['key'] == '8charkey'
    assert des_calls[0]['key_source'] == 'hardcoded'
    assert des_calls[0]['mode'] == 'ECB'
    assert des_calls[0]['iv'] is None
    assert des_calls[0]['transformation'] == 'DES/ECB/PKCS5Padding'

    print('[自检] 2 个用例通过')
