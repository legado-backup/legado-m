# legado-source-creator-archive 归档说明

> 本目录是 legado-source-creator skill v3 重构过程中归档的功能和脚本。

## 归档原因

用户反馈"非常不满意生成书源订阅源skill干活"，深度诊断后发现 skill 职责膨胀失控（116脚本+Web界面+数据库+CLI+设备管理+11工具），需要全面重构。

v3 重构砍掉所有与"生成可用源 JSON"核心目标无关的功能，归档到本目录保留 30 天回退窗口。

## 归档日期

2026-07-17

## 保留期限

**30 天**（截至 2026-08-16）

30 天后用户未提出回退需求，将彻底删除本目录。

## 回退方法

如需回退某个归档模块：

1. 找到对应归档子目录（如 `web/` / `storage/` / `server/` 等）
2. 将子目录移动回 `.trae/skills/legado-source-creator/scripts/legado_client/{对应位置}/`
3. 检查 SKILL.md 是否需要更新引用

## 归档清单

| 子目录 | 原位置 | 说明 |
|--------|--------|------|
| `web/` | `scripts/legado_client/web/` | Vue3 前端管理界面 |
| `storage/` | `scripts/legado_client/storage/` | MySQL 数据库存储层（ORM+Repository） |
| `alembic/` | `scripts/alembic/` | Alembic 数据库迁移 |
| `server/` | `scripts/legado_client/server/` | FastAPI 服务（7路由模块） |
| `device/` | `scripts/legado_client/device/` | 设备管理 + Legado HTTP/WebSocket 代理 |
| `oneoff-scripts/` | `scripts/*.py`（83%一次性脚本） | 一次性脚本（cleanup/test/fix/batch等） |
| `unused-tools/` | `scripts/legado_client/` 中无关辅助工具 | 11个辅助工具中9个无关的 |

## 保留的核心功能（在主 skill 目录）

- SKILL.md（精简后）
- 9 个核心脚本：debug-source.py / verify-source.py / verify-selector.py / verify-decrypt.py / verify-image.py / analyze_site.py / quick-verify.py / html_fetcher.py / fetch_html.py
- references/（合并去重后约 20 个文档）
- templates/（视频播放器模板）
- test-data/（测试数据）
- 必要的工具模块（legado_client/utils/ + analyzer/ + client/ + delegate/ + experience/）

## 关联文档

- 重构 OpenSpec 文档：`docs/specs/legado-skill-v3-rebuild/`（README/spec/design/tasks）
- 深度诊断报告：`docs/temp-analysis/skill_root_cause_diagnosis.md`
- 子代理统计报告：`docs/temp-analysis/scripts_bloat_report.md` + `references_bloat_report.md`
