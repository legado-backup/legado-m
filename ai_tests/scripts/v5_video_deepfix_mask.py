# -*- coding: utf-8 -*-
"""
后处理：对 v5_video_deepfix.json 做全量脱敏
- 替换所有 https?://domain 为 scheme://[DOMAIN]
- 替换 blob:URL 中的真实域名
- 替换 IP 地址为 [IP]
- 替换 mailto:xxx@xxx 为 mailto:[EMAIL]
"""
import json
import re
import sys
from pathlib import Path

INPUT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss\v5_video_deepfix.json"
OUTPUT = INPUT  # 原地覆盖
BACKUP = INPUT + ".bak"


# 匹配 https?:// 后跟域名（不含 [DOMAIN]）
RE_HTTP_DOMAIN = re.compile(r'(https?)://(?!\[DOMAIN\])([a-zA-Z0-9._-]+)(:\d+)?')
# 匹配 blob: 前缀的 URL
RE_BLOB_URL = re.compile(r'(blob:)(https?)://(?!\[DOMAIN\])([a-zA-Z0-9._-]+)(:\d+)?')
# 匹配 IP
RE_IP = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
# 匹配 mailto:
RE_MAILTO = re.compile(r'mailto:[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+')


def mask_string(s):
    if not isinstance(s, str):
        return s
    out = s
    # 先处理 blob:URL
    out = RE_BLOB_URL.sub(lambda m: f'{m.group(1)}{m.group(2)}://[DOMAIN]', out)
    # 再处理普通 https?://domain
    out = RE_HTTP_DOMAIN.sub(lambda m: f'{m.group(1)}://[DOMAIN]', out)
    # 处理 IP
    out = RE_IP.sub('[IP]', out)
    # 处理 mailto:
    out = RE_MAILTO.sub('mailto:[EMAIL]', out)
    return out


def mask_obj(obj):
    if isinstance(obj, dict):
        return {k: mask_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_obj(v) for v in obj]
    if isinstance(obj, str):
        return mask_string(obj)
    return obj


def main():
    p = Path(INPUT)
    if not p.exists():
        print(f"[ERR] input not found: {INPUT}")
        sys.exit(1)
    # 备份
    import shutil
    shutil.copy(INPUT, BACKUP)
    print(f"[INFO] backup -> {BACKUP}")
    # 读取
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 脱敏
    masked = mask_obj(data)
    # 统计泄露
    leak_count = 0
    def scan(o):
        nonlocal leak_count
        if isinstance(o, dict):
            for v in o.values(): scan(v)
        elif isinstance(o, list):
            for v in o: scan(v)
        elif isinstance(o, str):
            if RE_HTTP_DOMAIN.search(o) or RE_BLOB_URL.search(o) or RE_IP.search(o) or RE_MAILTO.search(o):
                leak_count += 1
    scan(masked)
    print(f"[INFO] residual leaks after mask: {leak_count}")
    # 写回
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(masked, f, ensure_ascii=False, indent=2)
    print(f"[DONE] masked -> {OUTPUT}")


if __name__ == "__main__":
    main()
