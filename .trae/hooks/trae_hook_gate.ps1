# Trae Hook 卡点（最早一层防线）
# 依据：docs/project-rules/process-gate-architecture.md §九 / §十
#       docs/project-rules/theme-consistency-iron-rule.md §四 S3 / §十二（机读规则块）
#       TraeCode Hook 规范：https://docs.trae.cn/ide_hook-configuration-reference
#
# 【单源铁律】本脚本**不得硬编码规则**：取色禁用集从
#   ai_tests/config/gate_rules/theme_rules.json 读取（由规范 md 的 gate-config 块派生）。
#   SessionStart 注入内容从 ai_tests/config/gate_rules/session_context.md 读取。
#   规范更新流程：改规范 md 机读块 → sync_gate_rules.py --write → 本脚本自动跟随。
#   （漂移由门禁 G-17 audit_spec_gate_drift.py 检测）
#
# 设计原则
#   D1 只读 + 幂等；D2 **失败开放**（自身异常一律 exit 0，绝不阻断工作流）；
#   D3 只在"确定违规"时 deny，不确定时用 ask 或仅附上下文；D4 每条决策附「正确做法 + 豁免路径」。
#
# 注意：本文件**必须保存为 UTF-8 with BOM**，否则 PowerShell 5.1 会按 ANSI 解码导致中文乱码并解析失败。

$ErrorActionPreference = 'Stop'

function Out-Json($obj) { $obj | ConvertTo-Json -Depth 8 -Compress }

function Get-ProjDir {
  if ($env:TRAE_PROJECT_DIR) { return $env:TRAE_PROJECT_DIR }
  if ($env:CLAUDE_PROJECT_DIR) { return $env:CLAUDE_PROJECT_DIR }
  return (Get-Location).Path
}

function Read-Text($p) {
  try { if (Test-Path $p) { return (Get-Content -Raw -Encoding UTF8 $p) } } catch { }
  return $null
}

# ---- H7：运行时日志治理（参数化 + 默认值）-----------------------------------
# H7.2：invocations.log **默认关闭**（原实现每次 Hook 调用都追加一行 ⇒ 长期膨胀且含路径信息）；
#       排障时设 TRAE_HOOK_DEBUG=1 开启；写前受 MAX_LOG_BYTES 轮转保护（超限保留尾部 256 KiB）。
$MaxLogBytes = if ($env:MAX_LOG_BYTES) { [int]$env:MAX_LOG_BYTES } else { 1048576 }  # 1 MiB
$LogKeepBytes = 262144                                                              # 超限保留尾部 256 KiB
# H7.3：`*.code_changed` 状态文件按会话累积 ⇒ 启动时清理过期项（保留最近 N 个会话）
$MaxCodeChanged = if ($env:MAX_CODE_CHANGED) { [int]$env:MAX_CODE_CHANGED } else { 20 }

function Write-RotatingLog($path, $line) {
  # 追加一行并做**尾部保留式轮转**（超限时只留最后 $LogKeepBytes 字节）⇒ 有界、不会无限增长
  try {
    Add-Content -Path $path -Value $line -Encoding UTF8
    $fi = Get-Item $path -ErrorAction SilentlyContinue
    if ($fi -and $fi.Length -gt $MaxLogBytes) {
      $all = [IO.File]::ReadAllBytes($path)
      $take = [Math]::Min($LogKeepBytes, $all.Length)
      $keep = New-Object byte[] $take
      [Array]::Copy($all, $all.Length - $take, $keep, 0, $take)
      [IO.File]::WriteAllBytes($path, $keep)
    }
  } catch { }
}

