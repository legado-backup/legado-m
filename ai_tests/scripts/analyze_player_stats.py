#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播放器统计脚本（T-003-P2-1）

从 logcat/appLog 日志中统计视频/图片/网络相关指标，输出 JSON + 控制台摘要。

用法:
    python analyze_player_stats.py <log_file_or_dir>
    python analyze_player_stats.py <log_file_or_dir> --json  # 仅输出JSON

统计指标:
    视频: sniffVideoType成功/失败、ERROR_CODE(3002/3003/2004)、ExoFallback降级、VIDEO_FALLBACK_WEBVIEW
    图片: ImageLoad加载、403计数、ImageFallback降级、triggerFallbackReload
    网络: DohDns失败、Cronet降级/恢复
    崩溃: FATAL EXCEPTION
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path


def collect_log_files(path: str) -> list:
    """收集日志文件（支持单文件或目录递归）"""
    p = Path(path)
    if p.is_file():
        return [p]
    if p.is_dir():
        # 递归收集 .log .txt 无扩展名 文件
        exts = {".log", ".txt", ""}
        return sorted(
            f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in exts
        )
    return []


def read_lines(files: list) -> list:
    """读取所有日志行（尝试多种编码）"""
    lines = []
    encodings = ["utf-8", "utf-8-sig", "gbk", "latin-1"]
    for f in files:
        for enc in encodings:
            try:
                with open(f, "r", encoding=enc, errors="strict") as fh:
                    lines.extend(fh.readlines())
                break
            except (UnicodeDecodeError, OSError):
                continue
        else:
            # 所有编码失败，用 latin-1 兜底（不会抛异常）
            try:
                with open(f, "r", encoding="latin-1", errors="replace") as fh:
                    lines.extend(fh.readlines())
            except OSError:
                pass
    return lines


def count_pattern(lines: list, pattern: str) -> int:
    """统计匹配正则的行数"""
    rx = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in lines if rx.search(line))


def count_pattern_pairs(lines: list, success_pat: str, fail_pat: str) -> dict:
    """统计成功/失败对"""
    rx_s = re.compile(success_pat, re.IGNORECASE)
    rx_f = re.compile(fail_pat, re.IGNORECASE)
    s = sum(1 for line in lines if rx_s.search(line))
    f = sum(1 for line in lines if rx_f.search(line))
    total = s + f
    rate = (s / total * 100) if total > 0 else 0.0
    return {"success": s, "fail": f, "total": total, "successRate": round(rate, 1)}


def extract_error_codes(lines: list) -> dict:
    """提取 ERROR_CODE_xxx 计数"""
    rx = re.compile(r"ERROR_CODE_(?:IO_|PARSING_)?[A-Z_]+|\b300[23]\b|\b2004\b")
    counter = Counter()
    for line in lines:
        for m in rx.findall(line):
            counter[m] += 1
    return dict(counter.most_common())


def analyze(lines: list) -> dict:
    """分析日志，返回统计结果"""
    stats = {
        "video": {
            "sniffVideoType": count_pattern_pairs(
                lines,
                r"sniffVideoType.*success",
                r"sniffVideoType.*(?:fail|io failed)",
            ),
            "playbackReady": count_pattern(lines, r"ExoPlayer.*STATE_READY|playback.*ready"),
            "firstFrame": count_pattern(lines, r"onRenderedFirstFrame|first.*frame"),
            "errorCodes": extract_error_codes(lines),
            "exoFallback": count_pattern(lines, r"ExoFallback.*switch|tryNextFallback"),
            "videoFallbackWebview": count_pattern(lines, r"VIDEO_FALLBACK_WEBVIEW"),
            "bufferingTimeout": count_pattern(lines, r"BUFFERING.*timeout"),
            "prepareAsyncReentrant": count_pattern(lines, r"prepareAsyncInternal.*reentrant"),
        },
        "image": {
            "imageLoad403": count_pattern(lines, r"ImageLoad.*403|403.*count="),
            "imageLoad404": count_pattern(lines, r"ImageLoad.*404|404.*count="),
            "imageFallback": count_pattern(lines, r"ImageFallback|triggerFallbackChain"),
            "triggerFallbackReload": count_pattern(lines, r"triggerFallbackReload"),
            "preheatReload": count_pattern(lines, r"preheat.*reload|markPreheatReload"),
            "headersMissing": count_pattern(lines, r"headers.*missing"),
            "urlPercent0A": count_pattern(lines, r"%0A|parseImageUrls.*filtered"),
        },
        "network": {
            "dohFail": count_pattern(lines, r"DohDns.*fail|DoH.*fail"),
            "cronetDegrade": count_pattern(lines, r"Cronet.*degrad|cronet.*降级"),
            "cronetRecover": count_pattern(lines, r"Cronet.*recover|cronet.*恢复"),
            "idnBypass": count_pattern(lines, r"IDN.*bypass|idn.*bypass"),
            "socketException": count_pattern(lines, r"SocketException"),
        },
        "crash": {
            "fatalException": count_pattern(lines, r"FATAL EXCEPTION"),
            "trackSelectorCrash": count_pattern(lines, r"TrackSelector.*init.*IllegalState"),
            "glideDestroyedCrash": count_pattern(lines, r"destroyed activity|Glide.*destroyed"),
        },
    }

    # 汇总
    stats["summary"] = {
        "totalLines": len(lines),
        "fatalCount": stats["crash"]["fatalException"],
        "sniffSuccessRate": stats["video"]["sniffVideoType"]["successRate"],
        "image403Count": stats["image"]["imageLoad403"],
        "image404Count": stats["image"]["imageLoad404"],
    }
    return stats


