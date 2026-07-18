#!/usr/bin/env python3
"""检查数据库源数量"""
import httpx, json

BASE = "http://127.0.0.1:8765"
resp = httpx.get(f"{BASE}/api/sources", params={"page":1,"page_size":1,"source_type":"book"}, timeout=10)
data = resp.json()
print(f"book total={data['data']['total']}")

resp2 = httpx.get(f"{BASE}/api/sources", params={"page":1,"page_size":1,"source_type":"rss"}, timeout=10)
data2 = resp2.json()
print(f"rss total={data2['data']['total']}")
