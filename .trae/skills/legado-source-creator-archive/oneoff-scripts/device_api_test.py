#!/usr/bin/env python3
"""快速验证真机 API 可用性"""
import requests
import json
import sys

HOST = "127.0.0.1"
PORT = 1122
BASE = f"http://{HOST}:{PORT}"
OUT = "device_api_test_result.txt"

def main():
    with open(OUT, "w", encoding="utf-8") as f:
        # 1. 连接测试
        try:
            r = requests.get(f"{BASE}/getBookSources", timeout=10, stream=True)
            f.write(f"getBookSources: {r.status_code}\n")
            chunk = next(r.iter_content(2048))
            preview = chunk.decode("utf-8", errors="replace")[:200]
            f.write(f"Data preview: {preview}\n")
            r.close()
        except Exception as e:
            f.write(f"getBookSources error: {e}\n")

        # 2. 获取少量书源信息
        try:
            r = requests.get(f"{BASE}/getBookSources", timeout=15)
            data = r.json()
            if isinstance(data, dict) and "data" in data:
                sources = data["data"]
            else:
                sources = data if isinstance(data, list) else []
            f.write(f"Total sources: {len(sources)}\n")
            # 找笔趣阁
            bqg = [s for s in sources if "xbiquge" in s.get("bookSourceUrl", "")]
            if bqg:
                f.write(f"Found {len(bqg)} xbiquge sources\n")
                test_src = bqg[0]
                f.write(f"Test source: {test_src.get('bookSourceName')}\n")
            else:
                test_src = sources[0] if sources else None
                f.write(f"Using first source: {test_src.get('bookSourceName','?') if test_src else 'None'}\n")
        except Exception as e:
            f.write(f"getBookSources error: {e}\n")
            test_src = None

        # 3. testBookSource
        if test_src:
            f.write("Calling testBookSource...\n")
            f.flush()
            try:
                r2 = requests.post(f"{BASE}/testBookSource", json=test_src, timeout=60)
                f.write(f"testBookSource: status={r2.status_code} len={len(r2.text)}\n")
                f.write(f"Result: {r2.text[:500]}\n")
            except Exception as e:
                f.write(f"testBookSource error: {e}\n")

        # 4. WebSocket 端口检查
        try:
            import websocket
            ws = websocket.create_connection(f"ws://{HOST}:{PORT+1}", timeout=5)
            ws.close()
            f.write(f"WebSocket {PORT+1}: OK\n")
        except Exception as e:
            f.write(f"WebSocket {PORT+1}: {str(e)[:100]}\n")

    # 打印到stdout
    with open(OUT, "r", encoding="utf-8") as f:
        print(f.read())

if __name__ == "__main__":
    main()
