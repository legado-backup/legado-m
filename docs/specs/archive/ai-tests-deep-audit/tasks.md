# tasks.md — ai_tests 深度审计与补全完善

## 1. 审计分析（只读，不修改代码）

- [x] 1.1 探索 ai_tests 目录结构
- [x] 1.2 读取 README.md / run_e2e.py / config.py / requirements.txt
- [x] 1.3 读取 fixed_test_workflow.md SOP
- [x] 1.4 审计 lib/ 10 模块实现完整性
- [x] 1.5 审计 tests/ 10 测试文件质量
- [x] 1.6 分类 scripts/ 150+ 脚本
- [x] 1.7 汇总优点/缺点/缺失项

## 2. 短期止损（🔴 高优先级，解决阻塞问题）

- [ ] 2.1 清理临时脚本：将 28 个 temp_* + 1 个 _tmp_* 脚本移到 scripts/archive/temp/
  - 验证：scripts/ 根目录无 temp_* 脚本
- [ ] 2.2 补全 requirements.txt：添加 pytest/pytest-html/pytest-xdist/pytest-cov/requests/playwright/openai/tiktoken/beautifulsoup4/lxml/click/python-dateutil/pyyaml/pytest-asyncio/pytest-mock 等实际依赖
  - 验证：pip install -r requirements.txt 成功
- [ ] 2.3 创建 conftest.py：定义 MEmu/device/临时目录等共享 fixture
  - 验证：pytest 能发现并使用 conftest fixture
- [ ] 2.4 补全 test_run_e2e.py：测试 parse_args/filter_cases/_expand_path_steps/_execute_steps_with_skip/handle_v3_reserved_args 等核心函数
  - 验证：pytest tests/test_run_e2e.py 通过
- [ ] 2.5 补全 F-P0-2~F-P0-4 用例：创建 book_source/cover_gallery/books 的 case.md
  - 验证：run_e2e.py --tc all 能解析到新用例
- [ ] 2.6 集成 M9/M16 到 run_e2e.py：--gen-test 调用 source_test_generator.generate()，--feedback 调用 feedback_loop.process()，移除"未实现"警告
  - 验证：--gen-test BookshelfActivity 生成测试骨架，--feedback 输出反馈建议

## 3. 中期完善（🟡 中优先级，提升质量）

- [ ] 3.1 归档 V5 脚本：将 40+ v5_* 脚本移到 scripts/archive/v5/
  - 验证：scripts/ 根目录仅保留活跃脚本
- [ ] 3.2 归档私有脚本：将 7 个 _v5*_* 脚本移到 scripts/archive/private/
  - 验证：scripts/ 根目录无 _ 开头脚本
- [ ] 3.3 scripts/ 目录分类：创建 core/verify/diagnose/fix/analyze 子目录
  - 验证：每个脚本归类到对应子目录
- [ ] 3.4 补全 test_memu_controller.py：测试 M1 核心方法（start/stop/wait_for_adb/is_running）
  - 验证：pytest tests/test_memu_controller.py 通过
- [ ] 3.5 增强 test_rule_analyzer.py：补全 4 规则串联判定的多场景测试
  - 验证：测试用例覆盖致命异常/警告/通过/手动四种 verdict
- [ ] 3.6 更新 README.md：M8 已实现集成✅，M9/M16 已实现待集成⚠️，B轨Python调度状态更新
  - 验证：README 无"⚠️ M8/M9/M16 未实现"描述
- [ ] 3.7 添加 lib/__init__.py：统一导出 M1-M9 模块
  - 验证：from ai_tests.lib import * 可用
- [ ] 3.8 整合 subagent_* 脚本：评估是否可合并为 lib/ 模块或归档
  - 验证：scripts/ 根目录 subagent_* 减少到必要数量

## 4. 长期优化（🟢 低优先级，锦上添花）

- [ ] 4.1 创建 pytest.ini / pyproject.toml [tool.pytest]：配置测试发现路径、标记、插件
  - 验证：pytest 可直接运行（无需指定路径）
- [ ] 4.2 CI/CD 集成：GitHub Actions 配置 E2E 测试流水线
  - 验证：PR 触发自动运行 E2E 测试
- [ ] 4.3 source_map.json 自动更新：git hook 触发 source_map.json 重建
  - 验证：源码变更后 source_map.json 自动同步
- [ ] 4.4 脚本输出目录标准化：统一 output/{category}/{timestamp}/ 约定
  - 验证：所有脚本输出遵循统一约定
- [ ] 4.5 版本号去硬编码：verify_v3.26.0717_bug_fix*.py 改为从 config.py 读取版本
  - 验证：无脚本硬编码版本号

## AOAdapt 日志

（审计阶段为只读分析，无 AOAdapt 记录）
