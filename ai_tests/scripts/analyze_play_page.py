#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站点E播放页结构分析（脱敏输出）
访问播放页，分析视频提取方式（m3u8/player_data/iframe/JS）
"""
import sys
import json
import re
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright


def main():
    print("=== 站点E播放页结构分析（脱敏）===")
    
    # 读取子站URL（用子站4，它有24个列表项）
    with open("output/siteE_subsites.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 子站4的URL（第4个.cfd域名）
    subsite_url = None
    for url in data["subsites"]:
        parsed = urlparse(url)
        if parsed.netloc.endswith(".cfd"):
            # 跳过前3个，取第4个
            pass
    
    # 实际上从siteE_sub4.html中已知播放页URL格式
    # 直接用子站4的域名 + 播放页路径
    # 但为了脱敏，我从HTML中提取第一个播放页链接
    
    # 读取子站4的HTML，提取第一个播放页链接
    with open("output/siteE_sub4.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # 提取第一个 m=play 的链接
    play_match = re.search(r'href="([^"]*m=play[^"]*)"', html)
    if not play_match:
        print("[ERROR] 未找到播放页链接")
        return
    
    play_path = play_match.group(1).replace("&amp;", "&")
    # 获取子站4的域名
    sub4_domain = None
    for url in data["subsites"]:
        parsed = urlparse(url)
        if parsed.netloc.endswith(".cfd"):
            # 从siteE_sub4.html的base URL获取
            pass
    
    # 从HTML中提取base URL或从页面URL获取
    # 实际上，我们需要子站4的真实URL。从siteE_analysis.json中获取
    with open("output/siteE_analysis.json", "r", encoding="utf-8") as f:
        analysis = json.load(f)
    
    # 子站4是第4个（索引3）
    sub4_url = analysis[3]["url"] if len(analysis) > 3 else None
    if not sub4_url:
        print("[ERROR] 未找到子站4的URL")
        return
    
    # 构造完整播放页URL
    parsed_sub = urlparse(sub4_url)
    base_url = f"{parsed_sub.scheme}://{parsed_sub.netloc}"
    
    # 播放页路径（play_path是相对路径如 /?m=play&u=javxx&k=xxx）
    if play_path.startswith("/"):
        play_url = base_url + play_path
    else:
        play_url = base_url + "/" + play_path
    
    print(f"播放页域名后缀: .{parsed_sub.netloc.split('.')[-1]}")
    print(f"播放页路径模式: /?m=play&u=[标识]&k=[视频ID]")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        page = context.new_page()
        
        try:
            print("[1] 访问播放页...")
            page.goto(play_url, timeout=45000, wait_until="domcontentloaded")
            # 播放页可能有JS跳转，等待导航稳定
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(8000)  # 等更久让JS跳转完成
            
            # 检测安全检测（用try-catch处理导航异常）
            title = "[空]"
            try:
                title = page.title()
            except Exception:
                page.wait_for_timeout(5000)
                try:
                    title = page.title()
                except Exception:
                    pass
            
            if "检测" in title:
                print("  [检测到安全检测，等待15秒...]")
                page.wait_for_timeout(15000)
                try:
                    title = page.title()
                except Exception:
                    pass
            
            print(f"  标题: {title[:30]}")
            html = page.content()
            print(f"  HTML长度: {len(html)}")
            print(f"  最终URL路径: {urlparse(page.url).path[:40]}")
            
            # 深度分析播放页
            play_info = page.evaluate("""() => {
                const r = {};
                const html = document.documentElement.outerHTML;
                
                // 1. 视频标签
                const video = document.querySelector('video');
                r.hasVideoTag = !!video;
                if (video) {
                    r.videoSrc = video.src || video.currentSrc || '';
                    r.videoSources = Array.from(video.querySelectorAll('source')).map(s => ({src: s.src, type: s.type}));
                }
                
                // 2. iframe（可能嵌入播放器）
                const iframes = document.querySelectorAll('iframe');
                r.iframeCount = iframes.length;
                r.iframeSrcs = Array.from(iframes).map(f => f.src).slice(0, 3);
                
                // 3. player_data / player_aaaa（MacCMS特征）
                r.hasPlayerData = html.includes('player_data');
                r.hasPlayerAaaa = html.includes('player_aaaa');
                
                // 4. m3u8链接
                const m3u8Match = html.match(/https?:\\/\\/[^"'\\s]+\\.m3u8[^"'\\s]*/);
                r.hasM3u8 = !!m3u8Match;
                r.m3u8Found = m3u8Match ? 'found' : 'not found';
                
                // 5. hls.js / DPlayer / videojs
                r.hasHlsJs = html.includes('hls.js') || html.includes('Hls');
                r.hasDPlayer = html.includes('DPlayer') || html.includes('dplayer');
                r.hasVideoJs = html.includes('videojs') || html.includes('video.js');
                r.hasJwplayer = html.includes('jwplayer') || html.includes('jwPlayer');
                
                // 6. 播放器容器
                const playerContainers = ['#player', '.player', '#video-box', '.video-box', '#player-wrapper', '.player-wrapper', '#dplayer', '.dplayer', '#video', '.video'];
                r.playerContainer = '';
                for (const sel of playerContainers) {
                    const el = document.querySelector(sel);
                    if (el) {
                        r.playerContainer = sel;
                        r.playerContainerHTML = el.outerHTML.substring(0, 500);
                        break;
                    }
                }
                
                // 7. JS中的视频URL模式
                const jsPatterns = [
                    /var\s+url\s*=\s*['"]([^'"]+)['"]/,
                    /var\s+videoUrl\s*=\s*['"]([^'"]+)['"]/,
                    /var\s+source\s*=\s*['"]([^'"]+)['"]/,
                    /source:\s*['"]([^'"]+)['"]/,
                    /file:\s*['"]([^'"]+)['"]/,
                    /src:\s*['"]([^'"]+)['"]/,
                    /url:\s*['"]([^'"]+)['"]/,
                    /videoUrl\s*=\s*['"]([^'"]+)['"]/,
                ];
                r.jsUrlMatches = [];
                for (const pattern of jsPatterns) {
                    const m = html.match(pattern);
                    if (m) r.jsUrlMatches.push({pattern: pattern.toString().substring(0,30), value: m[1].substring(0,60)});
                }
                
                // 8. 播放器API请求URL（可能通过ajax加载）
                const apiPatterns = [
                    /getPlayUrl\\s*\\([^)]*\\)/,
                    /api\\/play/,
                    /api\\/video/,
                    /player\\/api/,
                    /getplayurl/,
                ];
                r.apiPatterns = [];
                for (const p of apiPatterns) {
                    if (p.test(html)) r.apiPatterns.push(p.toString().substring(0,30));
                }
                
                // 9. 提取script标签中的src（可能含播放器JS）
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                r.scriptSrcs = scripts.map(s => s.src).filter(s => s.includes('player') || s.includes('video') || s.includes('hls') || s.includes('play')).slice(0, 5);
                
                // 10. 播放页正文文本（前300字符）
                r.bodyText = (document.body.innerText || '').substring(0, 300);
                
                return r;
            }""")
            
            print(f"\n[2] 播放页视频特征:")
            print(f"  video标签: {play_info.get('hasVideoTag', False)}")
            if play_info.get('videoSrc'):
                print(f"  video.src路径: {urlparse(play_info['videoSrc']).path[:40]}")
            print(f"  iframe数: {play_info.get('iframeCount', 0)}")
            if play_info.get('iframeSrcs'):
                for s in play_info['iframeSrcs'][:2]:
                    print(f"    iframe路径: {urlparse(s).path[:40]}")
            print(f"  player_data: {play_info.get('hasPlayerData', False)}")
            print(f"  player_aaaa: {play_info.get('hasPlayerAaaa', False)}")
            print(f"  m3u8: {play_info.get('hasM3u8', False)}")
            print(f"  hls.js: {play_info.get('hasHlsJs', False)}")
            print(f"  DPlayer: {play_info.get('hasDPlayer', False)}")
            print(f"  videojs: {play_info.get('hasVideoJs', False)}")
            print(f"  jwplayer: {play_info.get('hasJwplayer', False)}")
            
            print(f"\n[3] 播放器容器: {play_info.get('playerContainer', '未找到')}")
            if play_info.get('playerContainerHTML'):
                # 脱敏HTML
                container_html = play_info['playerContainerHTML']
                container_html = re.sub(r'https?://[^\s"\'<>]+', '[URL]', container_html)
                print(f"  容器HTML(脱敏): {container_html[:300]}")
            
            print(f"\n[4] JS中的URL模式:")
            for m in play_info.get('jsUrlMatches', []):
                # 脱敏
                val = m['value']
                val = re.sub(r'https?://[^\s]+', '[URL]', val)
                print(f"  {m['pattern']}: {val}")
            
            print(f"\n[5] API模式: {play_info.get('apiPatterns', [])}")
            print(f"  播放器JS脚本: {len(play_info.get('scriptSrcs', []))}个")
            for s in play_info.get('scriptSrcs', []):
                print(f"    脚本路径: {urlparse(s).path[:40]}")
            
            # 保存播放页HTML
            play_html = page.content()
            with open("output/siteE_play_page.html", "w", encoding="utf-8") as f:
                f.write(play_html)
            print(f"\n[6] 播放页HTML已保存: output/siteE_play_page.html (长度: {len(play_html)})")
            
            # 等待更长时间，看是否有动态加载的视频
            print("\n[7] 等待10秒看是否有动态加载...")
            page.wait_for_timeout(10000)
            
            # 再次检查video和m3u8
            dynamic = page.evaluate("""() => {
                const r = {};
                const video = document.querySelector('video');
                r.hasVideoNow = !!video;
                if (video) {
                    r.videoSrc = video.src || video.currentSrc || '';
                    r.videoSrcPath = r.videoSrc ? new URL(r.videoSrc, window.location.href).pathname.substring(0, 50) : '';
                }
                const html = document.documentElement.outerHTML;
                const m3u8Match = html.match(/https?:\\/\\/[^"'\\s]+\\.m3u8[^"'\\s]*/);
                r.hasM3u8Now = !!m3u8Match;
                // 检查network请求中的m3u8
                return r;
            }""")
            print(f"  动态加载后 video: {dynamic.get('hasVideoNow', False)}")
            if dynamic.get('videoSrcPath'):
                print(f"  video.src路径: {dynamic['videoSrcPath']}")
            print(f"  动态加载后 m3u8: {dynamic.get('hasM3u8Now', False)}")
            
            # 监听网络请求，找m3u8
            print("\n[8] 刷新页面监听网络请求...")
            m3u8_urls = []
            def handle_response(response):
                url = response.url
                if '.m3u8' in url or 'm3u8' in response.headers.get('content-type', ''):
                    m3u8_urls.append(url)
            
            page.on("response", handle_response)
            page.reload(timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(15000)
            
            print(f"  监听到m3u8请求: {len(m3u8_urls)}个")
            for u in m3u8_urls[:3]:
                parsed = urlparse(u)
                print(f"    m3u8路径: {parsed.path[:50]}")
            
        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    print("\n=== 播放页分析完成 ===")


if __name__ == "__main__":
    main()
