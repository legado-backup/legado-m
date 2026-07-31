"""Verify RSS source sort tabs - v4 with logcat check"""
import uiautomator2 as u2
import time
import re
import subprocess

PKG = 'io.legado.miss.app.debug'
ADB = r'D:\Program Files\Microvirt\MEmu\adb.exe'
d = u2.connect('127.0.0.1:21503')

# Wait for app to load
time.sleep(5)

# Navigate to RSS page - click description=订阅
rss_tab = d(description='订阅')
if rss_tab.exists:
    rss_tab.click()
    time.sleep(2)
    print('Clicked RSS tab')

# Click AV聚合 group
av_group = d(description='AV聚合')
if av_group.exists:
    av_group.click()
    time.sleep(2)
    print('Clicked AV聚合 group')

# Click first source
source = d(text='天籁精选')
if source.exists:
    source.click()
    print('Clicked 天籁精选')
    time.sleep(20)  # Wait for sortUrl JS to execute (long wait for network)

    # Check current activity
    act = d.app_current()
    print(f'Activity: {act}')

    # Check if sort tabs are visible
    xml2 = d.dump_hierarchy()
    tab_items = re.findall(r'text="([^"]+)"', xml2)
    print(f'All text on page ({len(tab_items)}):')
    for t in tab_items[:50]:
        if t: print(f'  {t}')

    # Look for category names
    categories = [t for t in tab_items if t in ['雄狮', '精品', 'Hsck', 'Xnxx', 'Xvideos', '91国产', '9109', '18AV']]
    print(f'\nCategory tabs found: {categories}')
    if categories:
        print('SUCCESS: Sort tabs are visible!')
    else:
        print('FAILED: No sort tabs visible')

    # Check logcat for sortUrls JS result
    result = subprocess.run([ADB, '-s', '127.0.0.1:21503', 'logcat', '-d', '-t', '200'],
                          capture_output=True, text=True, timeout=10)
    for line in result.stdout.split('\n'):
        if 'sortUrls' in line or 'sortUrlJs' in line:
            # Sanitize: only output technical info
            print(f'  LOG: {line[:150]}')
else:
    print('Source not found: 天籁精选')
