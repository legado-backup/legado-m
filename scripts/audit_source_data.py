#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实书源/订阅源数据阻断器（内容级，pre-push 卡点）。

判定：同一文件同时含「源定义字段」与「规则/名称字段」，且存在非保留域的真实地址
⇒ 视为真实源数据（业务数据），禁止入库/推送。

性能：用单次 `git cat-file --batch` 一次性读入本次推送涉及的文本文件，
避免逐文件 spawn，也避免全树 grep。

安全约束：只输出违规文件路径，绝不输出命中地址/源名称（output-safety）。

用法：
    python scripts/audit_source_data.py --rev <commit> --paths-file <file>
    <file> 每行一个待检文件路径（相对仓库根）。

退出码：0 = 通过；1 = 命中违规。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# 白名单为空：内置默认源 `assets/defaultData/bookSources.json` 已于 2026-10-28 移除
# （代码无任何引用，属死资产；且内含真实源地址，不符合"远端零真实源数据"口径）
ALLOWLIST: set[str] = set()

TEXT_EXT = (".json", ".txt", ".md", ".js", ".kt", ".java", ".xml", ".yaml", ".yml")

URL_FIELD_SIG = re.compile(r'"(bookSourceUrl|rssSourceUrl|sourceUrl)"')
RULE_FIELD_SIG = re.compile(
    r'"(ruleToc|ruleContent|ruleArticles|ruleBookInfo|ruleSearch|bookSourceName|rssSourceName)"'
)
RESERVED_HOST = re.compile(
    r"^https?://(example\.(com|org|net)|localhost|127\.0\.0\.1)([:/]|$)"
)
RESERVED_HOST_ALT = re.compile(
    r"^https?://([a-z0-9_-]+\.)*(test|invalid|example)([:/]|$)"
)
URL_PATTERN = re.compile(r'https?://[^"/\\\s]+')

MAX_BLOB_BYTES = 2 * 1024 * 1024


def read_blobs(rev: str, paths: list[str]) -> dict[str, bytes]:
    """用一次 cat-file --batch 读入多个文件内容；缺失/超限的跳过。"""
    if not paths:
        return {}
    request = "\n".join(f"{rev}:{p}" for p in paths) + "\n"
    proc = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=request.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        return {}

    data = proc.stdout
    pos = 0
    index = 0
    result: dict[str, bytes] = {}
    while pos < len(data) and index < len(paths):
        end = data.find(b"\n", pos)
        if end < 0:
            break
        header = data[pos:end].decode("utf-8", "ignore")
        pos = end + 1
        parts = header.split(" ")
        if len(parts) != 3 or parts[1] != "blob":
            # 形如 "<spec> missing"：该文件在该提交不存在
            index += 1
            continue
        try:
            size = int(parts[2])
        except ValueError:
            index += 1
            continue
        body = data[pos:pos + size]
        pos += size + 1  # 内容后跟一个换行
        path = paths[index]
        index += 1
        if size > MAX_BLOB_BYTES:
            continue
        result[path] = body
    return result


def is_real_source_data(text: str) -> bool:
    if not URL_FIELD_SIG.search(text):
        return False
    if not RULE_FIELD_SIG.search(text):
        return False
    for url in URL_PATTERN.findall(text):
        if RESERVED_HOST.match(url) or RESERVED_HOST_ALT.match(url):
            continue
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="阻断真实书源/订阅源数据")
    parser.add_argument("--rev", required=True, help="待检提交（如 local sha）")
    parser.add_argument("--paths-file", required=True, help="每行一个待检文件路径")
    args = parser.parse_args()

    with open(args.paths_file, encoding="utf-8", errors="ignore") as fh:
        pushed = [line.strip() for line in fh if line.strip()]

    targets = [
        p for p in pushed
        if p not in ALLOWLIST and p.lower().endswith(TEXT_EXT)
    ]

    blobs = read_blobs(args.rev, targets)

    violations: list[str] = []
    for path, raw in blobs.items():
        text = raw.decode("utf-8", "ignore")
        if is_real_source_data(text):
            violations.append(path)

    for path in sorted(violations):
        print(path)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
