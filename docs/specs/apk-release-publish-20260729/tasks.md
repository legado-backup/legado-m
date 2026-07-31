# APK Release 发布功能任务清单

> **目标**：把本地打的 APK 包集成发布到 Gitee 和 GitHub 的 Release，让 App 内"检查更新"功能能下载到新版本。
>
> **技术方案**：Python 脚本调用 Gitee API 和 GitHub API 上传 APK 到 Release。

## 关键信息

| 项 | 值 |
|----|----|
| 脚本位置 | `scripts/publish_release.py` |
| 配置文件 | `scripts/publish_config.json`（token 配置，加入 `.gitignore`） |
| Python 环境 | 复用 `ai_tests/venv/Scripts/python.exe` |
| APK 命名规则 | `legado_{miss|legacy}_app_{version}.apk`，version = `3.{yy}.{MMddHH}` |
| 三包输出位置 | `output/apk/{test,release,coexist}/` |
| Gitee 仓库 | Chinashitou/legado |
| GitHub 仓库 | syq17496152/legado |
| 更新日志路径 | `assets/updateLog.md` |

## 1. 准备工作

- [ ] 1.1 确认 Gitee API token 权限（创建 Release + 上传 Asset）
- [x] 1.2 确认 GitHub API token 权限（创建 Release + 上传 Asset）——2026-07-29 用户提供PAT+Release 3.26.072917发布成功验证
- [ ] 1.3 确认 Gitee Release 文件大小限制
- [x] 1.4 创建 `scripts/` 目录（如不存在）

## 2. 配置文件

- [x] 2.1 创建 `scripts/publish_config.json` 模板（含 `gitee_token` + `github_token` + repo 配置）
- [x] 2.2 创建 `scripts/publish_config.example.json` 示例文件
- [x] 2.3 修改 `.gitignore` 添加 `scripts/publish_config.json` 排除规则

## 3. 核心脚本实现

- [x] 3.1 实现 `scripts/publish_release.py` 主入口（参数解析：`--platform gitee/github/both`）
- [x] 3.2 实现读取配置文件函数（`read_config`）
- [x] 3.3 实现扫描 APK 文件函数（`scan_apk_files`，扫描 `output/apk/{test,release,coexist}/`）
- [x] 3.4 实现版本号提取函数（`extract_version`，从 APK 文件名提取 version）
- [x] 3.5 实现读取更新日志函数（`read_update_log`，从 `assets/updateLog.md` 读取最新日期日志）
- [x] 3.6 实现 Gitee Release 创建函数（`create_gitee_release`）
- [x] 3.7 实现 Gitee Asset 上传函数（`upload_gitee_asset`）
- [x] 3.8 实现 GitHub Release 创建函数（`create_github_release`）
- [x] 3.9 实现 GitHub Asset 上传函数（`upload_github_asset`）
- [x] 3.10 实现 Release 已存在处理逻辑（追加 asset 而非报错）
- [x] 3.11 实现发布结果输出（Release URL + 下载链接）

## 4. 错误处理

- [x] 4.1 网络异常重试机制（3 次重试，指数退避）
- [x] 4.2 API token 无效错误提示
- [x] 4.3 APK 文件不存在错误提示
- [x] 4.4 Release 创建失败错误处理
- [x] 4.5 Asset 上传失败错误处理（部分失败不影响其他包）

## 5. 验证

- [x] 5.1 dry-run 测试：版本号提取+APK扫描+updateLog读取（2026-07-29 通过）
- [ ] 5.2 集成测试：发布到 Gitee（需 Gitee token）
- [x] 5.3 集成测试：发布到 GitHub（需 GitHub PAT）——2026-07-29 Release 3.26.072917发布成功（三包上传完毕，大文件用gh CLI替代Python requests解决SSLEOFError）
- [ ] 5.4 端到端验证：本地打三包 → 运行脚本 → App 内检查更新能下载

## 6. 文档

- [ ] 6.1 创建 `scripts/PUBLISH_GUIDE.md` 使用说明
- [ ] 6.2 更新 `docs/INDEX.md` 添加本功能条目
- [ ] 6.3 更新 `assets/updateLog.md` 记录新增发布脚本

## 验收标准

1. 脚本能扫描三包目录，正确提取版本号
2. 脚本能成功创建 Gitee 和 GitHub Release 并上传 APK
3. 已存在的 Release 能追加 asset 而不报错
4. App 内"检查更新"功能能拉到新版本并下载
5. 网络异常时重试机制生效，部分失败不影响其他包
6. 配置文件中的 token 不会被提交到 git 仓库
