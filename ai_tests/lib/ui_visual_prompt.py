"""ai_tests/lib/ui_visual_prompt.py — VL UI 样式审计 prompt 模板与输出 Schema

ui-theme-gap-audit 规格 AD-02（结构化 JSON 判定）/ FR-5（VL 判定协议）。

用途：Qwen3VL 多模态截图审计的 system prompt 与 user prompt 构造器，
     以及 chat_json 输出 Schema 常量。供 scripts/ui_visual_verify.py 调用于阶段 3 R1。
依赖：ai_tests.config_ai（图像降采样由 LlmClient 内部处理，无需额外配置）。
"""
from typing import List

# === system prompt（角色 + 判定维度 + 输出约束） ===
SYSTEM_PROMPT = (
    "你是资深 Android 阅读 App UI 样式审计员。基于截图判定样式，只输出 JSON 对象，"
    "不得输出多余文字或 markdown 代码块。\n\n"
    "【必须遵守】observations 字段必须用至少 2 句话描述实际看到的内容"
    "（顶部区域颜色、主体背景色/主色、关键控件圆角与形态、搜索框/按钮样式），"
    "禁止写空字符串。若确实未发现不一致，observations 写明\"未发现不一致\"，issues 输出空数组。\n\n"
    "判定维度（逐项核验，基于图片证据，禁止臆测内容语义）：\n"
    "1. 顶部区域(top_bar)：颜色是否与页面主体协调；书架/订阅/发现/阅读记录/我的页头应随顶栏配置。\n"
    "2. 三点菜单/弹层(popup)：右侧三点菜单弹层（圆角/背景/文字色）是否与整页风格一致；"
    "旧式白色弹窗或与主题冲突记 issue。\n"
    "3. 弹框/底部弹层(dialog)：对话框/底部弹层圆角/背景/按钮风格是否统一。\n"
    "4. 圆角(corner)：卡片/按钮/搜索框圆角是否异常（标准：卡片 18dp、搜索框 18dp、按钮 12dp、列表封面 12dp）。\n"
    "5. 配色跟随主题(color_theme)：页面主色/高亮/选中态是否跟随主题；是否存在与主题冲突的硬编码颜色"
    "（纯黑/纯白/纯灰 UI 元素，视频播放控制层除外可单独标注）。\n"
    "6. 字号(typography)：正文/标题字号是否明显失衡（10-20sp 离散，仅报畸形）。\n"
    "7. 处置前后对照(before_after)：若同页有两张图，判定处置是否生效/半生效，并指出未生效区域。\n\n"
    "输出 JSON（field 名严格一致）：\n"
    "{\n"
    '  "observations": "≥2 句实际观察（技术描述，不描述内容语义）",\n'
    '  "issues": [{"element": "top_bar/search_box/dialog_more_menu 等",\n'
    '     "style_desc": "观察到的样式（含色值/圆角/形态）", "expected": "基线预期",'
    ' "actual": "实际观察", "match": true或false, "confidence": 0.0~1.0,'
    ' "reason": "不一致的技术原因推测"}\n'
    "  ]\n"
    "}\n"
    "注意：observations 与 issues 只允许技术描述（颜色/圆角/组件），禁止输出业务数据；"
    "无 issue 时 issues 必须为 []。"
)

# === user prompt 构造（页面信息 + 基线 + 图像说明） ===
def build_user_prompt(page_id: str, baseline_note: str) -> str:
    """构造 user prompt 文本。图像由调用方以多模态 content 传给 chat_json。

    page_id: 页面标识（如 BookshelfActivity / BookSourceScreen）。
    baseline_note: 基线说明（主题管理面预期，如 '主色=#7B1FA2，头部应读 TopBarConfig'）。
    """
    return (
        f"请审计页面 [{page_id}] 的样式。\n"
        f"基线预期：{baseline_note}\n"
        f"本次送审图：{IMG_PLACEHOLDER_NOTE}\n"
        "请输出 JSON（仅 JSON）。"
    )

IMG_PLACEHOLDER_NOTE = (
    "本次送审图按序组织：同一页面的截图可能成对出现（处置前 before → 处置后 after）。"
    "若成对出现请务必执行维度7（处置前后对照）：判定处置是否生效/局部生效，并指出未生效区域；"
    "不成对则为单页样式审计。图示：页面全图 → 局部放大 → 处置前后对照。"
)

# === 三图采样说明（供文档/日志） ===
SAMPLING_RULE = (
    "送审图像组：\n"
    "1) 页面全图（降采样最长边<=640，由 LlmClient.downscale_image_b64 处理）\n"
    "2) 局部放大图（头部/三点菜单/弹框单独裁图，原始分辨率）\n"
    "3) 处置前后对照图（before/after 同页两张，用于判定是否生效）"
)

# === 校准标准 ===
CALIBRATION_RULE = (
    "抽样校准：每批取 10% 命中由人工/主代理复核；若人工与 VL 判定（match 布尔）一致率 < 85%"
    "（差值 > 15%），调整 prompt 或采样并重跑该批。"
)

# === 输出 Schema（注释用途，解析由 chat_json 的 parse_json 兜底） ===
EXPECTED_SCHEMA = {
    "observations": "str",
    "issues": [
        {
            "element": "str",
            "style_desc": "str",
            "expected": "str",
            "actual": "str",
            "match": "bool",
            "confidence": "float(0-1)",
            "reason": "str",
        }
    ],
}


def prompt_smoke_test() -> None:
    """自检：模板可构造。"""
    p = build_user_prompt("BookSourceScreen", "S2 管理壳，头部应读 TopBarConfig")
    assert "BookSourceScreen" in p and "JSON" in p
    print("[PASS] ui_visual_prompt 构造自检")


if __name__ == "__main__":
    prompt_smoke_test()