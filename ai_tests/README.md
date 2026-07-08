# ai_tests — Legado AI 自动化测试基础设施

> **状态**：🔄 V3 设计中，实施中
> **设计文档**：[docs/specs/e2e-automated-testing/](../docs/specs/e2e-automated-testing/)

## 快速开始

```bash
# 1. 创建虚拟环境（任务 1.3）
python -m venv venv
venv\Scripts\activate

# 2. 安装依赖（任务 1.2）
pip install -r requirements.txt

# 3. 环境自检（任务 1.5）
python scripts/verify_env.py

# 4. 一键测试（任务 10.10）
python run_e2e.py --apk auto --tc all

# 5. V3 源码影响分析（任务 12.2）
python run_e2e.py --apk auto --diff HEAD~1

# 6. V3 源码→测试生成（任务 13.2）
python run_e2e.py --gen-test BookshelfActivity

# 7. V3 反馈闭环（任务 16.2）
python run_e2e.py --apk auto --tc all --feedback
```

## 目录结构

```
ai_tests/
├── config.py              # 全局配置（固化层）
├── requirements.txt       # Python 依赖
├── run_e2e.py             # 编排入口（任务 10）
├── lib/                   # 9 大模块（固化层）
│   ├── memu_controller.py         # M1 模拟器控制
│   ├── apk_deployer.py            # M2 APK 部署
│   ├── case_parser.py             # M3 用例解析器（V3 双轨）
│   ├── ui_executor.py             # M4 UI 执行器
│   ├── evidence_collector.py      # M5 证据收集器
│   ├── rule_analyzer.py           # M6 规则分析器（V3 +反馈信号）
│   ├── report_generator.py        # M7 报告生成器（V3 +affected+feedback）
│   ├── source_impact_analyzer.py  # M8 源码影响分析器（V3 新增）
│   ├── source_test_generator.py   # M9 源码→测试生成器（V3 新增）
│   ├── feedback_loop.py           # V3 反馈闭环
│   └── source_map.json            # V3 源码→UI 映射（AI 维护）
├── scripts/               # 工具脚本
│   ├── verify_env.py             # 环境自检
│   ├── init_device.py            # uiautomator2 初始化
│   └── gen_module_matrix.py      # 模块矩阵报告
├── templates/             # Jinja2 模板
│   ├── report.md.j2
│   ├── ai_prompt_template.j2
│   └── auto_test_template.j2     # V3 Python 测试骨架模板
├── tests/                # 单元测试
├── cases/                # 测试用例（持续迭代层）
│   ├── _index.md                 # 用例库总索引
│   └── {module}/                 # 按模块分组
│       ├── case.md                # A 轨 MD 用例
│       ├── auto_*.py              # B 轨 Python 用例
│       └── preconditions/         # 用户必供资源（gitignore）
├── docs/                 # 文档
│   ├── ai_collaboration_guide.md
│   ├── source_impact_guide.md     # V3
│   ├── source_test_guide.md       # V3
│   ├── known_issues.md            # V3 陷阱库
│   ├── regression_history.md      # V3 回归历史
│   ├── usage.md
│   └── troubleshooting.md
└── reports/              # 测试报告（gitignore）
```

## 固化层 vs 持续迭代层

参见 [README.md 1.9 节](../docs/specs/e2e-automated-testing/README.md)
