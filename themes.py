# -*- coding: utf-8 -*-
"""主题系统: 借鉴 TieZ clipboard 的「设计令牌 + 主题类」思想, 移植到 PyQt5 QSS.

QSS 不支持 CSS 变量, 因此:
- 每套主题 = 一组设计令牌 (颜色/圆角/边框/字体)
- style.qss 是模板, 用 {{token}} 占位符引用令牌
- 切换主题 = 用选中主题的令牌渲染模板 -> setStyleSheet (整体替换, 天然清旧)

5 套主题:
- deepspace 深空 (默认, 原深空科技风)
- sakura    樱花粉 (TieZ sakura)
- acrylic   毛玻璃 (TieZ acrylic 暗色版)
- paper     纸质书感 (TieZ paper)
- retro     复古3D (TieZ retro 暗色硬边)
"""

import os
import sys


def _get_base_dir():
    """与应用同目录/同打包资源目录, 用于定位 style.qss 模板."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return meipass
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# ===== 主题元数据 =====
THEMES = [
    ("deepspace", "深空"),
    ("sakura",    "樱花粉"),
    ("acrylic",   "毛玻璃"),
    ("paper",     "纸质书感"),
    ("retro",     "复古3D"),
]
THEME_IDS = [tid for tid, _ in THEMES]
DEFAULT_THEME = "deepspace"


def is_valid(theme_id):
    return theme_id in THEME_IDS


# ===== 设计令牌 =====
# 每个主题必须包含全部键, 缺失会在渲染后残留 {{key}} 导致 QSS 语法错误
_TOKEN_KEYS = [
    # 字体
    "font_family", "font_size",
    # 主窗口
    "bg", "glow_a", "glow_b",
    # 面板/控件底色
    "card", "groupbox_bg", "input", "btn_bg", "hover", "btn_pressed_bg",
    "disabled_bg", "disabled_text",
    # 边框
    "border", "border_w", "head_bg", "head_border",
    # 文字
    "text", "text_secondary", "text_muted", "text_bright", "title",
    "selection_text", "text_on_accent",
    # 强调色
    "accent", "accent_hover", "accent_soft", "accent_soft_hover",
    "accent_soft_border",
    # 渐变 (主按钮/勾选/进度条)
    "grad_a", "grad_b", "grad_hover_a", "grad_hover_b", "grad_pressed",
    "grad_check_a", "grad_check_b", "grad_progress_a", "grad_progress_b",
    # 滚动条/提示
    "scroll_bg", "scroll_thumb", "scroll_thumb_hover",
    "tooltip_bg", "tooltip_text",
    # 圆角
    "radius_sm", "radius_md", "radius_lg", "radius_pill", "radius_pill_btn",
]

THEME_TOKENS = {
    # ============ 深空 (默认) ============
    "deepspace": {
        "font_family": '"Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans SC", sans-serif',
        "font_size": "13px",
        "bg": "#14152a",
        "glow_a": "rgba(179, 108, 216, 0.08)",
        "glow_b": "rgba(95, 212, 232, 0.06)",
        "card": "#1f2138",
        "groupbox_bg": "rgba(31, 33, 56, 0.85)",
        "input": "#25243a",
        "btn_bg": "#2c2945",
        "hover": "#3a3760",
        "btn_pressed_bg": "#25243a",
        "disabled_bg": "#1f2138",
        "disabled_text": "#5c5a78",
        "border": "#2f2e48",
        "border_w": "1px",
        "head_bg": "#252940",
        "head_border": "#3a5a7a",
        "text": "#f1f2f6",
        "text_secondary": "#cccccc",
        "text_muted": "#888888",
        "text_bright": "#ffffff",
        "title": "#94e3eb",
        "selection_text": "#14152a",
        "text_on_accent": "#14152a",
        "accent": "#5fd4e8",
        "accent_hover": "#94e3eb",
        "accent_soft": "rgba(95, 212, 232, 0.08)",
        "accent_soft_hover": "rgba(95, 212, 232, 0.18)",
        "accent_soft_border": "rgba(95, 212, 232, 0.22)",
        "grad_a": "#5fd4e8",
        "grad_b": "#94e3eb",
        "grad_hover_a": "#94e3eb",
        "grad_hover_b": "#b36cd8",
        "grad_pressed": "#4ab8cc",
        "grad_check_a": "#b36cd8",
        "grad_check_b": "#5fd4e8",
        "grad_progress_a": "#5fd4e8",
        "grad_progress_b": "#b36cd8",
        "scroll_bg": "#1f2138",
        "scroll_thumb": "#2c2945",
        "scroll_thumb_hover": "#5fd4e8",
        "tooltip_bg": "#1f2138",
        "tooltip_text": "#94e3eb",
        "radius_sm": "6px",
        "radius_md": "8px",
        "radius_lg": "10px",
        "radius_pill": "12px",
        "radius_pill_btn": "10px",
    },
    # ============ 樱花粉 (TieZ sakura) ============
    "sakura": {
        "font_family": '"Microsoft YaHei UI", "Microsoft YaHei", sans-serif',
        "font_size": "13px",
        "bg": "#fdf2f5",
        "glow_a": "rgba(255, 133, 161, 0.14)",
        "glow_b": "rgba(255, 179, 199, 0.10)",
        "card": "#fff7fa",
        "groupbox_bg": "rgba(255, 245, 248, 0.85)",
        "input": "rgba(255, 255, 255, 0.72)",
        "btn_bg": "rgba(255, 255, 255, 0.55)",
        "hover": "rgba(255, 133, 161, 0.10)",
        "btn_pressed_bg": "rgba(255, 133, 161, 0.18)",
        "disabled_bg": "rgba(255, 235, 240, 0.60)",
        "disabled_text": "#c9a8b2",
        "border": "rgba(255, 133, 161, 0.30)",
        "border_w": "1px",
        "head_bg": "#fff0f4",
        "head_border": "rgba(255, 133, 161, 0.35)",
        "text": "#4a343a",
        "text_secondary": "#946c78",
        "text_muted": "#b89ca4",
        "text_bright": "#7a2f45",
        "title": "#d4607a",
        "selection_text": "#ffffff",
        "text_on_accent": "#ffffff",
        "accent": "#ff85a1",
        "accent_hover": "#ff6b8e",
        "accent_soft": "rgba(255, 133, 161, 0.10)",
        "accent_soft_hover": "rgba(255, 133, 161, 0.22)",
        "accent_soft_border": "rgba(255, 133, 161, 0.28)",
        "grad_a": "#ff9fb4",
        "grad_b": "#ff85a1",
        "grad_hover_a": "#ffb7c9",
        "grad_hover_b": "#ff6b8e",
        "grad_pressed": "#ef6c8a",
        "grad_check_a": "#ff85a1",
        "grad_check_b": "#ffb7c9",
        "grad_progress_a": "#ff85a1",
        "grad_progress_b": "#ff9fb4",
        "scroll_bg": "#fff0f4",
        "scroll_thumb": "rgba(212, 96, 122, 0.35)",
        "scroll_thumb_hover": "#ff85a1",
        "tooltip_bg": "#fff7fa",
        "tooltip_text": "#d4607a",
        "radius_sm": "6px",
        "radius_md": "8px",
        "radius_lg": "10px",
        "radius_pill": "12px",
        "radius_pill_btn": "10px",
    },
    # ============ 毛玻璃 (TieZ acrylic 暗色) ============
    "acrylic": {
        "font_family": '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif',
        "font_size": "13px",
        "bg": "#141418",
        "glow_a": "rgba(120, 138, 164, 0.20)",
        "glow_b": "rgba(74, 86, 108, 0.10)",
        "card": "rgba(28, 28, 28, 0.65)",
        "groupbox_bg": "rgba(28, 28, 28, 0.55)",
        "input": "rgba(255, 255, 255, 0.10)",
        "btn_bg": "rgba(255, 255, 255, 0.06)",
        "hover": "rgba(255, 255, 255, 0.10)",
        "btn_pressed_bg": "rgba(255, 255, 255, 0.03)",
        "disabled_bg": "rgba(255, 255, 255, 0.04)",
        "disabled_text": "#6a6a6a",
        "border": "rgba(255, 255, 255, 0.12)",
        "border_w": "1px",
        "head_bg": "rgba(36, 36, 36, 0.60)",
        "head_border": "rgba(255, 255, 255, 0.14)",
        "text": "#e8e8e8",
        "text_secondary": "#b2b2b2",
        "text_muted": "#8f8f8f",
        "text_bright": "#ffffff",
        "title": "#a8c0e8",
        "selection_text": "#ffffff",
        "text_on_accent": "#ffffff",
        "accent": "#4f7dff",
        "accent_hover": "#6f97ff",
        "accent_soft": "rgba(79, 125, 255, 0.14)",
        "accent_soft_hover": "rgba(79, 125, 255, 0.28)",
        "accent_soft_border": "rgba(79, 125, 255, 0.34)",
        "grad_a": "#4f7dff",
        "grad_b": "#6f97ff",
        "grad_hover_a": "#6f97ff",
        "grad_hover_b": "#8fb0ff",
        "grad_pressed": "#3f6ce9",
        "grad_check_a": "#4f7dff",
        "grad_check_b": "#8fb0ff",
        "grad_progress_a": "#4f7dff",
        "grad_progress_b": "#6f97ff",
        "scroll_bg": "rgba(0, 0, 0, 0.20)",
        "scroll_thumb": "rgba(96, 113, 136, 0.55)",
        "scroll_thumb_hover": "rgba(79, 125, 255, 0.72)",
        "tooltip_bg": "rgba(28, 28, 28, 0.95)",
        "tooltip_text": "#a8c0e8",
        "radius_sm": "8px",
        "radius_md": "10px",
        "radius_lg": "12px",
        "radius_pill": "12px",
        "radius_pill_btn": "10px",
    },
    # ============ 纸质书感 (TieZ paper) ============
    "paper": {
        "font_family": '"Microsoft YaHei UI", "Microsoft YaHei", "STSong", "SimSun", serif',
        "font_size": "13px",
        "bg": "#fdf6e3",
        "glow_a": "rgba(139, 90, 43, 0.06)",
        "glow_b": "rgba(139, 90, 43, 0.04)",
        "card": "#fbf1e7",
        "groupbox_bg": "rgba(255, 253, 247, 0.85)",
        "input": "#ffffff",
        "btn_bg": "#f3ead6",
        "hover": "rgba(139, 90, 43, 0.10)",
        "btn_pressed_bg": "#e8dcc0",
        "disabled_bg": "#f0e8d8",
        "disabled_text": "#b8ab93",
        "border": "#d5c4a1",
        "border_w": "1px",
        "head_bg": "#faf3e3",
        "head_border": "#d5c4a1",
        "text": "#3c3836",
        "text_secondary": "#7c6f64",
        "text_muted": "#a89984",
        "text_bright": "#4a4038",
        "title": "#8b5a2b",
        "selection_text": "#ffffff",
        "text_on_accent": "#ffffff",
        "accent": "#8b5a2b",
        "accent_hover": "#6d451e",
        "accent_soft": "rgba(139, 90, 43, 0.10)",
        "accent_soft_hover": "rgba(139, 90, 43, 0.20)",
        "accent_soft_border": "rgba(139, 90, 43, 0.28)",
        "grad_a": "#a06b32",
        "grad_b": "#8b5a2b",
        "grad_hover_a": "#b07a3c",
        "grad_hover_b": "#6d451e",
        "grad_pressed": "#7a4e24",
        "grad_check_a": "#8b5a2b",
        "grad_check_b": "#b07a3c",
        "grad_progress_a": "#8b5a2b",
        "grad_progress_b": "#c48f4e",
        "scroll_bg": "#f5eedd",
        "scroll_thumb": "#d5c4a1",
        "scroll_thumb_hover": "#8b5a2b",
        "tooltip_bg": "#fffdf7",
        "tooltip_text": "#8b5a2b",
        "radius_sm": "2px",
        "radius_md": "3px",
        "radius_lg": "4px",
        "radius_pill": "4px",
        "radius_pill_btn": "2px",
    },
    # ============ 复古3D (TieZ retro 暗色硬边) ============
    "retro": {
        "font_family": '"Consolas", "Courier New", "Microsoft YaHei", monospace',
        "font_size": "13px",
        "bg": "#181818",
        "glow_a": "rgba(255, 255, 255, 0.03)",
        "glow_b": "rgba(255, 255, 255, 0.02)",
        "card": "#1f1f1f",
        "groupbox_bg": "#1f1f1f",
        "input": "#202020",
        "btn_bg": "#2c2c2c",
        "hover": "#383838",
        "btn_pressed_bg": "#141414",
        "disabled_bg": "#1a1a1a",
        "disabled_text": "#555555",
        "border": "#000000",
        "border_w": "2px",
        "head_bg": "#222222",
        "head_border": "#000000",
        "text": "#ededed",
        "text_secondary": "#a0a0a0",
        "text_muted": "#777777",
        "text_bright": "#ffffff",
        "title": "#487bdb",
        "selection_text": "#ffffff",
        "text_on_accent": "#ffffff",
        "accent": "#487bdb",
        "accent_hover": "#5d8fe8",
        "accent_soft": "rgba(72, 123, 219, 0.16)",
        "accent_soft_hover": "rgba(72, 123, 219, 0.30)",
        "accent_soft_border": "rgba(72, 123, 219, 0.42)",
        "grad_a": "#3d69bc",
        "grad_b": "#487bdb",
        "grad_hover_a": "#487bdb",
        "grad_hover_b": "#5d8fe8",
        "grad_pressed": "#2f5396",
        "grad_check_a": "#487bdb",
        "grad_check_b": "#5d8fe8",
        "grad_progress_a": "#487bdb",
        "grad_progress_b": "#5d8fe8",
        "scroll_bg": "#181818",
        "scroll_thumb": "#383838",
        "scroll_thumb_hover": "#487bdb",
        "tooltip_bg": "#262626",
        "tooltip_text": "#487bdb",
        "radius_sm": "0px",
        "radius_md": "0px",
        "radius_lg": "0px",
        "radius_pill": "0px",
        "radius_pill_btn": "0px",
    },
}

# 兜底: 缺键时用默认主题的同键值 (开发期防错)
_BASE_TOKENS = dict(THEME_TOKENS[DEFAULT_THEME])
for _tid, _tk in THEME_TOKENS.items():
    for _k in _TOKEN_KEYS:
        _tk.setdefault(_k, _BASE_TOKENS[_k])


def get_tokens(theme_id):
    if theme_id not in THEME_TOKENS:
        theme_id = DEFAULT_THEME
    return THEME_TOKENS[theme_id]


def render_qss(theme_id, template_path=None):
    """渲染 style.qss 模板 -> 完整 QSS 字符串."""
    tokens = get_tokens(theme_id)
    if template_path is None:
        template_path = os.path.join(_get_base_dir(), "style.qss")
    with open(template_path, "r", encoding="utf-8") as f:
        qss = f.read()
    for k, v in tokens.items():
        qss = qss.replace("{{" + k + "}}", str(v))
    return qss


def preview_border_style(theme_id):
    """背景预览色卡的动态边框样式前缀 (update_bg_preview 使用)."""
    t = get_tokens(theme_id)
    return ("border: {w} solid {c};"
            "border-radius: 5px;").format(
        w=t["border_w"], c=t["head_border"])


# ===== 面板阴影 (QGraphicsDropShadowEffect, QSS 不支持 box-shadow 的补充) =====
# 每套主题定制阴影, 还原 TieZ 的 shadow token:
# 柔和主题用低透明度大模糊, retro 用 blur=0 + 偏移还原「3px 3px 0」硬边像素阴影
SHADOWS = {
    "deepspace": {"blur": 24, "dx": 0,  "dy": 5,  "color": "#66000000"},
    "sakura":    {"blur": 20, "dx": 0,  "dy": 4,  "color": "#40a05064"},
    "acrylic":   {"blur": 28, "dx": 0,  "dy": 6,  "color": "#5c000000"},
    "paper":     {"blur": 16, "dx": 0,  "dy": 3,  "color": "#333c3836"},
    "retro":     {"blur": 0,  "dx": 4,  "dy": 4,  "color": "#ff000000"},
}


def get_shadow(theme_id):
    """返回该主题的阴影参数 dict: {blur, dx, dy, color}."""
    if theme_id not in SHADOWS:
        theme_id = DEFAULT_THEME
    return SHADOWS[theme_id]
