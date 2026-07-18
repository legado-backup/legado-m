"""统一 CLI 参数解析

薄壳包装层：将现有 debug_runner.run / validate_source / batch_runner.run_batch
适配为返回 dict 的 CLI 入口。现有函数会 sys.exit()，此处捕获 SystemExit 转为状态字典。

db 子命令和 export 子命令使用 MySQL 存储层（storage 模块）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path


def _build_debug_args(source, source_type, stage, timeout,
                      skip_db_lookup=False, db_only=False):
    """构造 debug_runner.run() 所需的 args 对象。

    debug_runner.run() 读取 args 的多个属性（key/stage/timeout/output 等），
    此处填入 CLI 入参和安全默认值。

    3.7/3.8: skip_db_lookup / db_only 参数传递给 debug_runner。
    """
    return Namespace(
        source=source,
        key="",  # CLI 不强制 --key，留空由 JVM 端处理
        stage=stage,
        timeout=timeout,
        output=None,
        proxy=None,
        ua=None,
        import_cookies=None,
        no_experience=False,
        max_iterations=1,
        force=False,
        no_reverify=False,
        skip_db_lookup=skip_db_lookup,  # 3.7: 跳过数据库查询
        db_only=db_only,                # 3.8: 仅查数据库不测试
    )


def run_debug(source, source_type, stage, timeout,
              skip_db_lookup=False, db_only=False):
    """调试单个源（包装 debug_runner.run）。

    Returns:
        dict: {"success": bool, "exit_code": int, "source": str}
    """
    from legado_client.client.debug_runner import run as _run
    from legado_client.utils.file_utils import load_source_object

    if not os.path.exists(source):
        return {"success": False, "error": f"源文件不存在: {source}"}

    with open(source, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        source_obj = load_source_object(raw)
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 解析失败: {e}"}

    args = _build_debug_args(source, source_type, stage, timeout,
                             skip_db_lookup=skip_db_lookup, db_only=db_only)

    try:
        _run(args, source_obj)
        return {"success": True, "exit_code": 0, "source": source}
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        return {"success": code == 0, "exit_code": code, "source": source}


def validate_source_file(source, source_type):
    """验证源完整性（包装 validate_source）。

    Returns:
        dict: validate_source() 的返回值，或错误字典
    """
    from legado_client.analyzer.source_validator import validate_source

    if not os.path.exists(source):
        return {"valid": False, "error": f"源文件不存在: {source}"}

    with open(source, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        source_obj = json.loads(raw)
        if isinstance(source_obj, list):
            source_obj = source_obj[0] if source_obj else {}
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"JSON 解析失败: {e}"}

    return validate_source(source_obj, source_type)


def run_batch(dir_path, source_type, output):
    """批量调试（包装 batch_runner.run_batch）。

    Returns:
        dict: {"success": bool, "exit_code": int, "dir": str}
    """
    from legado_client.client.batch_runner import run_batch as _run_batch

    if not os.path.exists(dir_path):
        return {"success": False, "error": f"目录不存在: {dir_path}"}

    args = Namespace(
        batch=dir_path,
        timeout=30,
    )

    try:
        _run_batch(args)
        return {"success": True, "exit_code": 0, "dir": dir_path, "output": output}
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        return {"success": code == 0, "exit_code": code, "dir": dir_path, "output": output}


# ---------------------------------------------------------------------------
# db 子命令：使用 MySQL 存储层
# ---------------------------------------------------------------------------

async def _ensure_db() -> bool:
    """确保数据库已初始化，返回是否可用。"""
    from legado_client.storage.database import init_db, create_tables
    from legado_client.utils.config import config

    if config.db_available:
        return True
    ok = await init_db()
    if ok:
        await create_tables()
    return ok


async def _db_init() -> None:
    """db init：建表 + 扫描 output/ 导入。"""
    from legado_client.storage.database import init_db, create_tables

    ok = await init_db()
    if not ok:
        print("警告: 数据库连接失败，初始化中止", file=sys.stderr)
        return
    await create_tables()
    print("数据库初始化完成")

    from legado_client.fetcher.scanner import scan_and_import
    counts = await scan_and_import()
    print(f"导入源: 书源 {counts.get('book', 0)} 个, 订阅源 {counts.get('rss', 0)} 个")


async def _db_migrate() -> None:
    """db migrate：执行 Alembic 迁移。"""
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"迁移失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    if result.stdout:
        print(result.stdout, end="")
    print("数据库迁移完成")


async def _db_reset() -> None:
    """db reset：删除所有表并重建。"""
    from legado_client.storage.database import init_db, create_tables, get_engine
    from legado_client.storage.models import Base

    ok = await init_db()
    if not ok:
        print("错误: 数据库连接失败", file=sys.stderr)
        sys.exit(1)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await create_tables()
    print("数据库已重置")


async def _db_import_dir(dir_path: Path) -> None:
    """db import-dir：解析指定目录下 JSON 并入库。"""
    # v3 重构（2026-07-17）：fetcher.source_parser 和 storage.repository 已归档
    try:
        from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
        from legado_client.storage.repository import bulk_upsert
    except ImportError:
        print("错误: db import-dir 功能已归档（v3 重构移除 MySQL storage 和 fetcher 模块）", file=sys.stderr)
        print("如需恢复，请从 .trae/skills/legado-source-creator-archive/ 回滚相关模块", file=sys.stderr)
        sys.exit(1)

    if not await _ensure_db():
        print("错误: 数据库不可用", file=sys.stderr)
        sys.exit(1)

    all_sources: list[dict] = []
    for json_file in dir_path.rglob("*.json"):
        if json_file.name.startswith("."):
            continue
        try:
            raw = json_file.read_text(encoding="utf-8")
            parsed = parse_source_json(raw)
            all_sources.extend(parsed)
        except Exception as e:
            print(f"  跳过 {json_file.name}: {e}")

    if not all_sources:
        print("未发现有效源文件")
        return

    deduped = deduplicate_sources(all_sources)
    new_count = await bulk_upsert(deduped)
    # 统计类型分布
    book_count = sum(1 for s in deduped if s.get("source_type") == "book")
    rss_count = len(deduped) - book_count
    print(f"导入源: 书源 {book_count} 个, 订阅源 {rss_count} 个 (新增 {new_count})")


async def _db_stats() -> None:
    """db stats：查询 Source 表统计。"""
    from sqlalchemy import func, select
    from legado_client.storage.database import get_session_factory
    from legado_client.storage.models import Source

    if not await _ensure_db():
        print("错误: 数据库不可用", file=sys.stderr)
        sys.exit(1)

    sf = get_session_factory()
    async with sf() as session:
        # 按类型统计
        stmt = select(Source.source_type, func.count(Source.id)).group_by(Source.source_type)
        result = await session.execute(stmt)
        stats = {row[0]: row[1] for row in result.all()}

    book_count = stats.get("book", 0)
    rss_count = stats.get("rss", 0)
    print(f"书源: {book_count} 个")
    print(f"订阅源: {rss_count} 个")
    print(f"总计: {book_count + rss_count} 个")


async def _db_backup(output_path: str) -> None:
    """db backup：查询所有源并导出为 JSON。"""
    from sqlalchemy import select
    from legado_client.storage.database import get_session_factory
    from legado_client.storage.models import Source

    if not await _ensure_db():
        print("错误: 数据库不可用", file=sys.stderr)
        sys.exit(1)

    sf = get_session_factory()
    async with sf() as session:
        result = await session.execute(select(Source))
        sources = result.scalars().all()
        # 每条源从 source_json 字段还原原始 JSON
        items = []
        for s in sources:
            try:
                items.append(json.loads(s.source_json))
            except (json.JSONDecodeError, TypeError):
                items.append({"sourceUrl": s.source_url, "sourceName": s.source_name})

    from legado_client.utils.file_utils import write_json
    write_json(output_path, items)
    print(f"备份完成: {len(items)} 条源 -> {output_path}")


async def _db_restore(input_path: str) -> None:
    """db restore：从 JSON 文件恢复到数据库。"""
    # v3 重构（2026-07-17）：fetcher.source_parser 和 storage.repository 已归档
    try:
        from legado_client.fetcher.source_parser import parse_source_json, deduplicate_sources
        from legado_client.storage.repository import bulk_upsert
    except ImportError:
        print("错误: db restore 功能已归档（v3 重构移除 MySQL storage 和 fetcher 模块）", file=sys.stderr)
        print("如需恢复，请从 .trae/skills/legado-source-creator-archive/ 回滚相关模块", file=sys.stderr)
        sys.exit(1)

    if not await _ensure_db():
        print("错误: 数据库不可用", file=sys.stderr)
        sys.exit(1)

    raw = Path(input_path).read_text(encoding="utf-8")
    parsed = parse_source_json(raw)
    if not parsed:
        print("备份文件中无有效源")
        return

    deduped = deduplicate_sources(parsed)
    new_count = await bulk_upsert(deduped)
    book_count = sum(1 for s in deduped if s.get("source_type") == "book")
    rss_count = len(deduped) - book_count
    print(f"恢复完成: 书源 {book_count} 个, 订阅源 {rss_count} 个 (新增 {new_count})")


def _handle_db(args: argparse.Namespace) -> None:
    """处理 db 子命令。"""
    db_cmd = args.db_command
    if db_cmd is None:
        print("用法: legado-client db {init|migrate|reset|import-dir|stats|backup|restore}")
        sys.exit(1)

    if db_cmd == "init":
        asyncio.run(_db_init())
    elif db_cmd == "migrate":
        asyncio.run(_db_migrate())
    elif db_cmd == "reset":
        asyncio.run(_db_reset())
    elif db_cmd == "import-dir":
        dir_path = Path(args.dir)
        if not dir_path.exists():
            print(f"错误: 目录不存在: {args.dir}", file=sys.stderr)
            sys.exit(1)
        asyncio.run(_db_import_dir(dir_path))
    elif db_cmd == "stats":
        asyncio.run(_db_stats())
    elif db_cmd == "backup":
        asyncio.run(_db_backup(args.output))
    elif db_cmd == "restore":
        if not Path(args.input).exists():
            print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
            sys.exit(1)
        asyncio.run(_db_restore(args.input))


# ---------------------------------------------------------------------------
# export 子命令
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# serve 子命令：启动 Web 服务
# ---------------------------------------------------------------------------

def _handle_serve(args: argparse.Namespace) -> None:
    """启动 FastAPI Web 服务。"""
    import uvicorn
    from legado_client.server.app import app
    uvicorn.run(app, host=args.host, port=args.port)


async def _export_sources(source_type: str, output_path: str, ids: list[int] | None) -> None:
    """从数据库查询指定类型源并导出。"""
    from sqlalchemy import select
    from legado_client.storage.database import get_session_factory
    from legado_client.storage.models import Source

    if not await _ensure_db():
        print("错误: 数据库不可用", file=sys.stderr)
        sys.exit(1)

    sf = get_session_factory()
    async with sf() as session:
        stmt = select(Source).where(Source.source_type == source_type)
        if ids:
            stmt = stmt.where(Source.id.in_(ids))
        result = await session.execute(stmt)
        sources = result.scalars().all()

    if not sources:
        print("未找到匹配的源", file=sys.stderr)
        sys.exit(1)

    items = []
    for s in sources:
        try:
            items.append(json.loads(s.source_json))
        except (json.JSONDecodeError, TypeError):
            items.append({"sourceUrl": s.source_url, "sourceName": s.source_name})

    from legado_client.utils.file_utils import write_json
    write_json(output_path, items)
    type_label = "书源" if source_type == "book" else "订阅源"
    print(f"导出完成: {len(items)} 个{type_label} -> {output_path}")


def _handle_export(args: argparse.Namespace) -> None:
    """处理 export 子命令。"""
    ids = None
    if args.ids:
        try:
            ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
        except ValueError:
            print("错误: --ids 格式无效，应为逗号分隔的数字（如 1,2,3）", file=sys.stderr)
            sys.exit(1)

    asyncio.run(_export_sources(args.type, args.output, ids))


def main():
    parser = argparse.ArgumentParser(prog="legado-client", description="Legado 源调试客户端")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # debug 命令（替代 debug-source.py）
    debug_parser = subparsers.add_parser("debug", help="调试单个源")
    debug_parser.add_argument("--source", required=True, help="源 JSON 文件路径")
    debug_parser.add_argument("--type", choices=["book", "rss"], default="book", help="源类型")
    debug_parser.add_argument("--stage", choices=["all", "search", "detail", "toc", "content"], default="all", help="调试阶段")
    debug_parser.add_argument("--timeout", type=int, default=30, help="超时时间（秒）")
    debug_parser.add_argument("--skip-db-lookup", action="store_true", help="跳过数据库查询（3.7）")
    debug_parser.add_argument("--db-only", action="store_true", help="仅查数据库不测试（3.8）")

    # verify 命令（替代 quick-verify.py）
    verify_parser = subparsers.add_parser("verify", help="验证源完整性")
    verify_parser.add_argument("--source", required=True, help="源 JSON 文件路径")
    verify_parser.add_argument("--type", choices=["book", "rss"], default="book", help="源类型")

    # batch 命令（替代 run-full-regression.py）
    batch_parser = subparsers.add_parser("batch", help="批量调试")
    batch_parser.add_argument("--dir", required=True, help="源文件目录")
    batch_parser.add_argument("--type", choices=["book", "rss"], default="book", help="源类型")
    batch_parser.add_argument("--output", help="输出报告路径")

    # db 子命令：数据库管理
    db_parser = subparsers.add_parser("db", help="数据库管理")
    db_sub = db_parser.add_subparsers(dest="db_command", help="数据库操作")

    # db init
    db_sub.add_parser("init", help="建表 + 扫描 output/ 导入")

    # db migrate
    db_sub.add_parser("migrate", help="执行数据库迁移")

    # db reset
    db_sub.add_parser("reset", help="删除所有表并重建")

    # db import-dir
    import_dir_parser = db_sub.add_parser("import-dir", help="导入指定目录下的源文件")
    import_dir_parser.add_argument("--dir", required=True, help="源文件目录路径")

    # db stats
    db_sub.add_parser("stats", help="显示源数量统计")

    # db backup
    backup_parser = db_sub.add_parser("backup", help="备份数据库到JSON")
    backup_parser.add_argument("--output", required=True, help="备份输出文件路径")

    # db restore
    restore_parser = db_sub.add_parser("restore", help="从JSON恢复数据库")
    restore_parser.add_argument("--input", required=True, help="备份输入文件路径")

    # export 子命令：导出源
    export_parser = subparsers.add_parser("export", help="导出源为 Legado 兼容 JSON")
    export_parser.add_argument("--type", choices=["book", "rss"], required=True, help="源类型")
    export_parser.add_argument("--output", required=True, help="输出文件路径")
    export_parser.add_argument("--ids", help="指定ID列表，逗号分隔（如 1,2,3），为空则导出全部")

    # serve 子命令：启动 Web 服务
    serve_parser = subparsers.add_parser("serve", help="启动 Web 服务")
    serve_parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    serve_parser.add_argument("--port", type=int, default=8080, help="监听端口")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # 分发到对应处理函数
    if args.command == "debug":
        result = run_debug(args.source, args.type, args.stage, args.timeout,
                           skip_db_lookup=args.skip_db_lookup, db_only=args.db_only)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "verify":
        result = validate_source_file(args.source, args.type)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "batch":
        result = run_batch(args.dir, args.type, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "db":
        _handle_db(args)
    elif args.command == "export":
        _handle_export(args)
    elif args.command == "serve":
        _handle_serve(args)


if __name__ == "__main__":
    main()
