#!/usr/bin/env python3
"""Real device integration test."""
import requests, json, sys

BASE = "http://127.0.0.1:8080"
out = []

def log(msg):
    out.append(msg)
    print(msg, flush=True)

# 1. Add device
log("=== 1. 添加真机设备 ===")
r = requests.post(f"{BASE}/api/devices", json={"name": "Legado真机", "address": "127.0.0.1:1122"})
d = r.json()
log(f"  ok={d.get('ok')} data={json.dumps(d.get('data',d), ensure_ascii=False)[:200]}")

# Get device ID
r = requests.get(f"{BASE}/api/devices")
devices = r.json().get("data", [])
dev_id = None
for dev in devices:
    if dev.get("name") == "Legado真机":
        dev_id = dev["id"]
        break
log(f"  device_id={dev_id}")

if not dev_id:
    log("  ERROR: Device not found, aborting")
    sys.exit(1)

# 2. Test connection
log("\n=== 2. 测试真机连接 ===")
r = requests.post(f"{BASE}/api/devices/{dev_id}/test-connection", timeout=30)
d = r.json()
log(f"  ok={d.get('ok')} data={json.dumps(d.get('data',{}), ensure_ascii=False)[:300]}")

# 3. Pull book sources
log("\n=== 3. 从真机拉取书源 ===")
r = requests.post(f"{BASE}/api/devices/{dev_id}/pull", json={"source_type": "book"}, timeout=180)
d = r.json()
log(f"  ok={d.get('ok')}")
if d.get("ok"):
    dd = d.get("data", {})
    log(f"  pulled={dd.get('pulled_count','?')} saved={dd.get('saved_count','?')} total={dd.get('total_device_sources','?')}")
else:
    log(f"  error={d.get('error',{}).get('message',str(d))[:200]}")

# 4. Pull RSS
log("\n=== 4. 从真机拉取订阅源 ===")
r = requests.post(f"{BASE}/api/devices/{dev_id}/pull", json={"source_type": "rss"}, timeout=180)
d = r.json()
log(f"  ok={d.get('ok')}")
if d.get("ok"):
    dd = d.get("data", {})
    log(f"  pulled={dd.get('pulled_count','?')} saved={dd.get('saved_count','?')}")

# 5. Stats
log("\n=== 5. 拉取后统计 ===")
r = requests.get(f"{BASE}/api/stats/overview")
d = r.json()
if d["ok"]:
    dd = d["data"]
    log(f"  total={dd['total']} book={dd['book_count']} rss={dd['rss_count']}")

# 6. Push
log("\n=== 6. 推送源到真机 ===")
r = requests.get(f"{BASE}/api/sources", params={"page":1,"page_size":1})
items = r.json().get("data",{}).get("items",[])
src_id = items[0]["id"] if items else None
if src_id:
    r = requests.post(f"{BASE}/api/devices/{dev_id}/push", json={"source_ids": [src_id], "source_type": "book"}, timeout=15)
    d = r.json()
    log(f"  ok={d.get('ok')} data={json.dumps(d.get('data',d.get('error',{})), ensure_ascii=False)[:300]}")

# 7. Debug compare
log("\n=== 7. 真机对比调试 ===")
if src_id:
    r = requests.post(f"{BASE}/api/debug/compare", json={"source_id": src_id, "source_type": "book"}, timeout=15)
    d = r.json()
    log(f"  ok={d.get('ok')}")
    if d.get("ok"):
        dd = d.get("data", {})
        log(f"  device_result={json.dumps(dd.get('device_result',{}), ensure_ascii=False)[:200]}")
    else:
        log(f"  error={d.get('error',{}).get('message','?')[:200]}")

log("\n=== 真机测试完成 ===")

with open("device_test_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