def print_summary(stats: dict):
    """打印控制台摘要"""
    print("=" * 60)
    print("播放器统计报告")
    print("=" * 60)
    print(f"\n日志总行数: {stats['summary']['totalLines']}")
    print(f"FATAL EXCEPTION: {stats['summary']['fatalCount']} 次")

    print("\n--- 视频播放 ---")
    s = stats["video"]["sniffVideoType"]
    print(f"嗅探: 成功 {s['success']}/失败 {s['fail']} (成功率 {s['successRate']}%)")
    print(f"播放 READY: {stats['video']['playbackReady']} 次")
    print(f"首帧渲染: {stats['video']['firstFrame']} 次")
    print(f"ExoFallback 降级: {stats['video']['exoFallback']} 次")
    print(f"VIDEO_FALLBACK_WEBVIEW: {stats['video']['videoFallbackWebview']} 次")
    print(f"BUFFERING 超时: {stats['video']['bufferingTimeout']} 次")
    print(f"prepareAsync 重入: {stats['video']['prepareAsyncReentrant']} 次")
    if stats["video"]["errorCodes"]:
        print("错误码分布:")
        for code, cnt in stats["video"]["errorCodes"].items():
            print(f"  {code}: {cnt}")

    print("\n--- 图片加载 ---")
    print(f"403 计数: {stats['image']['imageLoad403']}")
    print(f"404 计数: {stats['image']['imageLoad404']}")
    print(f"ImageFallback 降级: {stats['image']['imageFallback']}")
    print(f"triggerFallbackReload: {stats['image']['triggerFallbackReload']}")
    print(f"headers missing: {stats['image']['headersMissing']}")
    print(f"URL %0A 残留: {stats['image']['urlPercent0A']}")

    print("\n--- 网络层 ---")
    print(f"DoH 失败: {stats['network']['dohFail']}")
    print(f"Cronet 降级: {stats['network']['cronetDegrade']}")
    print(f"Cronet 恢复: {stats['network']['cronetRecover']}")
    print(f"SocketException: {stats['network']['socketException']}")

    print("\n--- 崩溃 ---")
    print(f"TrackSelector 崩溃: {stats['crash']['trackSelectorCrash']}")
    print(f"Glide destroyed 崩溃: {stats['crash']['glideDestroyedCrash']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="播放器统计脚本")
    parser.add_argument("path", help="日志文件或目录路径")
    parser.add_argument("--json", action="store_true", help="仅输出JSON（不打印摘要）")
    args = parser.parse_args()

    files = collect_log_files(args.path)
    if not files:
        print(f"错误: 未找到日志文件: {args.path}", file=sys.stderr)
        sys.exit(1)

    print(f"分析 {len(files)} 个日志文件...", file=sys.stderr)
    lines = read_lines(files)

    stats = analyze(lines)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print_summary(stats)
        # 同时输出JSON到文件
        out_file = "player_stats_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\nJSON 报告已保存: {out_file}")


if __name__ == "__main__":
    main()
