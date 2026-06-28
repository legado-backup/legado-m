#!/usr/bin/env python3
"""
debug-source.py - 端到端书源/订阅源调试脚本（重构版）

核心逻辑已迁移到 legado_client 包：
  - legado_client.client.debug_runner: 单源调试流程
  - legado_client.client.batch_runner: 批处理调试流程
  - legado_client.analyzer.*: 错误诊断/可信度评估/源码导航/解析策略
  - legado_client.client.user_interaction: 用户交互请求
  - legado_client.experience.experience_manager: 经验闭环

JSON去重：main() 入口解析一次 source_obj，后续传递对象。
STAGE_NAMES 统一：使用字符串键（定义在 debug_runner.py 中）。

用法:
    python debug-source.py --source book_source.json --key "斗破苍穹"
    python debug-source.py --source book_source.json --key "http://..." --stage detail
    python debug-source.py --source rss_source.json --key "科技"
    python debug-source.py --batch output/rss/*.json

退出码:
    0 - 成功（所有阶段通过）
    1 - 部分失败（部分阶段失败）
    2 - 严重错误（JVM启动失败/参数错误）
    3 - 需要用户介入（需登录/Cookie/验证码/CF保护）
"""
import argparse
import json
import os
import sys

# 修复 Windows 终端编码问题（GBK 无法输出 Unicode 字符如 ⇒）
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 添加 scripts/ 目录到路径（legado_client 包在此目录下）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def main():
    parser = argparse.ArgumentParser(
        description="端到端书源/订阅源调试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 书源完整链路调试
  python debug-source.py --source book.json --key "斗破苍穹"

  # 书源单阶段调试
  python debug-source.py --source book.json --key "http://..." --stage detail
  python debug-source.py --source book.json --key "++http://..." --stage toc
  python debug-source.py --source book.json --key "--http://..." --stage content

  # 订阅源调试
  python debug-source.py --source rss.json --key "科技"

  # 批处理模式
  python debug-source.py --batch output/rss/*.json
        """
    )
    parser.add_argument("--source", help="书源/订阅源 JSON 文件路径")
    parser.add_argument("--key", help="搜索关键词或阶段标识")
    parser.add_argument("--batch", metavar="DIR_OR_GLOB",
                        help="批处理模式：指定目录或 glob 模式（如 output/rss/*.json），一次处理所有源")
    parser.add_argument("--stage", default="all",
                        choices=["all", "search", "detail", "toc", "content", "sort"],
                        help="调试阶段 (默认: all)")
    parser.add_argument("--no-reverify", action="store_true",
                        help="跳过进化后自动重新验证（5.6.3 防止无限循环）")
    parser.add_argument("--no-experience", action="store_true",
                        help="关闭经验闭环（方向4：跳过经验检索和写入）")
    parser.add_argument("--force", action="store_true",
                        help="强制执行，跳过网站类型检测")
    # 7.5/7.9: 阶段七新增命令行参数
    parser.add_argument("--import-cookie", metavar="FILE",
                        help="从浏览器导出文件导入 Cookie（Netscape/JSON 格式）")
    parser.add_argument("--proxy", metavar="URL",
                        help="HTTP/HTTPS 代理地址（如 http://127.0.0.1:8080）")
    parser.add_argument("--ua", metavar="UA",
                        help="自定义 User-Agent 字符串")
    # 方向10：多轮迭代修复闭环
    parser.add_argument("--max-iterations", type=int, default=1,
                        help="最大迭代修复次数（默认1=单次调试，>1启用迭代修复闭环）")
    # 方向3：结构化输出
    parser.add_argument("--output", metavar="FILE",
                        help="将调试结果导出为结构化JSON文件（如 report.json）")
    # 方向7.2：超时参数
    parser.add_argument("--timeout", type=int, default=30,
                        help="JVM 服务端超时秒数（默认: 30）")
    args = parser.parse_args()

    # 参数校验
    if not args.batch and not args.source:
        parser.error("--source 或 --batch 至少需要指定一个")
    if not args.batch and not args.key:
        parser.error("单源模式需要 --key 参数")

    # 批处理模式
    if args.batch:
        from legado_client.client.batch_runner import run_batch
        run_batch(args)
        return

    # 读取源文件
    if not os.path.exists(args.source):
        print(f"错误: 源文件不存在: {args.source}")
        sys.exit(2)

    with open(args.source, "r", encoding="utf-8") as f:
        raw = f.read()

    # JSON去重：入口解析一次 source_obj，后续传递对象（不再重复 json.loads）
    source_obj = json.loads(raw)
    if isinstance(source_obj, list):
        source_obj = source_obj[0] if source_obj else {}

    # 调用 legado_client 包进行调试
    from legado_client.client.debug_runner import run
    run(args, source_obj)


if __name__ == "__main__":
    main()
