#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""经验闭环管理器：测试前检索经验 + 测试后输出待写入经验。

AD-5决策：debug-source.py输出经验数据到JSON文件，由AI agent外层通过MCP写入basic-memory。
basic-memory是MCP服务器，不是CLI工具，Python脚本无法通过subprocess调用。

迁移自 scripts/experience_manager.py，路径基准改用 legado_client.utils.config.Config。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from legado_client.utils.config import config
from legado_client.utils.file_utils import sanitize_source_json


class ExperienceManager:
    """经验闭环管理器：文件搜索降级 + JSON pending输出。"""

    def __init__(self) -> None:
        self._references_dir: Path = config.references_dir / "troubleshooting"
        self._pending_file: Path = config.output_dir / "experience-pending.json"

    def search(self, source_url: str, source_name: str) -> str:
        """测试前检索：用pathlib.Path.rglob搜索references/troubleshooting/，Windows兼容。

        Returns:
            str: 检索结果摘要
        """
        keywords = [k for k in [source_url, source_name] if k]
        if not keywords:
            return "无相似案例"

        matches = []
        for md_file in self._references_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                for keyword in keywords:
                    if keyword in content:
                        matches.append(str(md_file.relative_to(self._references_dir.parent)))
                        break
            except Exception:
                continue

        if matches:
            return f"找到相似案例:\n  " + "\n  ".join(matches)
        return "无相似案例"

    def search_experience(self, source_url: str, source_name: str = "") -> list:
        """搜索相似案例，使用 pathlib.Path.rglob 搜索 references/troubleshooting/ 目录。

        从 source_url 提取域名进行匹配，返回相似案例列表。

        Args:
            source_url: 源URL
            source_name: 源名称（可选，扩展搜索关键词）

        Returns:
            list: 相似案例列表，每项含 file/domain/preview
        """
        if not self._references_dir.exists():
            return []

        # 从 source_url 提取域名
        domain_match = re.search(r'https?://([^/]+)', source_url)
        domain = domain_match.group(1) if domain_match else source_url

        # 搜索关键词：域名 + URL + 源名称
        keywords = [k for k in [domain, source_url, source_name] if k]

        results = []
        for md_file in self._references_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                for keyword in keywords:
                    if keyword in content:
                        results.append({
                            "file": str(md_file),
                            "domain": domain,
                            "preview": content[:200]
                        })
                        break
            except Exception:
                continue

        return results

    def write_pending(self, source: dict, fix_info: dict, test_result: dict) -> None:
        """测试后写入：输出到output/experience-pending.json，由AI agent外层通过MCP写入basic-memory。

        降级路径：pending文件写入失败时，降级写入references/troubleshooting/auto/目录，
        添加<!-- AUTO_GENERATED -->标记，不污染权威文档。

        Args:
            source: 书源/订阅源JSON
            fix_info: 修复信息（error_type, fix_method等）
            test_result: 测试结果（success, stages等）
        """
        experience = self._format_experience(source, fix_info, test_result)

        try:
            self._pending_file.parent.mkdir(parents=True, exist_ok=True)
            pending_data = []
            if self._pending_file.exists():
                try:
                    pending_data = json.loads(self._pending_file.read_text(encoding='utf-8'))
                except Exception:
                    pending_data = []

            pending_data.append({
                "content": experience,
                "tags": ["自动积累", fix_info.get("error_type", "")],
            })
            self._pending_file.write_text(
                json.dumps(pending_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception:
            # 降级写入：pending文件写入失败时，写入references/troubleshooting/auto/
            auto_dir = config.references_dir / "troubleshooting" / "auto"
            auto_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            source_name = source.get("bookSourceName") or source.get("sourceName") or "unknown"
            safe_name = source_name.replace("/", "_").replace(" ", "_")
            auto_file = auto_dir / f"{safe_name}_{timestamp}.md"
            auto_file.write_text(
                f"<!-- AUTO_GENERATED -->\n{experience}",
                encoding='utf-8'
            )

    def write_experience(self, error_type: str, fix_solution: str, test_result: str, source_url: str) -> str:
        """输出经验数据到 output/experience-pending.json，供 AI agent 通过 MCP 写入 basic-memory。

        Args:
            error_type: 错误类型
            fix_solution: 修复方案
            test_result: 测试结果
            source_url: 源URL

        Returns:
            str: pending 文件路径
        """
        self._pending_file.parent.mkdir(parents=True, exist_ok=True)

        experience_data = {
            "error_type": error_type,
            "fix_solution": fix_solution,
            "test_result": test_result,
            "source_url": source_url,
            "date": datetime.now().isoformat(),
            "status": "pending"
        }

        # 追加模式：读取已有数据，不覆盖
        existing = []
        if self._pending_file.exists():
            try:
                existing = json.loads(self._pending_file.read_text(encoding='utf-8'))
                if not isinstance(existing, list):
                    existing = [existing]
            except Exception:
                existing = []

        existing.append(experience_data)
        self._pending_file.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        return str(self._pending_file)

    def write_experience_fallback(self, error_type: str, fix_solution: str, source_url: str) -> str:
        """降级写入：basic-memory 不可用时写入 references/troubleshooting/auto/。

        添加 <!-- AUTO_GENERATED --> 标记，不污染权威文档。

        Args:
            error_type: 错误类型
            fix_solution: 修复方案
            source_url: 源URL

        Returns:
            str: 降级文件路径
        """
        auto_dir = self._references_dir / "auto"
        auto_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auto_{error_type}_{timestamp}.md"
        filepath = auto_dir / filename

        content = (
            f"<!-- AUTO_GENERATED -->\n"
            f"# 自动生成经验：{error_type}\n\n"
            f"- 来源URL: {source_url}\n"
            f"- 日期: {datetime.now().isoformat()}\n"
            f"- 修复方案: {fix_solution}\n\n"
            f"> 此文件为降级写入，AI agent 可通过 MCP 写入 basic-memory 后删除此文件。\n"
        )
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)

    def resolve_conflict(self, exp1: dict, exp2: dict) -> dict:
        """经验冲突解决：按置信度0.5+时效性0.3+覆盖度0.2评分选优。

        Args:
            exp1: 经验1（含confidence/date/coverage字段）
            exp2: 经验2

        Returns:
            dict: 评分更高的经验
        """
        def _score(exp: dict) -> float:
            confidence = exp.get("confidence", 0.5)
            date_str = exp.get("date", "")
            coverage = exp.get("coverage", 0.5)
            # 时效性：日期越近分数越高（简化：有日期=0.8，无=0.3）
            recency = 0.8 if date_str else 0.3
            return confidence * 0.5 + recency * 0.3 + coverage * 0.2

        return exp1 if _score(exp1) >= _score(exp2) else exp2

    def _format_experience(self, source: dict, fix_info: dict, test_result: dict) -> str:
        """格式化经验为Markdown模板。"""
        date_str = datetime.now().strftime("%Y-%m-%d")

        source_name = source.get("bookSourceName") or source.get("sourceName") or "未知"
        source_url = source.get("bookSourceUrl") or source.get("sourceUrl") or "未知"
        error_type = fix_info.get("error_type", "未知")
        fix_method = fix_info.get("fix_method", "未知")
        test_status = "通过" if test_result.get("success") else "失败"
        stages = test_result.get("stages", "")

        return (
            f"# {source_name} 修复经验\n\n"
            f"- 日期: {date_str}\n"
            f"- 源URL: {source_url}\n"
            f"- 错误类型: {error_type}\n"
            f"- 修复方案: {fix_method}\n"
            f"- 测试结果: {test_status} ({stages})\n"
        )

    def extract(self, source_obj, debug_result, confidence):
        """自动提取经验要素（新增方法）。

        Args:
            source_obj: 书源/订阅源 JSON 对象
            debug_result: 调试结果对象（需有 success/error_type/fix_method 等属性）
            confidence: 可信度评估结果

        Returns:
            dict: 经验草稿，包含网站特征/错误类型/修复方法/规则模式/可信度等
        """
        return {
            "website_feature": self._extract_website_feature(source_obj),
            "error_type": debug_result.get("error_type") if not debug_result.get("success") else None,
            "fix_method": debug_result.get("fix_method") if debug_result.get("fix_applied") else None,
            "rule_pattern": self._extract_rule_pattern(source_obj),
            "confidence": confidence,
            "source_url": source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl"),
            "source_name": source_obj.get("bookSourceName") or source_obj.get("sourceName"),
            "timestamp": datetime.now().isoformat()
        }

    def write_to_basic_memory(self, experience_draft):
        """通过 MCP 写入 basic-memory（新增方法，返回 MCP 调用指令由 AI agent 执行）。

        basic-memory 是 MCP 服务器，Python 脚本无法直接调用，
        故返回调用指令交由外层 AI agent 执行。

        Args:
            experience_draft: extract() 返回的经验草稿

        Returns:
            dict: MCP 调用指令，由 AI agent 执行写入
        """
        return {
            "tool": "mcp_basic-memory_write_note",
            "args": {
                "title": f"经验: {experience_draft.get('website_feature', 'unknown')}",
                "content": self._format_content(experience_draft),
                "project": "legado",
                "note_type": "experience",
                "tags": ["auto-extracted"],
                "metadata": experience_draft
            }
        }

    def _extract_website_feature(self, source_obj):
        """提取网站特征：域名 + 检测到的特征标签。"""
        url = source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl") or ""
        # 从URL提取域名
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc
        except Exception:
            domain = url
        # 检测特征
        features = []
        if "wordpress" in url.lower():
            features.append("WordPress")
        if "discuz" in url.lower():
            features.append("Discuz")
        if source_obj.get("loginUrl"):
            features.append("需登录")
        if source_obj.get("header"):
            features.append("自定义Header")
        if source_obj.get("enableJs") == 1:
            features.append("启用JS")
        return f"{domain} ({', '.join(features)})" if features else domain

    def _extract_rule_pattern(self, source_obj):
        """提取规则模式：检测源中使用的解析方式（CSS/XPath/JSONPath/JS/变量）。"""
        patterns = []
        # 检查规则中使用的解析方式
        all_rules = json.dumps(sanitize_source_json(source_obj), ensure_ascii=False)
        if "@CSS:" in all_rules or "class." in all_rules:
            patterns.append("CSS选择器")
        if "@XPath:" in all_rules:
            patterns.append("XPath")
        if "@Json:" in all_rules or "@json:" in all_rules:
            patterns.append("JSONPath")
        if "@js:" in all_rules or "<js>" in all_rules:
            patterns.append("JavaScript")
        if "@put:" in all_rules or "@get:" in all_rules:
            patterns.append("变量存取")
        return ", ".join(patterns) if patterns else "默认CSS"

    def _format_content(self, experience_draft):
        """格式化经验内容为 Markdown。"""
        lines = [
            f"# 经验: {experience_draft.get('website_feature', 'unknown')}",
            "",
            f"- **网站**: {experience_draft.get('website_feature', 'N/A')}",
            f"- **规则模式**: {experience_draft.get('rule_pattern', 'N/A')}",
            f"- **可信度**: {experience_draft.get('confidence', 'N/A')}",
            f"- **源URL**: {experience_draft.get('source_url', 'N/A')}",
            f"- **时间**: {experience_draft.get('timestamp', 'N/A')}",
        ]
        if experience_draft.get("error_type"):
            lines.append(f"- **错误类型**: {experience_draft['error_type']}")
        if experience_draft.get("fix_method"):
            lines.append(f"- **修复方法**: {experience_draft['fix_method']}")
        return "\n".join(lines)


# 简化说明：单例模式 | 已知上限：无 | 升级路径：如需动态配置，改为从JSON加载
_manager = ExperienceManager()


def search_experience(source_url: str, source_name: str = "") -> list:
    """搜索相似案例，使用 pathlib.Path.rglob 搜索 references/troubleshooting/ 目录。

    从 source_url 提取域名进行匹配，返回相似案例列表。

    Args:
        source_url: 源URL
        source_name: 源名称（可选，兼容旧调用 search_experience(url, name)）

    Returns:
        list: 相似案例列表，每项含 file/domain/preview
    """
    return _manager.search_experience(source_url, source_name)


def write_experience(error_type: str, fix_solution: str, test_result: str, source_url: str) -> str:
    """输出经验数据到 output/experience-pending.json，供 AI agent 通过 MCP 写入 basic-memory。

    Args:
        error_type: 错误类型
        fix_solution: 修复方案
        test_result: 测试结果
        source_url: 源URL

    Returns:
        str: pending 文件路径
    """
    return _manager.write_experience(error_type, fix_solution, test_result, source_url)


def write_experience_fallback(error_type: str, fix_solution: str, source_url: str) -> str:
    """降级写入：basic-memory 不可用时写入 references/troubleshooting/auto/。

    Args:
        error_type: 错误类型
        fix_solution: 修复方案
        source_url: 源URL

    Returns:
        str: 降级文件路径
    """
    return _manager.write_experience_fallback(error_type, fix_solution, source_url)
