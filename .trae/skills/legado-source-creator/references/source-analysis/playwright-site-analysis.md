# Playwright 网站真实分析指南（v4 反哺）

> **铁律**：生成书源/订阅源前**必须用 Playwright MCP 真实访问目标站点**分析 HTML 结构，禁止仅凭 CMS 主题名称或经验猜测字段值。
>
> **来源**：2026-07-18 v4 应用任务实战经验反哺。用户原话："必须使用 Playwright 呀，要真实分析网站，要不你帮用户通过这个 skill 写源，写的是个什么玩意？"

## 为什么必须用 Playwright（vs 其他方式）

| 方式 | 能否提取动态DOM | 能否执行JS | 能否获取完整HTML | 适用场景 |
|------|---------------|----------|---------------|---------|
| 凭经验猜测 | ❌ | ❌ | ❌ | 禁止使用 |
| WebFetch | ❌（仅静态HTML） | ❌ | 部分 | 仅适合纯静态站点 |
| curl/requests | ❌ | ❌ | 部分 | 仅适合API接口分析 |
| **Playwright MCP** | ✅ | ✅ | ✅ | **所有站点必须使用** |

**核心理由**：
1. **WordPress/Ajax 站点**：列表页 div 由 JS 动态生成，静态 HTML 看不到
2. **CF 防护站点**：必须等 JS challenge 跑完才能看到真实内容
3. **分页/排序参数**：必须实际访问页面才能发现 `?filter=popular` 等隐藏参数
4. **字段实际可用性**：CSS 选择器必须验证真实存在，不能凭主题名猜测

## 前置准备

### 1. 安装 chromium

```bash
npx --yes playwright install chromium
```

### 2. 版本不匹配问题（高频踩坑）

**症状**：MCP 调用 `playwright_navigate` 报错：
```
Executable doesn't exist at C:\Users\{user}\AppData\Local\ms-playwright\chromium_headless_shell-1200\chrome-headless-shell-win64\chrome-headless-shell.exe
```

**根因**：MCP 服务端使用固定 playwright 版本（如 v1.49.0 对应 chromium v1200），但 `npx playwright install` 安装的是最新版（如 v1228）。

**解决方案**：用 directory junction 把已安装版本映射到 MCP 期望版本（Windows 不需管理员权限）：

```python
import _winapi
_winapi.CreateJunction(
    r'C:\Users\{user}\AppData\Local\ms-playwright\chromium_headless_shell-1228',  # 实际安装
    r'C:\Users\{user}\AppData\Local\ms-playwright\chromium_headless_shell-1200'  # MCP 期望
)
# 同样为 chromium-1228 -> chromium-1200 创建 junction
```

### 3. 访问目标站点

```python
# MCP 调用（headless=true 避免弹窗）
playwright_navigate(
    url="https://{站点}/",
    headless=True,
    timeout=60000,  # CF 站点可能需要更久
    waitUntil="domcontentloaded"  # 不用 networkidle（部分资源永远在加载）
)
```

## 字段提取工作流（4个 RECOMMENDED 字段）

### JavaScript 模板（必须用 IIFE 包裹）

**重要**：`playwright_evaluate` 的 script 参数不支持顶层 `return`，必须用 IIFE `(function(){...})()` 包裹代码。

#### 一键提取4字段模板

```javascript
(function() {
  const result = {};
  
  // 1. sourceIcon: favicon / apple-touch-icon / meta image
  const iconLink = document.querySelector(
    'link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]'
  );
  result.icon = iconLink ? iconLink.href : null;
  if (!result.icon) {
    const metaImg = document.querySelector('meta[itemprop="image"]');
    result.icon = metaImg ? metaImg.content : null;
  }
  if (!result.icon) {
    result.icon = window.location.origin + '/favicon.ico';
  }
  
  // 2. searchUrl: 表单 action + 参数名
  const searchForm = document.querySelector(
    'form[action*="search"], form[id*="search"], form[class*="search"], #searchform, .search-form'
  );
  result.searchForm = searchForm ? {
    action: searchForm.action,
    method: searchForm.method,
    inputs: Array.from(searchForm.querySelectorAll('input,select')).map(i => ({
      name: i.name, type: i.type, placeholder: i.placeholder
    }))
  } : null;
  
  // 3. sortUrl: 分类导航 + 排序参数
  const allLinks = Array.from(document.querySelectorAll('a[href]'));
  result.categoryLinks = allLinks
    .filter(a => /\/category\//i.test(a.href) || /\/tags?\//i.test(a.href))
    .slice(0, 15)
    .map(a => ({ href: a.href, text: a.textContent.trim().substring(0, 30) }));
  
  // 排序参数探测（WordPress kolortube 主题常见）
  result.hotLinks = allLinks
    .filter(a => /filter=popular|filter=hot|sort=|order=/i.test(a.href))
    .slice(0, 5).map(a => a.href);
  
  // 4. ruleNextPage: 分页 CSS 选择器
  const pagination = document.querySelector(
    '.pagination, .page-nav, .nav-links, .wp-pagenavi, nav[role="navigation"], ul.page-numbers'
  );
  result.paginationHTML = pagination ? pagination.outerHTML.substring(0, 2000) : null;
  result.paginationClass = pagination ? pagination.className : null;
  
  // 额外信息：导航菜单（找分类页）
  const menu = document.querySelector('#menu-main-menu, .main-navigation ul, nav ul');
  result.menuItems = menu ? Array.from(menu.children).map(li => {
    const a = li.querySelector('a');
    return { text: a ? a.textContent.trim() : '', href: a ? a.href : '' };
  }) : null;
  
  return JSON.stringify(result, null, 2);
})();
```

