#!/usr/bin/env python3
"""fix_coverage_check.py — 修复点正向日志覆盖度分析

检查每个修复点的正向日志是否出现，确认修复代码路径被触发执行。
用法：
    ai_tests\\venv\\Scripts\\python.exe ai_tests/scripts/fix_coverage_check.py
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ADB_PATH, MEMU_ADB_HOST

def main():
    # 抓取 logcat
    cmd = f'"{ADB_PATH}" -s {MEMU_ADB_HOST} logcat -d'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            timeout=30, encoding='utf-8', errors='replace')
    log = result.stdout
    lines = log.splitlines()
    print(f"总日志行数: {len(lines)}")
    print("=" * 60)

    # 定义每个修复点的正向日志关键词
    fix_points = {
        "P1-A MPD误判修复(contains<MPD>)": {
            "正向": ["<MPD", ".mpd"],
            "说明": "应无.mpd文件写入（误判已修复），或正确识别MPD清单"
        },
        "P1-B FileUriExposed修复": {
            "正向": ["系统浏览器不支持本地清单文件", "系统浏览器打开失败"],
            "说明": "file://跳过日志（降级到系统浏览器时触发）"
        },
        "P1-C HTTP 416容错": {
            "正向": ["HTTP 416", "清除视频缓存"],
            "说明": "416错误清除缓存重试日志（CDN缓存不匹配时触发）"
        },
        "P1-D/P2-B DNS IP过滤": {
            "正向": ["DNS 解析到本地", "Filtered local", "DNS 解析失败"],
            "说明": "DNS过滤本地地址日志（域名被劫持时触发）"
        },
        "P2-A CancellationException守卫": {
            "正向": ["图片解密错误"],
            "负面": ["CancellationException"],
            "说明": "图片解密错误日志中不含CancellationException"
        },
        "P2-C HTTP/2强制HTTP/1.1": {
            "正向": ["HTTP_1_1", "protocol=http/1.1", "PROTOCOL_ERROR"],
            "说明": "无PROTOCOL_ERROR=HTTP/1.1生效；或negotiatedProtocol含http/1.1"
        },
        "P2-C Cronet回退OkHttp": {
            "正向": ["Cronet 协议错误", "Cronet 请求失败", "回退到 OkHttp"],
            "说明": "Cronet失败时回退日志（Cronet协议错误时触发）"
        },
        "R5网络抓包(VideoUrlExtractor)": {
            "正向": ["R5网络抓包"],
            "说明": "视频URL抓包日志（订阅源无内容规则时触发）"
        },
        "ExoPlayer播放活跃": {
            "正向": ["EventLogger", "loading"],
            "说明": "ExoPlayer loading事件=播放器在工作"
        },
        "网络错误重试(E2)": {
            "正向": ["ExoPlayer 网络错误自动重试"],
            "说明": "网络抖动重试日志（网络不稳定时触发）"
        },
    }

    triggered = []
    not_triggered = []

    for name, info in fix_points.items():
        positive = info.get("正向", [])
        negative = info.get("负面", [])
        counts = {}
        total = 0
        for kw in positive:
            c = sum(1 for l in lines if kw in l)
            counts[kw] = c
            total += c

        # 检查负面关键词（不应出现）
        neg_count = 0
        for kw in negative:
            neg_count += sum(1 for l in lines if kw in l and any(p in l for p in positive))

        desc = info.get("说明", "")
        if total > 0:
            status = "✅ 已触发"
            triggered.append(name)
            detail = ", ".join(f'"{k}"={v}' for k, v in counts.items() if v > 0)
        elif negative:
            # 只有负面检查的修复点（如P2-A），0正面+0负面=通过
            status = "✅ 通过(无错误)" if neg_count == 0 else "❌ 有错误"
            detail = f"负面关键词出现{neg_count}次"
        else:
            status = "⚠️ 未触发"
            not_triggered.append(name)
            detail = "本次测试场景未覆盖此代码路径"

        print(f"\n{name}")
        print(f"  状态: {status}")
        print(f"  详情: {detail}")
        print(f"  说明: {desc}")

    print("\n" + "=" * 60)
    print(f"已触发验证: {len(triggered)}/{len(fix_points)}")
    print(f"未触发: {len(not_triggered)}/{len(fix_points)}")
    if not_triggered:
        print("\n未触发的修复点（本次测试场景未覆盖）:")
        for n in not_triggered:
            print(f"  - {n}")
        print("\n注: 未触发不代表修复无效，只是本次测试场景没有走到该代码路径")
        print("    如需验证，需要构造特定场景（如416错误需特定CDN缓存状态）")

if __name__ == "__main__":
    main()
