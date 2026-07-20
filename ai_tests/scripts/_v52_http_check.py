# -*- coding: utf-8 -*-
"""HTTP 检测 V5.2 中源的可访问性(只输出技术信息,不输出业务字段)"""
import json
import socket
import ssl
import urllib.request
import urllib.error
from collections import Counter

ROOT = r"f:\myself\github\WeAgentChat\temp\legado\output\rss"
with open(f"{ROOT}\\optimized_v5_2_stable.json", "r", encoding="utf-8") as f:
    v52 = json.load(f)

print(f"V5.2 总源数: {len(v52)}")
# 用 PC 网络(非模拟器)做 HTTP 检测, 因为模拟器网络可能更不稳
UA = "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

def check_url(url, timeout=5):
    """返回 (status_code, err_type)"""
    if not url or not isinstance(url, str):
        return None, "empty_url"
    if not url.startswith("http"):
        return None, "not_http"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        # 4xx/5xx 也算可访问(站点响应了)
        return e.code, None
    except urllib.error.URLError as e:
        return None, f"url_err:{type(e.reason).__name__}"
    except socket.timeout:
        return None, "timeout"
    except socket.gaierror as e:
        return None, f"dns_err"
    except ssl.SSLError as e:
        return None, f"ssl_err"
    except ConnectionError as e:
        return None, "conn_err"
    except Exception as e:
        return None, f"other:{type(e).__name__}"

# 抽样检测: 前50个字段完整的源
candidates = []
for i, s in enumerate(v52):
    url = s.get("sourceUrl", "")
    ra = (s.get("ruleArticles") or "").strip()
    rl = (s.get("ruleLink") or "").strip()
    rt = (s.get("ruleTitle") or "").strip()
    if url.startswith("http") and ra and rl and rt:
        candidates.append(i)
print(f"字段完整+http源总数: {len(candidates)}")

# 检测前50个
print(f"\n开始 HTTP HEAD 检测前50个候选源...")
results = []
status_counter = Counter()
err_counter = Counter()
accessible_idx = []
for n, idx in enumerate(candidates[:50]):
    s = v52[idx]
    url = s.get("sourceUrl", "")
    status, err = check_url(url, timeout=5)
    if status is not None:
        status_counter[status] += 1
        if 200 <= status < 500:
            accessible_idx.append((idx, status))
            print(f"  [{n+1}/50] idx={idx} status={status} OK")
        else:
            err_counter[f"http_{status}"] += 1
            print(f"  [{n+1}/50] idx={idx} status={status}")
    else:
        err_counter[err] += 1
        print(f"  [{n+1}/50] idx={idx} err={err}")

print(f"\n=== 检测统计 ===")
print(f"可访问(status=2xx-4xx)源数: {len(accessible_idx)}")
print(f"status分布: {dict(status_counter)}")
print(f"错误分布: {dict(err_counter)}")

# 输出可访问源的 idx 列表
print(f"\n=== 可访问源 idx 列表(前20) ===")
print([idx for idx, _ in accessible_idx[:20]])
