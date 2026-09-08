"""{{page}}分页复现——本地HTTP服务器：记录每个请求的完整path+query到日志文件，
返回含页码标记的最小书源列表HTML。仅用于确定性观测AnalyzeUrl对{{page}}/{{key}}的替换结果。"""
import http.server
import json
import sys
from urllib.parse import urlparse, parse_qs

PORT = 18093
LOG = os_log = r"F:\myself\github\WeAgentChat\temp\legado\ai_tests\testdata\page_repro\requests.log"


def build_html(pg: int, kw: str) -> str:
    items = []
    for i in range(1, 4):
        items.append(
            f'<div class="book"><div class="name">P{pg}_BOOK_{i}_{kw}</div>'
            f'<div class="author">author{pg}</div>'
            f'<div class="link">http://127.0.0.1:18093/book/{pg}_{i}</div></div>'
        )
    return "<html><body>" + "".join(items) + "</body></html>"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        pg = q.get("pg", ["MISS"])[0]
        kw = q.get("kw", ["NONE"])[0]
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"path": u.path, "query_keys": sorted(q.keys()), "pg": pg, "kw_len": len(kw)}) + "\n")
        body = build_html(int(pg) if str(pg).isdigit() else 0, kw).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    open(LOG, "w").close()
    print(f"listening on {PORT}, log={LOG}")
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
