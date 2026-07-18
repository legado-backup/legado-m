#!/usr/bin/env python3
"""End-to-end test with real book sources."""
import json, sys, requests

BASE = "http://127.0.0.1:8080"
results = []

def log(msg):
    results.append(msg)
    print(msg)

# Load real sources
with open("test_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

log(f"=== 1. IMPORT {len(sources)} real book sources ===")
ids = []
for i, s in enumerate(sources):
    r = requests.post(f"{BASE}/api/sources", json={"source_json": json.dumps(s, ensure_ascii=False)})
    d = r.json()
    if d["ok"]:
        ids.append(d["data"]["id"])
        log(f"  [{i+1}] OK id={d['data']['id']} name={d['data']['source_name']}")
    else:
        log(f"  [{i+1}] FAIL: {d.get('error',{}).get('message','?')[:100]}")

log(f"\n=== 2. LIST sources ===")
r = requests.get(f"{BASE}/api/sources", params={"page": 1, "page_size": 20})
d = r.json()
log(f"  total={d['data']['total']}")
for it in d["data"]["items"]:
    log(f"  id={it['id']} name={it['source_name']} type={it['source_type']} enabled={it['enabled']}")

log(f"\n=== 3. SEARCH ===")
r = requests.get(f"{BASE}/api/sources", params={"search": "番茄"})
d = r.json()
log(f"  '番茄' found: {d['data']['total']}")

if ids:
    sid = ids[0]
    log(f"\n=== 4. DETAIL (id={sid}) ===")
    r = requests.get(f"{BASE}/api/sources/{sid}")
    d = r.json()
    if d["ok"]:
        dd = d["data"]
        log(f"  name={dd['source_name']} url={dd['source_url']} group={dd.get('source_group','')}")
        log(f"  has_login={dd.get('has_login')} json_len={len(dd.get('source_json',''))}")

    log(f"\n=== 5. VALIDATE ===")
    r = requests.post(f"{BASE}/api/sources/validate", json={"source_json": dd["source_json"]})
    v = r.json()
    log(f"  valid={v['data']['valid']} type={v['data'].get('source_type')}")

    log(f"\n=== 6. TOGGLE ===")
    r = requests.patch(f"{BASE}/api/sources/{sid}/toggle?enabled=false")
    log(f"  disable: ok={r.json()['ok']}")
    r = requests.patch(f"{BASE}/api/sources/{sid}/toggle?enabled=true")
    log(f"  enable: ok={r.json()['ok']}")

    log(f"\n=== 7. EXPORT single ===")
    r = requests.post(f"{BASE}/api/sources/{sid}/export")
    d = r.json()
    log(f"  ok={d['ok']} keys={len(d['data'])} name={d['data'].get('bookSourceName','?')}")

    log(f"\n=== 8. BATCH EXPORT ===")
    r = requests.post(f"{BASE}/api/sources/batch-export", json={"source_ids": ids})
    d = r.json()
    log(f"  ok={d['ok']} count={d['data']['count']}")

    log(f"\n=== 9. BY DOMAIN ===")
    r = requests.get(f"{BASE}/api/sources/by-domain", params={"domain_key": "snssdk"})
    d = r.json()
    log(f"  snssdk: {len(d['data'])} found")

log(f"\n=== 10. STATS ===")
r = requests.get(f"{BASE}/api/stats/overview")
d = r.json()
log(f"  total={d['data']['total']} book={d['data']['book_count']} rss={d['data']['rss_count']}")

log(f"\n=== 11. GROUPS ===")
r = requests.get(f"{BASE}/api/sources/groups")
d = r.json()
log(f"  {d['data']}")

# Pass/fail summary
fails = [r for r in results if "FAIL" in r]
log(f"\n=== SUMMARY: {len(results)} tests, {len(fails)} failures ===")
if fails:
    for f in fails:
        log(f"  {f}")
else:
    log("  ALL PASSED!")

with open("e2e_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
