"""验证崩溃修复：长按书源进入选择模式不再崩溃"""
import uiautomator2 as u2
import time, subprocess

ADB = 'D:/Program Files/Microvirt/MEmu/adb.exe'
DEVICE = '127.0.0.1:21503'
PKG = 'io.legado.app.debug'

# 清除logcat
subprocess.run([ADB, '-s', DEVICE, 'logcat', '-c'], timeout=10)

d = u2.connect(DEVICE)
print('[INFO] device connected')

# 启动书源管理
subprocess.run([ADB, '-s', DEVICE, 'shell', f'am start -n {PKG}/io.legado.app.ui.book.source.manage.BookSourceActivity'], timeout=10)
time.sleep(8)

# 检查RecyclerView
recycler = d(resourceId=f'{PKG}:id/recycler_view')
if recycler.exists:
    print('[PASS] RecyclerView exists')
    first_item = recycler.child(index=0)
    if first_item.exists:
        print('[INFO] long click first item...')
        try:
            first_item.long_click(duration=2)
            time.sleep(2)
            select_bar = d(resourceId=f'{PKG}:id/select_action_bar')
            if select_bar.exists:
                print('[PASS] selection mode entered, no crash!')
            else:
                print('[WARN] selection mode not detected')
        except Exception as e:
            print(f'[FAIL] long click error: {e}')
    else:
        print('[WARN] first item not exists')
else:
    print('[WARN] RecyclerView not exists')

# 检查logcat FATAL
result = subprocess.run([ADB, '-s', DEVICE, 'logcat', '-d', '-s', 'AndroidRuntime:E'], capture_output=True, timeout=15)
log = result.stdout.decode('utf-8', errors='ignore')
if 'FATAL' in log:
    print('[FAIL] FATAL EXCEPTION detected!')
    lines = log.split('\n')
    for i, line in enumerate(lines):
        if 'FATAL' in line or 'Exception' in line or 'at io.legado' in line:
            print(f'  {line}')
            if i > 15:
                break
else:
    print('[PASS] no FATAL EXCEPTION, crash fix verified!')

d.press('back')
time.sleep(1)
d.press('back')
