#!/usr/bin/env python3
"""测试通过ADB直接启动RssSortActivity搜索（传入key参数）"""
import uiautomator2 as u2
import time
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PKG = 'io.legado.miss.app.release'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
HOST = '127.0.0.1:21503'
d = u2.connect(HOST)

SOURCES = [
    {'name': '源[1]天籁', 'url': 'https://cc.tianlai48.cfd'},
    {'name': '源[2]撸色', 'url': 'https://aa.lusevip48.cfd'},
    {'name': '源[3]青涩', 'url': 'https://bb.qingse48.cfd'},
    {'name': '源[4]窝窝', 'url': 'https://ww.wowo47.cfd'},
    {'name': '源[5]桃花', 'url': 'https://91.taohua48.cfd'},
    {'name': '源[6]秘密', 'url': 'https://av.mimi48.cfd'},
    {'name': '源[7]Papa', 'url': 'https://av.papa48.cfd'},
]

def run_adb(cmd, timeout=30):
    full = f'"{ADB}" -s {HOST} {cmd}'
    return subprocess.run(full, shell=True, capture_output=True, text=True, timeout=timeout)

# Force stop first
run_adb(f'shell am force-stop {PKG}')
time.sleep(2)

results = {}

for src in SOURCES:
    name = src['name']
    url = src['url']
    
    print(f"\n{'='*50}")
    print(f"Testing search: {name}")
    print(f"{'='*50}")
    
    # Method: Launch RssSortActivity with key parameter
    # This mimics what SearchView.onQueryTextSubmit does internally
    cmd = f'shell am start -n {PKG}/io.legado.app.ui.rss.article.RssSortActivity --es sourceUrl \'{url}\' --es key \'HD\''
    r = run_adb(cmd)
    print(f'  Launch result: {r.stdout.strip()[:100]}')
    
    # Wait for search results (JS dynamic domain resolution needs time)
    found = False
    for wait_round in range(8):
        time.sleep(10)
        
        act = d.app_current().get('activity', '?')
        titles = d(resourceId=f'{PKG}:id/tv_title')
        title_count = titles.count if titles.exists else 0
        rv = d(className='androidx.recyclerview.widget.RecyclerView')
        rv_count = 0
        if rv.exists:
            try:
                rv_count = rv.child().count
            except:
                pass
        
        print(f'  Wait {(wait_round+1)*10}s: Act={act[-30:]}, Titles={title_count}, RV={rv_count}')
        
        if title_count > 0 or rv_count > 2:
            print(f'  [SEARCH-OK] {max(title_count, rv_count)} results found!')
            results[name] = {'search': 'OK', 'count': max(title_count, rv_count)}
            found = True
            break
    
    if not found:
        print(f'  [SEARCH-FAIL] No results after 80s')
        results[name] = {'search': 'FAIL', 'count': 0}
    
    # Go back
    run_adb(f'shell am force-stop {PKG}')
    time.sleep(2)

# Summary
print(f"\n{'='*50}")
print("SEARCH SUMMARY")
print(f"{'='*50}")
for name, r in results.items():
    status = r['search']
    count = r['count']
    print(f"  {name}: {status} ({count} results)")
