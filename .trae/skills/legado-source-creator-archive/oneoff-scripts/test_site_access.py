#!/usr/bin/env python3
"""验证测试书源的网站是否可访问"""
import httpx
import time

OUT = "f:\\myself\\github\\WeAgentChat\\temp\\legado\\.trae\\skills\\legado-source-creator\\scripts\\site_check_result.txt"

# 之前测试的书源URL
TEST_URLS = [
    ("肉文阁", "https://m.rouwenge.com/"),
    ("七猫读书网", "https://www.pokpets.net"),
    ("纵横中文网", "https://search.zongheng.com/"),
    ("恋小说", "http://www.lianxiaoshuo.com/"),
    ("笔趣阁[zx]", "https://www.zxbiquge.net/"),
    ("起点中文", "https://m.qidian.com"),
    ("晋江APP", "http://app.jjwxc.org/"),
]

def main():
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("电脑端网站可访问性检查\n")
        f.write("=" * 60 + "\n\n")

        client = httpx.Client(timeout=15, follow_redirects=True, verify=False)

        for name, url in TEST_URLS:
            f.write(f"[{name}] {url}\n")
            start = time.time()
            try:
                resp = client.get(url)
                elapsed = time.time() - start
                f.write(f"  状态: HTTP {resp.status_code}, 耗时: {elapsed:.1f}s, 长度: {len(resp.text)}\n")
                if resp.status_code == 200 and len(resp.text) > 100:
                    f.write(f"  结果: ✓ 可访问\n")
                    # 检查是否有搜索相关的表单
                    if "search" in resp.text.lower():
                        f.write(f"  搜索: ✓ 有搜索功能\n")
                else:
                    f.write(f"  结果: ✗ 响应异常\n")
            except httpx.ConnectError as e:
                elapsed = time.time() - start
                f.write(f"  状态: 连接失败({elapsed:.1f}s) {e}\n")
                f.write(f"  结果: ✗ DNS/连接失败\n")
            except Exception as e:
                elapsed = time.time() - start
                f.write(f"  状态: 异常({elapsed:.1f}s) {type(e).__name__}: {e}\n")
                f.write(f"  结果: ✗\n")
            f.write("\n")

        # 再测几个常见的笔趣阁变体
        f.write("\n--- 额外检查常见小说站 ---\n\n")
        EXTRA_URLS = [
            ("笔趣阁www.biquge.com.cn", "https://www.biquge.com.cn/"),
            ("笔趣阁www.biquge5200.cc", "https://www.biquge5200.cc/"),
            ("小说www.xiaoshuowu.com", "https://www.xiaoshuowu.com/"),
            ("书旗网", "https://www.shuqi.com/"),
            ("百度", "https://www.baidu.com/"),
        ]
        for name, url in EXTRA_URLS:
            f.write(f"[{name}] {url}\n")
            start = time.time()
            try:
                resp = client.get(url)
                elapsed = time.time() - start
                f.write(f"  HTTP {resp.status_code}, {elapsed:.1f}s, {len(resp.text)} bytes\n")
                f.write(f"  结果: {'✓' if resp.status_code == 200 else '✗'}\n")
            except Exception as e:
                elapsed = time.time() - start
                f.write(f"  失败({elapsed:.1f}s): {type(e).__name__}\n")
            f.write("\n")

        client.close()
        f.write("[DONE]\n")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()
