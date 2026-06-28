#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大规模闭环测试脚本：分层采样 + JAR/真机测试 + 差异分析。

策略：真机优先 + JAR 跟进。从数据库按域名分层采样源，
分别用 JAR 仿真器和真机测试，输出统计报告和优化建议。

用法:
    python deep_analysis.py --mode jar --sample-size 200
    python deep_analysis.py --mode device --device-host 192.168.1.100
    python deep_analysis.py --mode compare --sample-size 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 将 scripts/ 目录加入 sys.path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from legado_client.storage.database import get_session_factory, init_db
from legado_client.storage.models import Source
from legado_client.utils.config import config
from sqlalchemy import func, select


# ==================== 常量 ====================

DEFAULT_BOOK_KEY = "斗破苍穹"
DEFAULT_RSS_KEY = "首页"
DEFAULT_TIMEOUT = 30


# ==================== 采样 ====================

def _extract_domain(url: str) -> str:
    """从 URL 提取域名。"""
    if not url:
        return ""
    try:
        if "://" not in url:
            url = f"http://{url}"
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        return domain.lower().replace("www.", "")
    except Exception:
        return ""


def _check_domain_alive(domain: str, timeout: float = 3.0) -> bool:
    """检测域名是否存活（DNS解析+TCP 80/443端口）。"""
    if not domain or domain == "__unknown__":
        return False
    try:
        # DNS 解析
        ip = socket.getaddrinfo(domain, None, socket.AF_INET)[0][4][0]
    except (socket.gaierror, OSError, UnicodeError, ValueError):
        return False
    # TCP 连接测试（先 443，再 80）
    for port in (443, 80):
        try:
            sock = socket.create_connection((ip, port), timeout=timeout)
            sock.close()
            return True
        except (OSError, socket.timeout):
            continue
    return False