function Write-DecisionLog($stateDir, $evtName, $sid, $codeChanged, $gateRan, $decision, $reason) {
  # H6.2：Hook 决策结构化留痕（event / sid / codeChanged / gateRan / decision / reason）
  # 用于回答「卡点当时为什么放行/拦截」——纯文字表述无法事后审计。
  try {
    $line = "{0} | event={1} | sid={2} | codeChanged={3} | gateRan={4} | decision={5} | reason={6}" -f `
      (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $evtName, $sid, $codeChanged, $gateRan, $decision, $reason
    Write-RotatingLog (Join-Path $stateDir 'decisions.log') $line
  } catch { }
}

function Clear-StaleCodeChanged($stateDir) {
  # H7.3：只保留最近 $MaxCodeChanged 个会话的 `*.code_changed`（按最后写时间倒序）
  try {
    $files = @(Get-ChildItem -Path $stateDir -Filter '*.code_changed' -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending)
    if ($files.Count -gt $MaxCodeChanged) {
      $files | Select-Object -Skip $MaxCodeChanged | ForEach-Object {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
      }
    }
  } catch { }
}

function Load-ThemeRules($proj) {
  # fallback（仅在配置缺失时使用，保持 fail-open）
  $fallback = @{
    rxKotlin = 'Color\(0x[0-9A-Fa-f]+|\bColor\.(White|Black|Gray|Grey|Red|Green|Blue|Yellow|Cyan|Magenta|Transparent)\b|Color\.parseColor\s*\(|(MaterialTheme\.)?colorScheme\.(surface|surfaceVariant|onSurface|onSurfaceVariant|background|secondaryContainer|outline)\b'
    rxXml = '@color/md_|@android:color/(white|black)|android:(textColor|background|tint|color)="#'
    allowFile = 'ai_tests/config/theme_token_allowlist.json'
  }
  $cfg = Join-Path $proj 'ai_tests\config\gate_rules\theme_rules.json'
  $raw = Read-Text $cfg
  if (-not $raw) { return $fallback }
  try {
    $o = $raw | ConvertFrom-Json
    $kl = @($o.bannedColorLiterals)
    $m3 = @($o.bannedM3Keys | ForEach-Object { "(MaterialTheme\.)?colorScheme\.$_" + '\b' })
    $rxk = (@($kl) + @($m3)) -join '|'
    $rxx = (@($o.bannedXmlPatterns) -join '|')
    return @{
      rxKotlin = $(if ($rxk) { $rxk } else { $fallback.rxKotlin })
      rxXml = $(if ($rxx) { $rxx } else { $fallback.rxXml })
      allowFile = $(if ($o.allowlistFile) { $o.allowlistFile } else { $fallback.allowFile })
    }
  } catch { return $fallback }
}

try {
  $proj = Get-ProjDir
  # 快速关闭开关（无需去 Trae UI 关 Hook）：存在 .trae/hooks.disabled 即立即放行
  if (Test-Path (Join-Path $proj '.trae\hooks.disabled')) { exit 0 }
  # 【卡死修复】有界读取 stdin：若 Trae 未关闭管道，ReadToEnd 会永久阻塞 ⇒ 「对话卡住」。
  # 因此最多等 1500ms；拿不到输入就 fail-open 立即放行（D2 失败开放）。
  $raw = ''
  try {
    $task = [Console]::In.ReadToEndAsync()
    if ($task.Wait(1500)) { $raw = $task.Result }
  } catch { $raw = '' }
  # H7.2：invocations.log **默认关闭**（原实现每次 Hook 调用都写一行 ⇒ 长期膨胀；排障才需要）
  # 需排障时设 TRAE_HOOK_DEBUG=1 开启，且写入受 MAX_LOG_BYTES 轮转保护（尾部保留 256 KiB）。
  if ($env:TRAE_HOOK_DEBUG -eq '1') {
    try {
      $logDir = Join-Path $proj '.trae\.hook-state'
      if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
      $logEvent = ''
      $logTool = ''
      if ($raw) {
        try {
          $p1 = $raw | ConvertFrom-Json
          $logEvent = [string]$p1.hook_event_name
          if ($p1.tool_name) { $logTool = [string]$p1.tool_name }
          if ($p1.llm_tool_name) { $logTool = $logTool + '/' + [string]$p1.llm_tool_name }
        } catch { }
      }
      Write-RotatingLog (Join-Path $logDir 'invocations.log') ("$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | event=$logEvent | tool=$logTool | rawLen=$($raw.Length)")
    } catch { }
  }
  if (-not $raw -or $raw.Trim().Length -eq 0) { exit 0 }
  $evt = $null
  if ($raw -and $raw.Trim().Length -gt 0) { $evt = $raw | ConvertFrom-Json }
  $name = $null
  if ($evt) { $name = $evt.hook_event_name }

  $stateDir = Join-Path $proj '.trae\.hook-state'
  if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
  $sid = 'default'
  if ($evt -and $evt.session_id) { $sid = [string]$evt.session_id }
  $gateMarker = Join-Path $stateDir ("$sid.gate_ran")

  $rules = Load-ThemeRules $proj
  $rxKotlin = $rules.rxKotlin
  $rxXml = $rules.rxXml
  $allowRel = $rules.allowFile

  switch ($name) {

    'SessionStart' {
      # H7.3：新会话启动即清理过期 `*.code_changed`（保留最近 $MaxCodeChanged 个会话，默认 20）
      Clear-StaleCodeChanged $stateDir
      $ctx = ''
      try {
        $ctxFile = Join-Path $proj 'ai_tests\config\gate_rules\session_context.md'
        if (Test-Path $ctxFile) { $ctx = [IO.File]::ReadAllText($ctxFile, [Text.Encoding]::UTF8) }
      } catch { $ctx = '' }
      if (-not $ctx) {
        $ctx = "【卡点体系已启用】必读：openspec-workflow.md / testing-iron-rule.md / theme-consistency-iron-rule.md / process-gate-architecture.md；统一门禁入口 ai_tests\venv\Scripts\python.exe ai_tests/scripts/run_gates.py --stage commit。"
      }
      Out-Json @{ hookSpecificOutput = @{ hookEventName = 'SessionStart'; additionalContext = $ctx } }
    }

    'UserPromptSubmit' {
      $p = ''
      if ($evt -and $evt.prompt) { $p = [string]$evt.prompt }
      $add = @()
      if ($p -match 'UI|界面|样式|主题|取色|颜色|标签|芯片|chip|顶栏|角标') {
        $add += '→ 涉 UI 取色/刷新：先做「取色归属三步」（查面 token 表 → 查同语义既有实现 → 排除 M3 派生色禁区），见 theme-consistency-iron-rule.md §四。'
      }
      if ($p -match '数据库|迁移|migration|schema|Room|实体|字段') {
        $add += '→ 涉数据库：必须加载 database-migration-safety.md；schema / AppDatabase version 变更必须做覆盖安装迁移验证。'
      }
      if ($p -match '测试|单测|用例|回归') {
        $add += '→ 涉测试：遵守 testing-iron-rule.md（修 Bug 先写失败复现用例；改码必须配套测试变更）。'
      }
      if ($p -match '发版|发布|打包|APK|tag') {
        $add += '→ 涉发布：加载 apk-publish-workflow.md + version-delivery-sync.md；交付一律走 build-legado.bat。'
      }
      if ($p -match '优化|重构|新功能|新增|修复|bug|Bug|BUG') {
        $add += '→ 涉代码变更：先做 6 维盘点（global-thinking-checklist.md）；收尾跑九项门禁 + 配对审计。'
      }
      if ($p -match '规范|卡点|门禁|hook|gate') {
        $add += '→ 涉规范/门禁自身：改规则后必须跑 sync_gate_rules.py --write 并重跑 G-15/G-17（process-gate-architecture.md §十）。'
      }
      if ($add.Count -gt 0) {
        Out-Json @{ hookSpecificOutput = @{ hookEventName = 'UserPromptSubmit'; additionalContext = ("【卡点提醒】`n" + ($add -join "`n")) } }
      }
    }

    'PreToolUse' {
      $tool = ''
      if ($evt -and $evt.tool_name) { $tool = [string]$evt.tool_name }
      $ti = $null
      if ($evt) { $ti = $evt.tool_input }

      if ($tool -match '^(Edit|Write|MultiEdit)$') {
        $path = ''
        if ($ti -and $ti.file_path) { $path = [string]$ti.file_path }
        $body = ''
        foreach ($k in @('content', 'new_string', 'new_str', 'newText', 'text', 'file_text', 'new_content', 'patch', 'edits')) {
          if ($ti -and $ti.PSObject.Properties.Name -contains $k -and $ti.$k) {
            $body += [string]($ti.$k | ConvertTo-Json -Depth 6 -Compress)
          }
        }
        # 路径归一（修复未拦截）：兼容绝对/相对、反斜杠、盘符大小写差异 ⇒ 统一截取到 app/ 或 modules/ 起始
        $rel = ([string]$path).Replace('\', '/')
        $rel = $rel -replace '^.*?(?=(app|modules)/)', ''
        $rel = $rel -replace '^[\\/]+', ''
        # H7.1：原此处写临时诊断日志（`.hook-state/` 下的一次性排查文件）。
        # 其唯一 ④ 留证（2026-09-23 15:12 真实拦截行）已**先迁移**到 `.hook-state/decisions.log`
        # 的 [hook-evidence] 段（GB-6：先迁移后删除），随后删除该写入代码与该日志文件。
        # 决策留痕改由 Write-DecisionLog 承担（结构化字段，见下）。
        # 记录「本轮改过代码」，供 Stop 判定（纯文档任务不应被 Stop 阻断）
        if ($rel -match '^(app|modules)/.*\.(kt|java|xml)$') {
          Set-Content -Path (Join-Path $stateDir ("$sid.code_changed")) -Value (Get-Date -Format o) -Encoding UTF8
        }

        # (1) 取色违规 —— 写文件前 deny
        if ($rel -match '^app/src/main/' -and $body.Length -gt 0) {
          $rx = $null
          if ($rel -match '\.(kt|java)$') { $rx = $rxKotlin }
          elseif ($rel -match '\.xml$') { $rx = $rxXml }
          if ($rx) {
            $allowFile = Join-Path $proj ($allowRel -replace '/', '\')
            $allowHit = $false
            if (Test-Path $allowFile) {
              try {
                $allow = (Get-Content $allowFile -Raw -Encoding UTF8 | ConvertFrom-Json).entries
                foreach ($e in $allow) {
                  if ($e.file -ne $rel) { continue }
                  elseif (-not $e.pattern) { $allowHit = $true; break }
                  elseif ($body -match $e.pattern) { $allowHit = $true; break }
                }
              } catch { $allowHit = $false }
            }
            if (-not $allowHit -and ($body -match $rx)) {
              $reason = @"
【PreToolUse 拦截】取色违规将被写入：$rel
命中禁用模式（来自 gate_rules/theme_rules.json，即规范 theme-consistency-iron-rule.md §十二 机读块）。
正确做法（三选一）：
  1) 查 ui-standards/color.md 面 token 归属表：卡片=cardColor、chip/Tab/次级面=tabBackgroundColor、搜索框=searchFieldBackgroundColor、分隔线=dividerColor；
  2) 查同语义既有实现（Compose 与 View 双栈都要查），取同一 token 与同一派生阶段；
  3) 确需保留（媒体画布 / 视频控制层 / 封面打底）⇒ 登记到 $allowRel（含理由/归属设置项/批准人）。
自检命令：ai_tests\venv\Scripts\python.exe ai_tests/scripts/audit_theme_token_violation.py --files $rel
"@
              Write-DecisionLog $stateDir 'PreToolUse' $sid $null $null 'deny' "取色违规: $rel"
              Out-Json @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; permissionDecision = 'deny'; permissionDecisionReason = $reason } }
            }
          }
        }

        # (2) 数据库 schema 版本变更 —— ask（需人工确认已做覆盖安装迁移验证）
        if ($rel -match 'AppDatabase\.kt$' -and $body -match '"version"\s*:|version\s*=\s*\d+') {
          $reason = @"
【PreToolUse 确认】检测到可能修改数据库版本（$rel）。
依据 database-migration-safety.md：version 递增必须配套迁移与**覆盖安装**验证（全新安装不能替代）。
请确认：①已写/改迁移逻辑 ②已准备覆盖安装测试 ③已加载 database-migration-safety.md。
"@
          Write-DecisionLog $stateDir 'PreToolUse' $sid $null $null 'ask' "数据库版本变更: $rel"
          Out-Json @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; permissionDecision = 'ask'; permissionDecisionReason = $reason } }
        }

        # (3) 改动门禁/规范自身 —— 附上下文（提醒跑漂移检测；不拦，避免误伤正当更新）
        if ($rel -match '^docs/project-rules/.*\.md$' -or $rel -match 'gate_registry\.json$' -or $rel -match '^(\.trae/hooks\.json|ai_tests/config/gate_rules/|ai_tests/config/theme_token_allowlist\.json)') {
          $ctx = @"
【卡点提示】正在修改门禁/规范自身（$rel）。
依据 process-gate-architecture.md §十（单源化与漂移防护），改完必须：
  ai_tests\venv\Scripts\python.exe ai_tests/scripts/sync_gate_rules.py --write
  ai_tests\venv\Scripts\python.exe ai_tests/scripts/audit_spec_gate_drift.py     （G-17 漂移检测）
禁止：直接改 gate_rules/*.json（生成物）；删除规范 md 的 gate-config 机读块。
"@
          Out-Json @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; additionalContext = $ctx } }
        }

        # (4) 新增 UI 组件类 —— 附上下文（提醒组件登记）
        if ($tool -match '^Write$' -and $rel -match '^app/src/main/java/.*/ui/.*\.kt$' -and (Split-Path $rel -Leaf) -match '(Chip|Tag|Badge|Card|Bar|Row|Item|Header|Banner)') {
          $ctx = @"
【卡点提示】疑似新增 UI 组件（$rel）。
依据 theme-consistency-iron-rule.md §五：新增组件类必须登记（组件名 / 归属组件族 / 取色来源面 token / 与既有组件是否同语义）。
若与既有组件同语义 ⇒ **必须复用**（禁止自造形态）。
"@
          Out-Json @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; additionalContext = $ctx } }
        }
      }

      if ($tool -match '^(RunCommand|Shell|Bash|BashCommand)$') {
        $cmd = ''
        if ($ti) {
          foreach ($k in @('command', 'cmd', 'script')) {
            if ($ti.PSObject.Properties.Name -contains $k -and $ti.$k) { $cmd += [string]$ti.$k + ' ' }
          }
        }
        $violation = $null
        if ($cmd -match '--no-verify') { $violation = '禁止用 --no-verify 跳过 git hooks（绕卡点）' }
        elseif ($cmd -match 'SKIP_GATES\s*=\s*1|--force-skip') { $violation = '禁止用 SKIP_GATES / --force-skip 跳过门禁（确需跳过必须三处留痕并经用户确认）' }
        elseif ($cmd -match 'git\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*x') { $violation = '禁止 git clean -fdx（-x 会删除被 gitignore 的文件，含签名证书）' }
        elseif ($cmd -match '(rm|Remove-Item).*(-Recurse).*(\.git/hooks|\.git\\hooks)') { $violation = '禁止删除 git hooks（绕卡点反模式）' }
        elseif ($cmd -match 'git\s+push.*(--force|-f)\b' -and $cmd -match 'master|main') { $violation = '禁止强推 master/main' }
        if ($violation) {
          $reason = @"
【PreToolUse 拦截】$violation
依据：docs/project-rules/process-gate-architecture.md §四（禁止绕卡点）。
如确需执行，请先向用户说明理由并获得确认；跳过门禁的唯一通道是 SKIP_GATES=1 且必须在 commit message 与项目记忆留痕。
"@
          Write-DecisionLog $stateDir 'PreToolUse' $sid $null $null 'deny' "绕卡点命令: $violation"
          Out-Json @{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; permissionDecision = 'deny'; permissionDecisionReason = $reason } }
        }
      }
    }

    'PostToolUse' {
      $cmd = ''
      if ($evt -and $evt.tool_input) {
        foreach ($k in @('command', 'cmd', 'script')) {
          if ($evt.tool_input.PSObject.Properties.Name -contains $k -and $evt.tool_input.$k) { $cmd += [string]$evt.tool_input.$k + ' ' }
        }
      }
      $resp = ''
      if ($evt -and $evt.tool_response) { $resp = ($evt.tool_response | ConvertTo-Json -Depth 6 -Compress) }

      $isGateCmd = $cmd -match 'run_gates\.py|audit_theme_token_violation\.py|audit_code_change_has_test\.py|audit_host_refresh_coverage\.py|audit_spec_gate_drift\.py'
      if ($isGateCmd) { Set-Content -Path $gateMarker -Value (Get-Date -Format o) -Encoding UTF8 }

      $looksFailed = $resp -match 'exit_code"\s*:\s*[1-9]|exit code [1-9]|FAIL|Traceback|Command failed'
      if ($isGateCmd -and $looksFailed) {
        $reason = @"
【PostToolUse 阻断】门禁命令执行结果异常，禁止就此继续或声明完成。
请按门禁输出修复（取色走面 token / 补调刷新钩子 / 补写测试 / 同步规范漂移），或确需保留时登记豁免。
修复后重跑：ai_tests\venv\Scripts\python.exe ai_tests/scripts/run_gates.py --stage commit
"@
        Write-DecisionLog $stateDir 'PostToolUse' $sid (Test-Path (Join-Path $stateDir ("$sid.code_changed"))) (Test-Path $gateMarker) 'block' '门禁命令输出含失败特征'
        Out-Json @{ decision = 'block'; reason = $reason }
      }
    }

    'Stop' {
      # H6.1（判据结构化）：改为**状态机**判据 —— `*.code_changed` ∧ ¬`*.gate_ran` ⇒ 阻断。
      # 原实现依赖对 last_assistant_message 的**措辞词表**（已完成/已修复/已交付…）判断
      # 「是否声明完成」，两侧都不可靠：①换词即绕过（「搞定了」不含词表词 ⇒ 放行）
      # ②误伤（回复里引用规范原文含这些词、或纯文档任务也被拦）。状态文件是**客观证据**：
      # code_changed 只在本轮真的写过 app/ 或 modules/ 源码时由 PreToolUse 落盘；
      # gate_ran 由 PostToolUse 观察到门禁命令成功执行时落盘。
      $codeChanged = Test-Path (Join-Path $stateDir ("$sid.code_changed"))
      $gateRan = Test-Path $gateMarker
      if ($codeChanged -and -not $gateRan) {
        $reason = @"
【Stop 阻断：本轮改过代码但未跑门禁】
判据（H6.1）：存在 `$sid.code_changed` 且无 `$sid.gate_ran` ⇒ 阻断。
请先运行并附退出码证据（testing-iron-rule.md / theme-consistency-iron-rule.md §二 K2）：
  ai_tests\venv\Scripts\python.exe ai_tests/scripts/run_gates.py --stage commit
说明：本轮若确无代码变更，则不会被本条拦下（无 code_changed 标记即放行），无需人工声明。
"@
        Write-DecisionLog $stateDir 'Stop' $sid $codeChanged $gateRan 'block' 'code_changed 且未跑门禁'
        Out-Json @{ decision = 'block'; reason = $reason }
      } else {
        # 放行也必须留痕（H6.2 验证标准：实测一次 Stop 后日志新增 1 行且字段齐全）
        $why = if ($codeChanged) { '已跑门禁' } else { '本轮无代码变更' }
        Write-DecisionLog $stateDir 'Stop' $sid $codeChanged $gateRan 'allow' $why
      }
    }
  }

  exit 0
} catch {
  exit 0
}