### 字段映射到源 JSON

| Playwright 提取字段 | 源 JSON 字段 | 映射规则 |
|-------------------|------------|---------|
| `result.icon` | `sourceIcon` | 直接用完整URL |
| `result.searchForm.action + ?{name}={{key}}` | `searchUrl` | 用表单参数名替换为 `{{key}}` 占位符 |
| `result.categoryLinks` + `result.hotLinks` | `sortUrl` | 多分类用 `\n` 分隔，格式 `名称::URL` |
| `result.paginationHTML` 中的下一页元素 | `ruleNextPage` | 提取 a 标签的 CSS 选择器 + `@href` |

## 典型 CMS 字段模式

### WordPress kolortube 主题（实战案例）

| 字段 | 提取模式 | 源 JSON 值示例 |
|------|---------|---------------|
| sourceIcon | `link[rel="icon"]` 或 `wp-content/uploads/` 路径 | `https://{站点}/wp-content/uploads/2024/07/{文件名}.png` |
| searchUrl | 标准 WordPress `?s=` 参数 | `https://{站点}/?s={{key}}` |
| sortUrl | 主菜单 + `?filter=popular` 排序参数 + `/categories/` 全分类页 | `最新::https://{站点}/\n热门::https://{站点}/?filter=popular\n全部分类::https://{站点}/categories/` |
| ruleNextPage | Bootstrap 风格 `ul.pagination > li > a.next` | `@CSS:a.next.page-link@href` |
| ruleArticles | `div.video-block.thumbs-rotation` | 列表项容器 |
| ruleTitle | `a.infos span.title@text` | 视频标题 |
| ruleLink | `a.infos@href` | 详情页链接 |
| ruleContent | `meta[itemprop=contentURL]@content` | m3u8 直链 |
| ruleImage | `img.video-img@data-src` | 缩略图（注意 data-src 不是 src） |

### 通用提取策略

1. **sourceIcon 必有路径**：WordPress 用 `wp-content/uploads/`，Typecho 用 `usr/uploads/`，Hexo 用 `source/images/`
2. **searchUrl 必有参数**：WordPress 是 `?s=`，Typecho 是 `?s=` 或 `/search/`，Z-Blog 是 `?q=`
3. **sortUrl 三种来源**：① 主菜单分类链接 ② tag 标签链接 ③ 排序参数（`?filter=`, `?sort=`, `?order=`）
4. **ruleNextPage 两种模式**：① WordPress Bootstrap 风格 `a.next.page-link` ② 传统 `a.next` 或 `a[rel="next"]`

## 常见踩坑

### 踩坑1：顶层 return 报错

**错误**：
```
page.evaluate: SyntaxError: Illegal return statement
```

**原因**：`playwright_evaluate` 把 script 当作语句块执行，不允许顶层 `return`。

**修复**：用 IIFE 包裹：`(function(){ ... return ... })();`

### 踩坑2：chromium 版本不匹配

详见前置准备章节。

### 踩坑3：用 `networkidle` 永远不返回

**错误**：`playwright_navigate` 超时，但页面其实已加载。

**原因**：很多站点有持续轮询的 JS（统计、广告、心跳），`networkidle` 永远不会触发。

**修复**：用 `waitUntil="domcontentloaded"`（DOMContentLoaded 事件）。

### 踩坑4：headless=false 弹出浏览器窗口

**修复**：必传 `headless=True`，避免干扰用户。

### 踩坑5：被 CF challenge 拦截

**症状**：返回的 HTML 只有 `<title>Just a moment</title>`，没有真实内容。

