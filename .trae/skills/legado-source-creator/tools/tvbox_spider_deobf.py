# -*- coding: utf-8 -*-
"""
TVBox/CatVod spider jar 反混淆工具
=================================
用途：反编译 CatVod spider jar 后，破解 `com.github.catvod.spider.obf.Str.u()` 字符串混淆，
      批量还原全部站点接口，或输出单类反混淆源码。

背景：TVBox 配置（`前缀+**+Base64`，sites[].type=3，api=csp_XXX）无法直接转 Legado 源，
      需从 spider jar 提取真实接口。详见 references/special-scenarios/tvbox-spider-reverse-engineering.md

用法：
  # 1) 全量扫描：列出每个 spider 类里疑似接口/字段的明文
  python tvbox_spider_deobf.py --src <decompiled/sources/com/github/catvod/spider> --scan --out scan.txt

  # 2) 单类反混淆：把 java 里的 Str.u("...") 就地替换为明文，便于阅读
  python tvbox_spider_deobf.py --src <spider_dir> --class Bili --deobf --out clean_Bili.java

  # 3) 单类明文清单：只打印某类的全部解密字符串（按出现顺序）
  python tvbox_spider_deobf.py --src <spider_dir> --class Bili --strings

参数：
  --filter  仅扫描命中该关键词的行（默认 http / .php / m3u8 / /api）
  --top N   扫描模式下每类最多输出 N 行（默认 40，0=不限）
"""
import argparse
import os
import re
import sys

# com/github/catvod/spider/obf/Str.java 的密钥（无符号）
KEY = (0xA5, 0x3C, 0x7E, 0x19)
# Str.u(): byte b = (char)((c - 19968) & 255); b ^= a[i & 3]
STR_U_RE = re.compile(r'Str\.u\("((?:[^"\\]|\\.)*)"\)')
DEFAULT_FILTER = ("http", ".php", "m3u8", "/api")


def decrypt(s):
    """还原 Str.u() 密文为明文。"""
    buf = bytearray()
    for i, ch in enumerate(s):
        buf.append(((ord(ch) - 19968) & 0xFF) ^ KEY[i & 3])
    return buf.decode("utf-8", "replace")


def _escape(txt):
    return (txt.replace("\\", "\\\\")
               .replace('"', '\\"')
               .replace("\r", "")
               .replace("\n", "\\n"))


def scan_spider_dir(src, out, filter_kw, top):
    """全量扫描：按类输出疑似接口明文。"""
    files = sorted(f for f in os.listdir(src) if f.endswith(".java"))
    hits = 0
    with open(out, "w", encoding="utf-8", errors="replace") as w:
        for fn in files:
            try:
                code = open(os.path.join(src, fn), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            found = STR_U_RE.findall(code)
            if not found:
                continue
            plain = [decrypt(x) for x in found]
            interesting = [d for d in dict.fromkeys(plain)
                           if any(k in d for k in filter_kw)]
            if not interesting:
                continue
            if top:
                interesting = interesting[:top]
            hits += 1
            w.write("=" * 70 + "\n")
            w.write("### %s   (Str.u 共%d处)\n" % (fn[:-5], len(found)))
            for d in interesting:
                w.write("   " + d[:300] + "\n")
    print("[scan] 命中类数: %d -> %s" % (hits, out))


def dump_strings(src, cls, out=None):
    """单类：按出现顺序打印全部解密字符串。"""
    code = open(os.path.join(src, cls + ".java"), encoding="utf-8", errors="replace").read()
    found = STR_U_RE.findall(code)
    lines = [decrypt(x) for x in found]
    if out:
        with open(out, "w", encoding="utf-8", errors="replace") as w:
            w.write("### %s  (Str.u 共%d处)\n" % (cls, len(found)))
            for d in lines:
                w.write("   " + d[:300] + "\n")
        print("[strings] %s -> %s" % (cls, out))
    else:
        print("### %s (共%d处)" % (cls, len(found)))
        for d in lines:
            print("  ", d[:300])
    return lines


def deobf_class(src, cls, out):
    """单类：写出去混淆后的 java 源码。"""
    code = open(os.path.join(src, cls + ".java"), encoding="utf-8", errors="replace").read()

    def rep(m):
        return '"%s"' % _escape(decrypt(m.group(1)))

    clean = STR_U_RE.sub(rep, code)
    with open(out, "w", encoding="utf-8", errors="replace") as w:
        w.write(clean)
    print("[deobf] %s -> %s (%d chars)" % (cls, out, len(clean)))


def main():
    ap = argparse.ArgumentParser(description="TVBox spider jar 反混淆工具")
    ap.add_argument("--src", required=True, help="反编译产物目录（含 Xxx.java）")
    ap.add_argument("--class", dest="cls", help="目标类名（不含 .java）")
    ap.add_argument("--scan", action="store_true", help="全量扫描模式")
    ap.add_argument("--deobf", action="store_true", help="单类反混淆输出")
    ap.add_argument("--strings", action="store_true", help="单类明文清单")
    ap.add_argument("--out", help="输出文件")
    ap.add_argument("--filter", default=",".join(DEFAULT_FILTER), help="扫描关键词，逗号分隔")
    ap.add_argument("--top", type=int, default=40, help="扫描模式下每类最多输出行数，0=不限")
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        print("ERR: --src 目录不存在: %s" % args.src, file=sys.stderr)
        return 2

    if args.scan:
        out = args.out or "deobf_scan.txt"
        scan_spider_dir(args.src, out, tuple(k for k in args.filter.split(",") if k), args.top)
    elif args.cls and args.deobf:
        deobf_class(args.src, args.cls, args.out or ("clean_%s.java" % args.cls))
    elif args.cls and args.strings:
        dump_strings(args.src, args.cls, args.out)
    elif args.cls:
        dump_strings(args.src, args.cls, args.out)
    else:
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
