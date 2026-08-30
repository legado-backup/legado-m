# GitHub Secrets 配置教程 - 签名密钥安全化

> **⚠️ 更新说明（2026-07-25）**：本文档为历史 spec 归档，记录仓库清理时的配置教程。
> 当前签名证书已改名为 `legado_release.jks`（RSA 2048位，有效期100年，别名`legado`），配置流程详见 [build-apk-guide.md](../../project-flow/build-apk-guide.md) 第三章。
> 下文中提到的 `legado.jks` 均为历史名称，实际使用时请替换为 `legado_release.jks`。

## 背景

仓库中的签名密钥文件 `.github/workflows/legado.jks` 和 `test.yml` 中的明文密码已移除/改造，CI 构建时需要从 GitHub Secrets 读取签名信息。

## 需要配置的 4 个 Secrets

| Secret 名称 | 值 | 说明 |
|-------------|------|------|
| `SIGNING_KEY_BASE64` | legado.jks 的 base64 编码内容 | 签名密钥文件（二进制→文本编码） |
| `KEY_ALIAS` | `legado` | 密钥别名 |
| `KEY_STORE_PASSWORD` | 原明文密码 | 密钥库密码 |
| `KEY_PASSWORD` | 原明文密码 | 密钥密码 |

## 步骤 1：获取 SIGNING_KEY_BASE64

在项目根目录执行：

```bash
git show HEAD:.github/workflows/legado.jks | base64 -w 0
```

> 注意：虽然文件已从工作区删除，但 git 历史中仍可访问。

输出是一长串 base64 字符串（约 3000+ 字符），复制完整内容。

**验证**：可以用以下命令验证 base64 能正确还原：

```bash
git show HEAD:.github/workflows/legado.jks | base64 -w 0 | base64 -d > test.jks
keytool -list -keystore test.jks -storepass <你的密码>
# 应输出密钥信息，确认别名是 "legado"
rm test.jks
```

## 步骤 2：在 GitHub 上配置 Secrets

1. 打开 GitHub 仓库：`https://github.com/syq17496152/legado`
2. 点击 **Settings** 标签
3. 左侧菜单点击 **Secrets and variables** → **Actions**
4. 点击 **New repository secret**
5. 逐个添加 4 个 Secret：

### 2.1 SIGNING_KEY_BASE64

- **Name**: `SIGNING_KEY_BASE64`
- **Value**: 步骤 1 中 base64 命令输出的完整字符串
- 点击 **Add secret**

### 2.2 KEY_ALIAS

- **Name**: `KEY_ALIAS`
- **Value**: `legado`
- 点击 **Add secret**

### 2.3 KEY_STORE_PASSWORD

- **Name**: `KEY_STORE_PASSWORD`
- **Value**: 原来写在 test.yml 中的密码（`gedoor_legado` 或你修改后的密码）
- 点击 **Add secret**

### 2.4 KEY_PASSWORD

- **Name**: `KEY_PASSWORD`
- **Value**: 同 KEY_STORE_PASSWORD
- 点击 **Add secret**

## 步骤 3：验证配置

### 3.1 检查 Secrets 列表

在 Settings → Secrets and variables → Actions 页面，确认有 4 个 Secret：
- SIGNING_KEY_BASE64 ✅
- KEY_ALIAS ✅
- KEY_STORE_PASSWORD ✅
- KEY_PASSWORD ✅

### 3.2 触发 CI 构建验证

1. 将变更推送到仓库
2. 打开 **Actions** 标签
3. 查看 test.yml 的 workflow 运行日志
4. 检查 "Release Apk Sign" 步骤：
   - 应输出 `给apk增加签名`
   - 不应出现 `gedoor_legado` 明文密码
   - APK 构建应成功

### 3.3 验证 APK 签名

如果 CI 构建成功，下载 APK 后验证签名：

```bash
# 下载 CI 产出的 APK
# 验证签名信息
jarsigner -verify -verbose -certs legado_app_*.apk
```

## 回滚方案

如果 CI 构建失败，可以临时回退：

1. 从 git 历史恢复 .jks 文件：`git checkout HEAD~1 -- .github/workflows/legado.jks`
2. 恢复 test.yml 中的明文密码
3. 排查失败原因后重新改造

## 常见问题

### Q: base64 编码后字符串很长，GitHub Secrets 有长度限制吗？
A: GitHub Secrets 最大 48 KB，base64 编码的 .jks 文件通常只有几 KB，不会超限。

### Q: 配置后 CI 报错 `base64: invalid input`？
A: 检查 SIGNING_KEY_BASE64 的值是否完整复制，没有多余的换行或空格。

### Q: 构建时报 `Keystore was tampered with`？
A: 密码不正确。确认 KEY_STORE_PASSWORD 和 KEY_PASSWORD 与原 .jks 文件的密码一致。

### Q: 想更换签名密钥怎么办？
A: 生成新密钥 → base64 编码 → 更新 SIGNING_KEY_BASE64 和密码 Secrets → 重新构建。