**方案**：
1. 用 `headless=False` 让用户手动通过 challenge（仅调试用）
2. 通过后保存 cookie，写入源的 `header` 字段
3. 或者标记站点为 `unverifiable`，建议用户手动登录

### 踩坑6：fetch 仅返回静态 HTML

**症状**：用 WebFetch 获取的 HTML 中找不到列表项 div，但 Playwright 实际访问时能看到。

**原因**：列表项由 JS 动态生成，静态 HTML 没有。

**修复**：必须用 Playwright，禁止用 WebFetch 替代。

## 工作流集成到 v4 Skill

### Phase 1（分析）必经步骤（v4 强化）

```
1. Playwright 访问站点首页（headless=True, waitUntil=domcontentloaded）
2. 执行 IIFE JavaScript 提取4字段 + 导航菜单
3. 记录到 `source_ref` metadata（verified_against_source=true）
4. 识别触发字段（CF/login/captcha）→ 必须先源码验证再写规则
5. 搜索 references/ 知识库找同类经验
```

### Phase 2（生成）字段映射

```python
# Playwright 提取结果 → 源 JSON 字段映射
source = {
    'sourceIcon': playwright_result['icon'],
    'searchUrl': build_search_url(playwright_result['searchForm']),  # ?{name}={{key}}
    'sortUrl': build_sort_url(playwright_result['categoryLinks'], playwright_result['hotLinks']),
    'ruleNextPage': extract_next_page_selector(playwright_result['paginationHTML']),
}

# AI手动不写None，必填字段对照SKILL.md清单校验
# AI手动构建，sanitize/validate由SKILL.md流程保证
sanitized = {k: ('' if v is None else v) for k, v in source.items()}  # AI手动不写None
# AI手动对照SKILL.md必填字段清单校验（CRITICAL/MANDATORY/RECOMMENDED三级）
```

### 字段构建辅助函数

```python
def build_search_url(form_info):
    """从表单信息构建 searchUrl"""
    if not form_info:
        return None
    action = form_info['action'].rstrip('?')
    inputs = form_info['inputs']
    # 找文本/search类型输入
    text_input = next((i for i in inputs if i['type'] in ('text', 'search')), None)
    if text_input:
        sep = '&' if '?' in action else '?'
        return f"{action}{sep}{text_input['name']}={{{{key}}}}"
    return None

def build_sort_url(category_links, hot_links):
    """从分类链接+排序参数构建 sortUrl"""
    items = []
    if hot_links:
        items.append(f"热门::{hot_links[0]}")
    if category_links:
        # 优先 /categories/ 全分类页
        all_cat = next((l for l in category_links if '/categories/' in l['href']), None)
        if all_cat:
            items.append(f"全部分类::{all_cat['href']}")
    items.append(f"最新::{{base_url}}")  # 首页即最新
    return '\n'.join(items)

def extract_next_page_selector(pagination_html):
    """从分页HTML提取下一页CSS选择器"""
    if not pagination_html:
        return None
    # 优先 a.next.page-link（Bootstrap）
    if 'next page-link' in pagination_html:
        return '@CSS:a.next.page-link@href'
    if 'class="next"' in pagination_html:
        return '@CSS:a.next@href'
    if 'rel="next"' in pagination_html:
        return '@CSS:a[rel="next"]@href'
    return None
```

## 任务完成标准（v4 强化）

生成书源/订阅源前必须确认：
- [ ] 已用 Playwright MCP 访问目标站点首页
- [ ] 已执行 IIFE JavaScript 提取4字段技术结构
- [ ] sourceIcon/searchUrl/sortUrl/ruleNextPage 4字段值来自真实DOM提取（非猜测）
- [ ] `source_ref` metadata 标记 `verified_against_source=true`
- [ ] 必填字段清单校验通过（对照SKILL.md）
- [ ] E2E 14/14 测试无回归

## 案例：v4 应用任务（2026-07-18）

**目标站点**：站点A（WordPress kolortube 主题）
**操作流程**：
1. `npx --yes playwright install chromium` 安装 v1228
2. 创建 junction 映射 v1228 → v1200（MCP 版本不匹配）
3. `playwright_navigate` 访问首页（domcontentloaded）
4. `playwright_evaluate` 执行 IIFE 提取4字段
5. 发现站点支持 `?filter=popular` 排序参数 + `/categories/` 全分类页
6. 生成 `rssSource_skill_v4_optimized.json`，4字段全部补全
7. v4 校验器 PASSED=True
8. E2E 14/14 测试无回归

**反哺内容**：
- 本文档（Playwright 网站分析指南）
- SKILL.md Phase 1 强化（必经 Playwright）
- references/ 对应文档经验笔记
