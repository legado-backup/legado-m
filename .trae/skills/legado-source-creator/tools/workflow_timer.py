#!/usr/bin/env python3
"""
workflow_timer.py - 8.5 用户体验增强：工作流计时

为书源/订阅源创建工作流提供阶段计时能力，输出总耗时、各阶段耗时、
瓶颈阶段识别与优化建议，帮助用户定位耗时环节。

用法:
    from workflow_timer import WorkflowTimer
    timer = WorkflowTimer()
    timer.start_phase("规则解析")
    # ... 执行解析 ...
    timer.end_phase("规则解析")
    print(timer.report())
"""

import sys
import time

# 修复 Windows 终端编码
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 瓶颈阈值与优化建议
# ---------------------------------------------------------------------------

# 单阶段耗时超过此阈值（秒）视为潜在瓶颈
_BOTTLENECK_THRESHOLD = 10.0

# 阶段名 -> 优化建议（按常见工作流阶段预设）
_OPTIMIZE_TIPS = {
    "规则解析": "检查 CSS/XPath 选择器是否过宽，或页面元素过多导致遍历慢",
    "HTML抓取": "网络请求慢，检查目标站点响应速度，或启用 cookie/UA 伪装",
    "CF破盾": "Cloudflare 防护较严，建议手动导入 cf_clearance Cookie",
    "登录辅助": "Cookie 缓存失效，建议重新导入浏览器 Cookie",
    "验证码识别": "OCR 识别失败率高，建议升级 ddddocr 或手动输入",
    "规则测试": "测试用例过多或目标站点响应慢，建议减少测试样本",
    "源码验证": "JVM 仿真器启动慢，建议复用已运行的规则引擎服务",
}


class WorkflowTimer:
    """工作流阶段计时器。

    记录每个阶段的开始/结束时间，支持嵌套阶段（按调用顺序），
    report() 输出总耗时、各阶段耗时、瓶颈识别与优化建议。
    """

    def __init__(self):
        # phase_name -> {"start": float, "end": float, "duration": float}
        self._phases = {}
        # 保持阶段插入顺序
        self._order = []

    def start_phase(self, phase_name):
        """开始阶段计时。

        Args:
            phase_name: 阶段名称（如 "规则解析"、"HTML抓取"）

        Returns:
            float: 开始时间戳
        """
        if phase_name not in self._phases:
            self._phases[phase_name] = {}
            self._order.append(phase_name)
        self._phases[phase_name]["start"] = time.time()
        return self._phases[phase_name]["start"]

    def end_phase(self, phase_name):
        """结束阶段计时，计算耗时。

        Args:
            phase_name: 阶段名称

        Returns:
            float: 该阶段耗时（秒）；阶段未开始返回 0.0
        """
        phase = self._phases.get(phase_name)
        if not phase or "start" not in phase:
            return 0.0
        end = time.time()
        phase["end"] = end
        phase["duration"] = end - phase["start"]
        return phase["duration"]

    def _total_duration(self):
        """计算所有已完成阶段的总耗时"""
        return sum(p.get("duration", 0.0) for p in self._phases.values())

    def _bottleneck(self):
        """识别耗时最长的阶段（瓶颈）"""
        completed = [(name, p["duration"]) for name, p in self._phases.items()
                     if "duration" in p]
        if not completed:
            return None, 0.0
        return max(completed, key=lambda x: x[1])

    def report(self):
        """输出计时报告：总耗时+各阶段耗时+瓶颈识别+优化建议。

        Returns:
            str: 格式化的报告文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append("工作流计时报告")
        lines.append("=" * 60)

        total = self._total_duration()
        lines.append(f"总耗时: {total:.3f} 秒")
        lines.append("-" * 60)
        lines.append("各阶段耗时:")
        for name in self._order:
            phase = self._phases.get(name, {})
            duration = phase.get("duration")
            if duration is None:
                lines.append(f"  [{name}] 未结束（进行中或未调用 end_phase）")
            else:
                pct = (duration / total * 100) if total > 0 else 0.0
                lines.append(f"  [{name}] {duration:.3f}s ({pct:.1f}%)")

        # 瓶颈识别
        lines.append("-" * 60)
        bn_name, bn_dur = self._bottleneck()
        if bn_name:
            lines.append(f"瓶颈阶段: [{bn_name}] {bn_dur:.3f}s")
            if bn_dur > _BOTTLENECK_THRESHOLD:
                tip = _OPTIMIZE_TIPS.get(bn_name)
                if tip:
                    lines.append(f"优化建议: {tip}")
                else:
                    lines.append("优化建议: 该阶段耗时较长，建议检查是否存在网络/解析瓶颈")
            else:
                lines.append("（各阶段耗时均在合理范围内）")
        else:
            lines.append("瓶颈阶段: 无（尚无已完成阶段）")

        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def _self_test():
    """最小自检：覆盖正常+边界用例"""
    # 正常用例：完整流程
    t = WorkflowTimer()
    t.start_phase("阶段A")
    time.sleep(0.01)
    t.end_phase("阶段A")
    t.start_phase("阶段B")
    time.sleep(0.02)
    t.end_phase("阶段B")
    report = t.report()
    assert "总耗时" in report
    assert "阶段A" in report and "阶段B" in report
    assert "瓶颈阶段" in report
    # 瓶颈应为阶段B（耗时更长）
    bn_name, bn_dur = t._bottleneck()
    assert bn_name == "阶段B"
    assert bn_dur > 0

    # 边界用例1：未结束的阶段
    t2 = WorkflowTimer()
    t2.start_phase("未结束阶段")
    report2 = t2.report()
    assert "未结束" in report2

    # 边界用例2：空计时器
    t3 = WorkflowTimer()
    report3 = t3.report()
    assert "瓶颈阶段: 无" in report3

    # 边界用例3：end 未 start 的阶段
    t4 = WorkflowTimer()
    assert t4.end_phase("不存在") == 0.0

    print("[self_test] workflow_timer 全部通过 (4 组用例)")


if __name__ == "__main__":
    _self_test()