def preflight_domains(
    domain_groups: Dict[str, List], max_workers: int = 50
) -> set:
    """批量域名存活检测，返回存活域名集合。"""
    alive: set = set()
    domains = list(domain_groups.keys())
    total = len(domains)
    print(f"[预检] 开始域名存活检测: {total} 个域名 ...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check_domain_alive, d): d for d in domains}
        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            domain = futures[future]
            if future.result():
                alive.add(domain)
            if done_count % 200 == 0 or done_count == total:
                print(f"[预检] {done_count}/{total} 已检测, 存活: {len(alive)}")

    print(f"[预检] 域名存活检测完成: {len(alive)}/{total} 存活")
    return alive


async def sample_sources(
    source_type: str,
    sample_size: int,
    per_domain: int = 3,
    include_login: bool = False,
    preflight: bool = True,
) -> List[Source]:
    """按域名分层采样源。

    1. 提取所有源的 source_url 域名，按域名分组
    2. 可选：域名存活预检，过滤不可达域名
    3. 每组最多采样 per_domain 个，优先有 searchUrl 的
    4. 排除 loginUrl 非空的源（除非 include_login）
    5. 总采样数上限 sample_size

    Args:
        source_type: "book" 或 "rss"
        sample_size: 总采样上限
        per_domain: 每域名最大采样数
        include_login: 是否包含需登录源

    Returns:
        采样后的 Source 列表
    """
    sf = get_session_factory()
    if sf is None:
        print("[ERROR] 数据库不可用，无法采样")
        return []

    async with sf() as session:
        # 查询所有符合基本条件的源
        stmt = select(Source).where(Source.source_type == source_type)
        if not include_login:
            stmt = stmt.where(
                (Source.has_login == False) | (Source.has_login.is_(None))
            )
        # 书源需要有 searchUrl 才能测搜索
        if source_type == "book":
            stmt = stmt.where(
                Source.search_url.isnot(None), Source.search_url != ""
            )
        # RSS 源需要有 ruleArticles
        else:
            stmt = stmt.where(
                Source.rule_articles.isnot(None), Source.rule_articles != ""
            )

        result = await session.execute(stmt)
        all_sources = list(result.scalars().all())

    print(f"[采样] {source_type} 类型共 {len(all_sources)} 个候选源")

    # 按域名分组
    domain_groups: Dict[str, List[Source]] = {}
    for src in all_sources:
        domain = _extract_domain(src.source_url or "")
        if not domain:
            domain = "__unknown__"
        domain_groups.setdefault(domain, []).append(src)

    print(f"[采样] 覆盖 {len(domain_groups)} 个域名")

    # 域名存活预检
    if preflight:
        alive_domains = preflight_domains(domain_groups)
        # 过滤掉不可达域名
        dead_count = len(domain_groups) - len(alive_domains)
        domain_groups = {
            d: srcs for d, srcs in domain_groups.items() if d in alive_domains
        }
        print(f"[采样] 过滤不可达域名: {dead_count} 个, 剩余 {len(domain_groups)} 个可达域名")

    # 每组采样：优先有 searchUrl 的（按 enabled 降序、id 升序）
    sampled: List[Source] = []
    for domain, sources in sorted(
        domain_groups.items(), key=lambda x: -len(x[1])
    ):
        # 优先选 enabled 的、有 searchUrl 的
        sources.sort(
            key=lambda s: (
                0 if s.enabled else 1,
                0 if s.search_url else 1,
                s.id or 0,
            )
        )
        picked = sources[:per_domain]
        sampled.extend(picked)
        if len(sampled) >= sample_size:
            break

    # 截断到上限
    sampled = sampled[:sample_size]
    domain_count = len(set(_extract_domain(s.source_url or "") for s in sampled))
    print(f"[采样] 最终采样 {len(sampled)} 个源，覆盖 {domain_count} 个域名")
    return sampled


# ==================== JAR 测试 ====================

def _jar_debug_source(
    source_json_str: str,
    source_type: str,
    key: str,
    jar_path: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """用 JAR 仿真器调试单个源。

    启动 JAR 进程，发送 debugBookSource/debugRssSource 命令，
    解析 stdout 流式 JSON 输出，30s 超时。

    Args:
        source_json_str: 源 JSON 字符串
        source_type: "book" 或 "rss"
        key: 搜索关键词
        jar_path: JAR 文件路径
        timeout: 超时秒数

    Returns:
        测试结果字典
    """
    result: Dict[str, Any] = {
        "status": "unknown",
        "stages": {
            "search": False,
            "detail": False,
            "toc": False,
            "content": False,
        },
        "search_count": 0,
        "toc_count": 0,
        "content_length": 0,
        "duration_ms": 0,
        "errors": [],
    }

    if source_type == "book":
        cmd_dict = {
            "cmd": "debugBookSource",
            "sourceJson": source_json_str,
            "key": key,
        }
    else:
        cmd_dict = {
            "cmd": "debugRssSource",
            "sourceJson": source_json_str,
            "key": key,
        }

    cmd_json = json.dumps(cmd_dict, ensure_ascii=False)
    input_data = (cmd_json + '\n{"cmd":"shutdown"}\n').encode("utf-8")

    start = time.time()
    try:
        proc = subprocess.Popen(
            ["java", "-jar", jar_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_bytes, _ = proc.communicate(input=input_data, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        result["status"] = "timeout"
        result["errors"].append("timeout")
        result["duration_ms"] = int((time.time() - start) * 1000)
        return result
    except FileNotFoundError:
        result["status"] = "error"
        result["errors"].append("java_not_found")
        return result
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e)[:200])
        result["duration_ms"] = int((time.time() - start) * 1000)
        return result

    result["duration_ms"] = int((time.time() - start) * 1000)

    # JAR stdout 用 GBK 解码
    stdout = stdout_bytes.decode("gbk", errors="replace")

    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_type = obj.get("type", "")

        if msg_type == "log":
            state = obj.get("state", 0)
            msg = obj.get("msg", "")
            # state 映射：10=search开始,11=search结果,20=detail,21=detail结果,...
            if state == 11:
                result["stages"]["search"] = True
            elif state == 21:
                result["stages"]["detail"] = True
            elif state == 31:
                result["stages"]["toc"] = True
            elif state == 41:
                result["stages"]["content"] = True
            # 目录成功判定：日志中包含目录总数（state=1 的普通日志）
            if state == 1 and "目录总数" in msg:
                result["stages"]["toc"] = True
            # 正文成功判定：state=1 日志含正文信息
            if state == 1 and "获取正文" in msg and "成功" in msg:
                result["stages"]["content"] = True
            if state < 0:
                result["errors"].append(f"{state}: {msg[:120]}")

        elif msg_type == "error":
            result["errors"].append(f"error: {obj.get('msg', '')[:120]}")
            failed_stage = obj.get("failedStage", "")
            if failed_stage and failed_stage in result["stages"]:
                result["stages"][failed_stage] = False

        elif msg_type == "result":
            result["status"] = "success" if obj.get("success") else "failed"
            summary = obj.get("summary", {})
            if summary.get("searchCount", 0) > 0:
                result["stages"]["search"] = True
                result["search_count"] = summary["searchCount"]
            if summary.get("bookName"):
                result["stages"]["detail"] = True
            if summary.get("tocCount", 0) > 0:
                result["stages"]["toc"] = True
                result["toc_count"] = summary["tocCount"]
            if summary.get("contentLength", 0) > 0:
                result["stages"]["content"] = True
                result["content_length"] = summary["contentLength"]

    return result


async def run_jar_tests(
    sources: List[Source],
    source_type: str,
    jar_path: str,
    timeout: int,
) -> List[Dict[str, Any]]:
    """对采样源执行 JAR 测试。顺序执行（JAR 是单进程 stdin/stdout 协议）。"""
    results: List[Dict[str, Any]] = []
    key = DEFAULT_BOOK_KEY if source_type == "book" else DEFAULT_RSS_KEY

    for i, source in enumerate(sources):
        source_json = source.source_json
        if isinstance(source_json, dict):
            source_json = json.dumps(source_json, ensure_ascii=False)

        source_name = source.source_name or f"source_{source.id}"
        source_url = source.source_url or ""
        elapsed_str = f"[{i+1}/{len(sources)}]"

        print(f"  {elapsed_str} JAR: {source_name[:30]} ({source_url[:50]})")

        jar_result = _jar_debug_source(
            source_json, source_type, key, jar_path, timeout
        )

        results.append({
            "source_id": source.id,
            "source_name": source_name,
            "source_url": source_url,
            "domain": _extract_domain(source_url),
            "source_type": source_type,
            "test_mode": "jar",
            **jar_result,
        })

        # 简短结果行
        stages_str = " ".join(
            f"{s[:3]}={'Y' if v else 'N'}"
            for s, v in jar_result["stages"].items()
        )
        err_short = jar_result["errors"][0][:50] if jar_result["errors"] else ""
        print(f"    {stages_str} | {jar_result['status']}"
              f" | {jar_result['duration_ms']}ms"
              + (f" | {err_short}" if err_short else ""))

    return results


# ==================== 真机测试 ====================

async def run_device_tests(
    sources: List[Source],
    source_type: str,
    host: str,
    port: int,
    timeout: int,
) -> List[Dict[str, Any]]:
    """对采样源执行真机 WebSocket 测试。"""
    from legado_client.device.legado_web_client import LegadoWebClient

    results: List[Dict[str, Any]] = []
    key = DEFAULT_BOOK_KEY if source_type == "book" else DEFAULT_RSS_KEY

    async with LegadoWebClient(host=host, port=port) as client:
        # 先测试连接
        conn = await client.test_connection()
        if not conn["connected"]:
            print(f"[ERROR] 真机连接失败: {conn.get('error', 'unknown')}")
            return []

        print(f"[真机] 已连接 {host}:{port}")

        for i, source in enumerate(sources):
            source_json = source.source_json
            if isinstance(source_json, dict):
                source_obj = source_json
            else:
                try:
                    source_obj = json.loads(source_json)
                except (json.JSONDecodeError, TypeError):
                    source_obj = {}

            source_name = source.source_name or f"source_{source.id}"
            source_url = source.source_url or ""

            print(f"  [{i+1}/{len(sources)}] Device: {source_name[:30]} ({source_url[:50]})")

            # 先 push 源到真机
            try:
                if source_type == "book":
                    await client.save_book_source(source_obj)
                else:
                    await client.save_rss_source(source_obj)
            except Exception as e:
                print(f"    push 失败: {e}")

            # WebSocket 调试
            stage_result: Dict[str, Any] = {
                "source_id": source.id,
                "source_name": source_name,
                "source_url": source_url,
                "domain": _extract_domain(source_url),
                "source_type": source_type,
                "test_mode": "device",
                "status": "unknown",
                "stages": {
                    "search": False,
                    "detail": False,
                    "toc": False,
                    "content": False,
                },
                "search_count": 0,
                "toc_count": 0,
                "content_length": 0,
                "duration_ms": 0,
                "errors": [],
            }

            start = time.time()
            try:
                if source_type == "book":
                    logs = await client.ws_debug_book_source(source_obj, key)
                else:
                    logs = await client.ws_debug_rss_source(source_obj)

                stage_result["duration_ms"] = int((time.time() - start) * 1000)

                # 解析 WebSocket 日志
                for log_line in logs:
                    log_lower = log_line.lower()
                    # 搜索成功
                    if "搜索" in log_line and ("成功" in log_line or "找到" in log_line):
                        stage_result["stages"]["search"] = True
                    # 详情成功
                    if "详情" in log_line and "成功" in log_line:
                        stage_result["stages"]["detail"] = True
                    # 目录成功
                    if "目录" in log_line and ("成功" in log_line or "章" in log_line):
                        stage_result["stages"]["toc"] = True
                    # 正文成功
                    if "正文" in log_line and "成功" in log_line:
                        stage_result["stages"]["content"] = True
                    # 错误
                    if "[error]" in log_lower or "失败" in log_line:
                        stage_result["errors"].append(log_line[:120])

                # 判断整体状态
                if any(stage_result["stages"].values()):
                    stage_result["status"] = "success"
                else:
                    stage_result["status"] = "failed"

            except Exception as e:
                stage_result["status"] = "error"
                stage_result["errors"].append(str(e)[:200])
                stage_result["duration_ms"] = int((time.time() - start) * 1000)

            results.append(stage_result)
            stages_str = " ".join(
                f"{s[:3]}={'Y' if v else 'N'}"
                for s, v in stage_result["stages"].items()
            )
            print(f"    {stages_str} | {stage_result['status']} | {stage_result['duration_ms']}ms")

    return results


# ==================== 差异分析 ====================

def compare_results(
    jar_results: List[Dict[str, Any]],
    device_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """对比 JAR 和真机结果，生成差异分析。

    分类:
    - jar_only_fail: 真机通过+JAR失败 → JAR 优化方向
    - device_only_fail: 真机失败+JAR通过 → 可能是 JAR 假阳性
    - both_fail: 都失败 → 源规则问题或网站不可达
    - both_pass: 都通过 → 正常
    """
    # 按 source_id 建立索引
    jar_map = {r["source_id"]: r for r in jar_results if r.get("source_id")}
    device_map = {r["source_id"]: r for r in device_results if r.get("source_id")}

    common_ids = set(jar_map.keys()) & set(device_map.keys())

    diff_report: Dict[str, Any] = {
        "total_compared": len(common_ids),
        "both_pass": [],
        "both_fail": [],
        "jar_only_fail": [],
        "device_only_fail": [],
        "stage_diff": [],
    }

    for sid in common_ids:
        jr = jar_map[sid]
        dr = device_map[sid]

        jar_pass = jr["status"] == "success"
        device_pass = dr["status"] == "success"

        entry = {
            "source_id": sid,
            "source_name": jr.get("source_name", ""),
            "source_url": jr.get("source_url", ""),
            "domain": jr.get("domain", ""),
        }

        if jar_pass and device_pass:
            diff_report["both_pass"].append(entry)
        elif not jar_pass and not device_pass:
            entry["jar_errors"] = jr.get("errors", [])[:3]
            entry["device_errors"] = dr.get("errors", [])[:3]
            diff_report["both_fail"].append(entry)
        elif not jar_pass and device_pass:
            # JAR 优化方向
            entry["jar_stages"] = jr.get("stages", {})
            entry["device_stages"] = dr.get("stages", {})
            entry["jar_errors"] = jr.get("errors", [])[:3]
            entry["failed_jar_stages"] = [
                s for s, v in jr.get("stages", {}).items() if not v
            ]
            diff_report["jar_only_fail"].append(entry)
        else:
            # device_only_fail: JAR通过但真机失败 → 可能假阳性
            entry["jar_stages"] = jr.get("stages", {})
            entry["device_stages"] = dr.get("stages", {})
            entry["device_errors"] = dr.get("errors", [])[:3]
            diff_report["device_only_fail"].append(entry)

        # 逐阶段对比
        jar_stages = jr.get("stages", {})
        device_stages = dr.get("stages", {})
        for stage in ("search", "detail", "toc", "content"):
            jv = jar_stages.get(stage, False)
            dv = device_stages.get(stage, False)
            if jv != dv:
                diff_report["stage_diff"].append({
                    **entry,
                    "stage": stage,
                    "jar_pass": jv,
                    "device_pass": dv,
                })

    return diff_report


# ==================== 错误分类 ====================

def classify_error(error_msg: str) -> str:
    """将错误信息分类为标准错误类型。"""
    el = error_msg.lower()
    if "404" in el:
        return "404"
    if "403" in el:
        return "403"
    if "timeout" in el or "超时" in el:
        return "timeout"
    if "ssl" in el or "handshake" in el or "certif" in el:
        return "ssl"
    if "dns" in el or "resolve" in el or "unknown host" in el:
        return "dns"
    if "connect" in el or "connection" in el or "refused" in el:
        return "connect"
    if "为空" in el or "empty" in el or "0 结果" in el:
        return "empty"
    if "parse" in el or "解析" in el:
        return "parse_error"
    if "timeout" in el:
        return "timeout"
    return "other"


# ==================== 统计输出 ====================

def compute_statistics(
    results: List[Dict[str, Any]],
    label: str,
) -> Dict[str, Any]:
    """计算测试结果统计。"""
    if not results:
        return {"label": label, "total": 0}

    total = len(results)
    stage_counter = {s: {"pass": 0, "fail": 0} for s in ("search", "detail", "toc", "content")}
    error_counter: Counter = Counter()
    status_counter: Counter = Counter()
    duration_list: List[int] = []

    for r in results:
        status_counter[r.get("status", "unknown")] += 1
        duration_list.append(r.get("duration_ms", 0))

        for stage in ("search", "detail", "toc", "content"):
            if r.get("stages", {}).get(stage, False):
                stage_counter[stage]["pass"] += 1
            else:
                stage_counter[stage]["fail"] += 1

        for err in r.get("errors", []):
            error_counter[classify_error(err)] += 1

    avg_duration = sum(duration_list) / len(duration_list) if duration_list else 0

    return {
        "label": label,
        "total": total,
        "status_distribution": dict(status_counter),
        "stage_pass_rate": {
            stage: {
                "pass": sc["pass"],
                "fail": sc["fail"],
                "rate": round(sc["pass"] / total * 100, 1) if total else 0,
            }
            for stage, sc in stage_counter.items()
        },
        "error_distribution": dict(error_counter.most_common()),
        "avg_duration_ms": round(avg_duration),
    }


def print_report(
    jar_stats: Dict[str, Any],
    device_stats: Dict[str, Any],
    diff_report: Optional[Dict[str, Any]],
    output_path: str,
) -> None:
    """打印统计报告并保存 JSON。"""
    print(f"\n{'='*70}")
    print("大规模闭环测试报告")
    print(f"{'='*70}")

    for stats in (jar_stats, device_stats):
        if stats["total"] == 0:
            continue
        print(f"\n--- {stats['label']} ---")
        print(f"  测试源数: {stats['total']}")
        print(f"  状态分布: {stats['status_distribution']}")
        print(f"  平均耗时: {stats['avg_duration_ms']}ms")
        print(f"  各阶段通过率:")
        for stage in ("search", "detail", "toc", "content"):
            info = stats["stage_pass_rate"][stage]
            print(f"    {stage}: {info['pass']}/{info['pass']+info['fail']} = {info['rate']}%")
        if stats["error_distribution"]:
            print(f"  错误类型分布:")
            for err_type, count in stats["error_distribution"].items():
                print(f"    {err_type}: {count}")

    # 差异分析
    if diff_report and diff_report["total_compared"] > 0:
        print(f"\n--- 差异分析 (JAR vs 真机) ---")
        print(f"  对比源数: {diff_report['total_compared']}")
        print(f"  都通过: {len(diff_report['both_pass'])}")
        print(f"  都失败: {len(diff_report['both_fail'])}")
        print(f"  真机通过+JAR失败 (JAR优化方向): {len(diff_report['jar_only_fail'])}")
        print(f"  JAR通过+真机失败 (可能假阳性): {len(diff_report['device_only_fail'])}")

        # JAR 优化建议
        if diff_report["jar_only_fail"]:
            print(f"\n  JAR 优化建议 (真机通过但 JAR 失败的源):")
            for entry in diff_report["jar_only_fail"][:20]:
                stages = entry.get("failed_jar_stages", [])
                print(f"    - [{entry['domain']}] {entry['source_name'][:30]}"
                      f" | JAR失败阶段: {','.join(stages)}"
                      f" | 错误: {'; '.join(entry.get('jar_errors', [])[:1])[:80]}")

        # 假阳性审查
        if diff_report["device_only_fail"]:
            print(f"\n  假阳性审查 (JAR通过但真机失败):")
            for entry in diff_report["device_only_fail"][:10]:
                print(f"    - [{entry['domain']}] {entry['source_name'][:30]}"
                      f" | 真机错误: {'; '.join(entry.get('device_errors', [])[:1])[:80]}")

    # 保存 JSON 报告
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "jar_stats": jar_stats,
        "device_stats": device_stats,
        "diff_report": diff_report,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n报告已保存: {output_path}")


# ==================== 主流程 ====================

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="大规模闭环测试：分层采样 + JAR/真机测试 + 差异分析"
    )
    parser.add_argument(
        "--mode",
        choices=["jar", "device", "compare"],
        default="jar",
        help="测试模式: jar(仅JAR), device(仅真机), compare(真机+JAR对比)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=200,
        help="书源采样上限 (默认200)",
    )
    parser.add_argument(
        "--rss-sample-size",
        type=int,
        default=50,
        help="订阅源采样上限 (默认50)",
    )
    parser.add_argument(
        "--per-domain",
        type=int,
        default=3,
        help="每域名最大采样数 (默认3)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="单源测试超时秒数 (默认30)",
    )
    parser.add_argument(
        "--include-login",
        action="store_true",
        help="包含需登录的源 (默认排除)",
    )
    parser.add_argument(
        "--device-host",
        default="127.0.0.1",
        help="真机 IP (默认127.0.0.1)",
    )
    parser.add_argument(
        "--device-port",
        type=int,
        default=1122,
        help="真机 HTTP 端口 (默认1122)",
    )
    parser.add_argument(
        "--output",
        default="reports/deep-analysis.json",
        help="报告输出路径 (默认 reports/deep-analysis.json)",
    )
    parser.add_argument(
        "--source-type",
        choices=["book", "rss", "both"],
        default="both",
        help="测试源类型 (默认 both)",
    )
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        help="跳过域名存活预检 (默认启用)",
    )
    args = parser.parse_args()

    print(f"模式: {args.mode}")
    print(f"书源采样上限: {args.sample_size}, 订阅源采样上限: {args.rss_sample_size}")
    print(f"超时: {args.timeout}s, 每域名上限: {args.per_domain}")

    # 初始化数据库
    db_ok = await init_db()
    if not db_ok:
        print("[ERROR] 数据库初始化失败，退出")
        sys.exit(1)

    # 确定测试的源类型
    source_types = []
    if args.source_type in ("book", "both"):
        source_types.append("book")
    if args.source_type in ("rss", "both"):
        source_types.append("rss")

    # JAR 路径
    jar_path = config.jar_path
    if not os.path.exists(jar_path):
        print(f"[ERROR] JAR 不存在: {jar_path}")
        sys.exit(1)
    print(f"JAR: {jar_path}")

    # 采样
    all_sources: List[Source] = []
    for st in source_types:
        limit = args.sample_size if st == "book" else args.rss_sample_size
        sources = await sample_sources(
            source_type=st,
            sample_size=limit,
            per_domain=args.per_domain,
            include_login=args.include_login,
            preflight=not args.no_preflight,
        )
        all_sources.extend(sources)

    if not all_sources:
        print("[ERROR] 采样为空，退出")
        sys.exit(1)

    print(f"\n总采样: {len(all_sources)} 个源")

    # 按类型分组
    book_sources = [s for s in all_sources if s.source_type == "book"]
    rss_sources = [s for s in all_sources if s.source_type == "rss"]

    # 执行测试
    jar_results: List[Dict[str, Any]] = []
    device_results: List[Dict[str, Any]] = []

    if args.mode in ("jar", "compare"):
        print(f"\n{'='*70}")
        print("JAR 仿真器测试")
        print(f"{'='*70}")
        if book_sources:
            print(f"\n[书源] {len(book_sources)} 个")
            jar_results.extend(
                await run_jar_tests(book_sources, "book", jar_path, args.timeout)
            )
        if rss_sources:
            print(f"\n[订阅源] {len(rss_sources)} 个")
            jar_results.extend(
                await run_jar_tests(rss_sources, "rss", jar_path, args.timeout)
            )

    if args.mode in ("device", "compare"):
        print(f"\n{'='*70}")
        print("真机测试")
        print(f"{'='*70}")
        if book_sources:
            print(f"\n[书源] {len(book_sources)} 个")
            device_results.extend(
                await run_device_tests(
                    book_sources, "book",
                    args.device_host, args.device_port, args.timeout,
                )
            )
        if rss_sources:
            print(f"\n[订阅源] {len(rss_sources)} 个")
            device_results.extend(
                await run_device_tests(
                    rss_sources, "rss",
                    args.device_host, args.device_port, args.timeout,
                )
            )

    # 统计
    jar_stats = compute_statistics(jar_results, "JAR仿真器")
    device_stats = compute_statistics(device_results, "真机")

    # 差异分析
    diff_report = None
    if args.mode == "compare" and jar_results and device_results:
        diff_report = compare_results(jar_results, device_results)

    # 输出报告
    # 报告输出路径相对于 scripts/ 目录
    output_path = os.path.join(SCRIPTS_DIR, args.output)
    print_report(jar_stats, device_stats, diff_report, output_path)


if __name__ == "__main__":
    asyncio.run(main())
