#!/usr/bin/env python3
"""清理死源+空壳源：DNS检查→删除死源→删除空壳源→验证"""
import asyncio, httpx, time
from urllib.parse import urlparse

async def main():
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        # 1. 获取源列表
        print('获取源列表...')
        r = await client.get('http://127.0.0.1:1122/getBookSources')
        book_sources = r.json().get('data', [])
        r = await client.get('http://127.0.0.1:1122/getRssSources')
        rss_sources = r.json().get('data', [])
        print(f'书源: {len(book_sources)}, 订阅源: {len(rss_sources)}')

        # 2. 提取域名
        book_domains = {}
        for src in book_sources:
            url = src.get('bookSourceUrl', '')
            try:
                base = url.split('#')[0].strip()
                if '://' not in base: base = 'http://' + base
                domain = urlparse(base).hostname or ''
                domain = domain.lower().replace('www.', '')
                if domain:
                    book_domains.setdefault(domain, []).append(url)
            except: pass

        rss_domains = {}
        for src in rss_sources:
            url = src.get('sourceUrl', '')
            try:
                base = url.split('#')[0].strip()
                if '://' not in base: base = 'http://' + base
                domain = urlparse(base).hostname or ''
                domain = domain.lower().replace('www.', '')
                if domain:
                    rss_domains.setdefault(domain, []).append(url)
            except: pass

        all_domains = set(book_domains.keys()) | set(rss_domains.keys())
        print(f'唯一域名: {len(all_domains)} 个')

        # 3. DNS检查
        import socket
        sem = asyncio.Semaphore(200)

        async def _check(d):
            async with sem:
                try:
                    loop = asyncio.get_event_loop()
                    await asyncio.wait_for(loop.getaddrinfo(d, None), timeout=8.0)
                    return d, True
                except:
                    return d, False

        print('DNS检查(200并发)...')
        start = time.time()
        tasks = [_check(d) for d in all_domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        dead_set = {r[0] for r in results if isinstance(r, tuple) and not r[1]}
        print(f'DNS完成 ({time.time()-start:.1f}s), 死域名: {len(dead_set)} 个')

        # 4. 收集死源URL
        dead_book_urls = []
        for d, urls in book_domains.items():
            if d in dead_set:
                dead_book_urls.extend(urls)

        dead_rss_urls = []
        for d, urls in rss_domains.items():
            if d in dead_set:
                dead_rss_urls.extend(urls)

        print(f'死书源: {len(dead_book_urls)}, 死订阅源: {len(dead_rss_urls)}')

        # 5. 识别空壳书源(无searchUrl+无exploreUrl+无ruleSearch.bookList, 且非死源)
        empty_book_urls = []
        for src in book_sources:
            has_search = bool(src.get('searchUrl'))
            has_explore = bool(src.get('exploreUrl'))
            rule_search = src.get('ruleSearch', {})
            has_booklist = bool(rule_search.get('bookList')) if isinstance(rule_search, dict) else False
            if not has_search and not has_explore and not has_booklist:
                url = src.get('bookSourceUrl', '')
                domain = ''
                try:
                    base = url.split('#')[0].strip()
                    if '://' not in base: base = 'http://' + base
                    domain = urlparse(base).hostname or ''
                    domain = domain.lower().replace('www.', '')
                except: pass
                if domain not in dead_set:
                    empty_book_urls.append(url)

        print(f'空壳书源(非死源): {len(empty_book_urls)}')

        # 6. 执行删除
        total_deleted = 0

        # 删除死书源
        if dead_book_urls:
            batch_size = 500
            for i in range(0, len(dead_book_urls), batch_size):
                batch = dead_book_urls[i:i+batch_size]
                payload = [{'bookSourceUrl': u} for u in batch]
                try:
                    r = await client.post('http://127.0.0.1:1122/deleteBookSources', json=payload, timeout=60)
                    total_deleted += len(batch)
                    print(f'  死书源删除: {total_deleted}/{len(dead_book_urls)}')
                except Exception as e:
                    print(f'  删除失败: {e}')

        # 删除空壳书源
        if empty_book_urls:
            batch_size = 500
            for i in range(0, len(empty_book_urls), batch_size):
                batch = empty_book_urls[i:i+batch_size]
                payload = [{'bookSourceUrl': u} for u in batch]
                try:
                    r = await client.post('http://127.0.0.1:1122/deleteBookSources', json=payload, timeout=60)
                    total_deleted += len(batch)
                    print(f'  空壳书源删除: {min(i+batch_size, len(empty_book_urls))}/{len(empty_book_urls)}')
                except Exception as e:
                    print(f'  删除失败: {e}')

        # 删除死订阅源
        if dead_rss_urls:
            batch_size = 200
            for i in range(0, len(dead_rss_urls), batch_size):
                batch = dead_rss_urls[i:i+batch_size]
                payload = [{'sourceUrl': u} for u in batch]
                try:
                    r = await client.post('http://127.0.0.1:1122/deleteRssSources', json=payload, timeout=60)
                    total_deleted += len(batch)
                    print(f'  死订阅源删除: {min(i+batch_size, len(dead_rss_urls))}/{len(dead_rss_urls)}')
                except Exception as e:
                    print(f'  删除失败: {e}')

        print(f'\n清理完成! 共删除 {total_deleted} 个源')

        # 7. 验证剩余数量
        r = await client.get('http://127.0.0.1:1122/getBookSources')
        remaining_book = len(r.json().get('data', []))
        r = await client.get('http://127.0.0.1:1122/getRssSources')
        remaining_rss = len(r.json().get('data', []))
        print(f'剩余: 书源 {remaining_book}, 订阅源 {remaining_rss}')

if __name__ == '__main__':
    asyncio.run(main())
