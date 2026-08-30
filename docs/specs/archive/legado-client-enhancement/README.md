# Legado Client Enhancement

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> 规模级别：Full
> 状态：🔄 设计中

## 核心目标

将 `legado_client` Python 客户端从「仅 AI 调试工具」升级为「AI + 用户双模式管理平台」，实现四大核心能力：

1. **自动源获取** — 多渠道（yckceo.com / GitHub / URL / 本地文件 / 真机同步）自动获取书源/订阅源并入库
2. **MySQL 持久化** — 源数据、调试结果、经验教训统一存储，AI 调试时先查库复用
3. **测试-优化闭环** — 查库→测试→失败自动修复→重测→更新，形成完整闭环
4. **Web 管理界面** — Vue3 SPA 让用户浏览器即可完成查看/管理/测试/优化/推送全流程

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent / Scope / Approach / Requirements / Scenarios |
| [design.md](./design.md) | 技术设计：架构 / 数据流 / 文件变更 / ADR |
| [tasks.md](./tasks.md) | 任务清单：分阶段实施 Roadmap |

## 关键架构

```
Web Frontend (Vue3 + Element Plus)
    ↕
Web API Layer (FastAPI: RESTful + WebSocket)
    ↕
Core Services: Fetcher → Storage(MySQL) → Debugger(JVM) → 真机推送
```

## 影响范围

- `scripts/legado_client/` — Python 客户端核心代码
- `scripts/legado_client/web/` — 新增 Web API + 前端
- `scripts/legado_client/storage/` — 新增 MySQL 存储层
- `scripts/legado_client/fetcher/` — 新增多渠道源获取器
