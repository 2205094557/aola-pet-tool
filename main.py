# -*- coding: utf-8 -*-
"""奥拉星立绘提取器 - 主程序

功能:
- 按ID或名称搜索宠物
- 显示可用资源列表
- 一键下载静态立绘
- 生成 Wallpaper Engine 动态壁纸项目
- 相机参数调整(背景色/缩放/偏移)
"""

import os
import sys
import json
import shutil
import webbrowser
import threading
import http.server
import socketserver
import io
import base64
import tempfile
import uuid
from datetime import datetime

# PyInstaller 打包时隐藏导入的依赖
import PIL
import PIL.Image
import requests
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTabWidget, QTextEdit, QProgressBar, QStatusBar, QMessageBox,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QColorDialog,
    QSplitter, QFrame, QComboBox, QFileDialog
)

from aola_api import AolaAPI


def _get_base_dir():
    """获取应用根目录，兼容 PyInstaller 打包"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，exe 所在目录
        return os.path.dirname(os.path.abspath(sys.executable))
    # 源代码模式
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _get_base_dir()


class SearchThread(QThread):
    """搜索线程"""
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, api, keyword):
        super().__init__()
        self.api = api
        self.keyword = keyword

    def run(self):
        try:
            if self.keyword.isdigit():
                # 数字: 按ID查询
                name = self.api.get_pet_name(self.keyword)
                if name:
                    self.result_signal.emit([(self.keyword, name)])
                else:
                    self.error_signal.emit(f"未找到ID为 {self.keyword} 的宠物")
            else:
                # 文字: 按名称搜索
                results = self.api.search_pets_by_name(self.keyword)
                if results:
                    self.result_signal.emit(results[:50])
                else:
                    self.error_signal.emit(f"未找到名称含「{self.keyword}」的宠物")
        except Exception as e:
            self.error_signal.emit(str(e))


class DetectThread(QThread):
    """资源检测线程"""
    result_signal = pyqtSignal(list, dict)
    error_signal = pyqtSignal(str)

    def __init__(self, api, pet_id):
        super().__init__()
        self.api = api
        self.pet_id = pet_id

    def run(self):
        try:
            resources = self.api.get_pet_resources(self.pet_id)
            info = self.api.get_pet_info(self.pet_id)
            if not resources:
                self.error_signal.emit(f"宠物 {self.pet_id} 没有可用资源")
            else:
                self.result_signal.emit(resources, info or {})
        except Exception as e:
            self.error_signal.emit(str(e))


class DownloadThread(QThread):
    """下载线程"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    files_signal = pyqtSignal(list)

    def __init__(self, api, pet_id, download_dir, items):
        super().__init__()
        self.api = api
        self.pet_id = pet_id
        self.download_dir = download_dir
        self.items = items  # list of resource dict

    def run(self):
        try:
            saved_files = []
            total = len(self.items)
            for i, item in enumerate(self.items):
                path = item["path"]
                self.progress_signal.emit(
                    int((i / total) * 100) if total > 0 else 0,
                    f"下载: {os.path.basename(path)}"
                )
                # 按类型分目录
                sub_dir = os.path.join(self.download_dir, self.pet_id, item["type"])
                os.makedirs(sub_dir, exist_ok=True)
                f = self.api.download_resource(path, sub_dir)
                if f:
                    saved_files.append(f)
                else:
                    self.finished_signal.emit(False, f"下载失败(HTTP错误或空内容): {path}")
                    return

            self.progress_signal.emit(100, "下载完成")
            self.files_signal.emit(saved_files)
            self.finished_signal.emit(True, f"成功下载 {len(saved_files)} 个文件")
        except Exception as e:
            import traceback
            self.finished_signal.emit(False, f"{e}\n{traceback.format_exc()}")


class WallpaperThread(QThread):
    """生成壁纸项目线程"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, api, pet_id, pet_name, output_dir, settings):
        super().__init__()
        self.api = api
        self.pet_id = pet_id
        self.pet_name = pet_name
        self.output_dir = output_dir
        self.settings = settings  # 含 bg_color, scale, offset_x, offset_y, resource_type

    # ===== 背景计算工具方法 =====
    @staticmethod
    def _rgb_to_hsv(r, g, b):
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        h = s = 0
        v = mx
        d = mx - mn
        if d != 0:
            s = d / mx if mx != 0 else 0
            if mx == r:
                h = ((g - b) / d + (6 if g < b else 0)) / 6
            elif mx == g:
                h = ((b - r) / d + 2) / 6
            else:
                h = ((r - g) / d + 4) / 6
        return h, s, v

    @staticmethod
    def _hsv_to_rgb(h, s, v):
        if s == 0:
            return v * 255, v * 255, v * 255
        h = h * 6
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f) if i % 2 == 0 else v * (1 - s * (1 - f))
        t = v * (1 - s * (1 - f)) if i % 2 == 0 else v * (1 - s * f)
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        return r * 255, g * 255, b * 255

    @staticmethod
    def _hsv_to_hex(h, s, v):
        r, g, b = WallpaperThread._hsv_to_rgb(h, s, v)
        return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))

    @staticmethod
    def _extract_palette(png_path, num_colors=4):
        """从PNG提取主色调 - 保持原色调,仅做适度压暗以适合做背景"""
        try:
            from PIL import Image
            img = Image.open(png_path).convert('RGBA')
            w, h = img.size

            # 采样像素
            pixels = []
            step = max(1, (w * h) // 80000)
            for y in range(0, h, step):
                for x in range(0, w, step):
                    r, g, b, a = img.getpixel((x, y))
                    if a < 30:
                        continue
                    # 过滤纯黑/纯白/极灰(通常是描线或边缘)
                    mx, mn = max(r, g, b), min(r, g, b)
                    if mx < 25:
                        continue
                    if mn > 235:
                        continue
                    if mx - mn < 12 and (mx < 50 or mx > 200):
                        continue
                    pixels.append((r, g, b))

            if len(pixels) < 20:
                return None

            # 用更细的量化(每通道16级)分桶,并记录桶内所有像素的RGB总和
            buckets = {}
            for r, g, b in pixels:
                key = (r >> 4, g >> 4, b >> 4)
                if key not in buckets:
                    buckets[key] = [0, 0, 0, 0]  # r_sum, g_sum, b_sum, count
                buckets[key][0] += r
                buckets[key][1] += g
                buckets[key][2] += b
                buckets[key][3] += 1

            # 按频率排序,取桶内真实平均色
            sorted_buckets = sorted(buckets.items(), key=lambda x: x[1][3], reverse=True)

            # 选色彩差异足够大的颜色,避免取到一堆相近色
            min_dist = 35
            chosen = []
            for key, (rs, gs, bs, cnt) in sorted_buckets:
                avg_r = rs // cnt
                avg_g = gs // cnt
                avg_b = bs // cnt
                # 检查与已选颜色的距离
                too_close = False
                for cr, cg, cb in chosen:
                    dist = abs(avg_r - cr) + abs(avg_g - cg) + abs(avg_b - cb)
                    if dist < min_dist:
                        too_close = True
                        break
                if not too_close:
                    chosen.append((avg_r, avg_g, avg_b))
                if len(chosen) >= num_colors:
                    break

            # 如果差异色不够,放宽条件再选
            if len(chosen) < num_colors:
                min_dist = 15
                for key, (rs, gs, bs, cnt) in sorted_buckets:
                    avg_r = rs // cnt
                    avg_g = gs // cnt
                    avg_b = bs // cnt
                    too_close = False
                    for cr, cg, cb in chosen:
                        dist = abs(avg_r - cr) + abs(avg_g - cg) + abs(avg_b - cb)
                        if dist < min_dist:
                            too_close = True
                            break
                    if not too_close:
                        chosen.append((avg_r, avg_g, avg_b))
                    if len(chosen) >= num_colors:
                        break

            if not chosen:
                return None

            # 转为hex,仅做适度压暗(×0.7)让背景不抢角色
            palette = []
            for r, g, b in chosen:
                r = int(r * 0.7)
                g = int(g * 0.7)
                b = int(b * 0.7)
                palette.append('#{:02x}{:02x}{:02x}'.format(r, g, b))
            return palette
        except Exception:
            return None

    @staticmethod
    def _make_gradient(colors, style="monet"):
        if len(colors) < 2:
            return f"background: {colors[0] if colors else '#000000'};"
        if style == "oil":
            c1, c2, c3 = colors[:3]
            return (
                f"background: "
                f"radial-gradient(ellipse at 20% 30%, {c2}88 0%, transparent 50%), "
                f"radial-gradient(ellipse at 80% 70%, {c3}99 0%, transparent 55%), "
                f"linear-gradient(160deg, {c1} 0%, {c2} 60%, {c3} 100%);"
            )
        else:
            angle = 135 if style == "monet" else 120
            stops = ", ".join(
                f"{c} {100 * i / (len(colors) - 1):.0f}%"
                for i, c in enumerate(colors)
            )
            return f"background: linear-gradient({angle}deg, {stops});"

    @staticmethod
    def _compute_bg_css(bg_color, mode, png_path=None, bg_image=None):
        if mode == 0:
            return f"background: {bg_color};"
        if mode == 4:
            # 自定义图片背景
            if bg_image:
                img_name = os.path.basename(bg_image)
                return (f"background: url('{img_name}') center/cover no-repeat;")
            return f"background: {bg_color};"
        palette = WallpaperThread._extract_palette(png_path) if png_path else None
        if not palette:
            from PyQt5.QtGui import QColor
            c = QColor(bg_color)
            h = c.hue() / 360.0
            s = c.saturation() / 255.0
            v = c.value() / 255.0
            if s < 0.1:
                s = 0.4
            if v < 0.15:
                v = 0.5
            if h < 0:
                h = 0.5
            if mode == 1:  # 莫奈
                palette = [
                    WallpaperThread._hsv_to_hex(h, max(0.1, s * 0.6), min(0.95, v * 1.1)),
                    WallpaperThread._hsv_to_hex((h + 0.08) % 1, max(0.2, s * 0.8), min(1.0, v * 1.2)),
                    WallpaperThread._hsv_to_hex((h + 0.15) % 1, max(0.15, s * 0.9), min(0.9, v * 0.95)),
                    WallpaperThread._hsv_to_hex((h + 0.45) % 1, max(0.1, s * 0.4), min(0.85, v * 0.85)),
                ]
                return WallpaperThread._make_gradient(palette, "monet")
            elif mode == 2:  # 油画
                palette = [
                    WallpaperThread._hsv_to_hex(h, s, min(0.9, v * 0.85)),
                    WallpaperThread._hsv_to_hex((h + 0.03) % 1, min(1, s * 1.15), min(0.95, v * 1.05)),
                    WallpaperThread._hsv_to_hex((h + 0.12) % 1, max(0.3, s * 0.7), min(1.0, v * 1.15)),
                    WallpaperThread._hsv_to_hex((h + 0.28) % 1, max(0.25, s * 0.5), min(0.8, v * 0.75)),
                ]
                return WallpaperThread._make_gradient(palette, "oil")
            else:  # 自动
                palette = [
                    WallpaperThread._hsv_to_hex(h, max(0.1, s * 0.6), min(0.95, v * 1.1)),
                    WallpaperThread._hsv_to_hex((h + 0.08) % 1, max(0.2, s * 0.8), min(1.0, v * 1.2)),
                    WallpaperThread._hsv_to_hex((h + 0.15) % 1, max(0.15, s * 0.9), min(0.9, v * 0.95)),
                    WallpaperThread._hsv_to_hex((h + 0.45) % 1, max(0.1, s * 0.4), min(0.85, v * 0.85)),
                ]
                return WallpaperThread._make_gradient(palette, "auto")
        else:
            style = "oil" if mode == 2 else ("monet" if mode == 1 else "auto")
            return WallpaperThread._make_gradient(palette, style)

    def run(self):
        try:
            pet_id = self.pet_id
            resource_type = self.settings.get("resource_type", "spine_fight")

            self.progress_signal.emit(10, "下载Spine资源...")
            success, files = self.api.download_spine_resources(
                pet_id, self.output_dir, resource_type
            )
            if not success:
                self.finished_signal.emit(
                    False, "Spine资源下载失败(可能此宠物没有动态立绘)", ""
                )
                return

            skel_file = files["skeleton"]
            atlas_file = files["atlas"]
            png_file = files["texture"]
            skel_type = "json" if skel_file.lower().endswith(".json") else "binary"

            self.progress_signal.emit(40, "复制Spine运行时...")
            # 复制 spine-webgl.js
            src_runtime = os.path.join(BASE_DIR, "web", "spine-webgl.js")
            if os.path.exists(src_runtime):
                shutil.copy(src_runtime, os.path.join(self.output_dir, "spine-webgl.js"))

            self.progress_signal.emit(60, "生成HTML...")
            # 读HTML模板
            tpl_path = os.path.join(BASE_DIR, "web", "wallpaper_template.html")
            with open(tpl_path, "r", encoding="utf-8") as f:
                tpl = f.read()

            # 填充模板 (壁纸生成时可用真实 PNG 提取颜色)
            bg_mode = self.settings.get("bg_mode", 0)
            bg_color = self.settings.get("bg_color", "#000000")
            bg_image = self.settings.get("bg_image", "")
            if bg_mode == 4:
                # 自定义图片模式: 复制背景图到输出目录
                if bg_image and os.path.isfile(bg_image):
                    dst_img = os.path.join(self.output_dir, os.path.basename(bg_image))
                    shutil.copy(bg_image, dst_img)
                bg_css = WallpaperThread._compute_bg_css(bg_color, bg_mode, None, bg_image)
            elif bg_mode > 0 and png_file and os.path.exists(png_file):
                bg_css = WallpaperThread._compute_bg_css(bg_color, bg_mode, png_file)
            else:
                bg_css = self.settings.get("bg_css", f"background: {bg_color};")
            html = tpl.replace("{{SKEL_FILE}}", os.path.basename(skel_file)) \
                      .replace("{{ATLAS_FILE}}", os.path.basename(atlas_file)) \
                      .replace("{{TEXTURE_FILE}}", os.path.basename(png_file)) \
                      .replace("{{SKEL_TYPE}}", skel_type) \
                      .replace("{{BG_CSS}}", bg_css) \
                      .replace("{{BG_COLOR}}", bg_color) \
                      .replace("{{CAMERA_SCALE}}", str(self.settings.get("scale", 1.0))) \
                      .replace("{{CAMERA_OFFSET_X}}", str(self.settings.get("offset_x", 0))) \
                      .replace("{{CAMERA_OFFSET_Y}}", str(self.settings.get("offset_y", 0)))

            # 写 index.html
            index_html = os.path.join(self.output_dir, "index.html")
            with open(index_html, "w", encoding="utf-8") as f:
                f.write(html)

            self.progress_signal.emit(80, "生成 project.json...")
            # 生成 Wallpaper Engine 项目配置(必须严格符合官方 schema,否则会崩溃)
            project_json = {
                "file": "index.html",
                "general": {
                    "properties": {
                        "scalectrl": {
                            "text": "缩放",
                            "type": "slider",
                            "value": float(self.settings.get("scale", 1.0)),
                            "min": 0.1,
                            "max": 3.0,
                            "editable": True
                        },
                        "offsetx": {
                            "text": "水平偏移",
                            "type": "slider",
                            "value": int(self.settings.get("offset_x", 0)),
                            "min": -1000,
                            "max": 1000,
                            "editable": True
                        },
                        "offsety": {
                            "text": "垂直偏移",
                            "type": "slider",
                            "value": int(self.settings.get("offset_y", 0)),
                            "min": -1000,
                            "max": 1000,
                            "editable": True
                        }
                    }
                },
                "title": f"{self.pet_name} ({pet_id})",
                "type": "web"
            }
            with open(os.path.join(self.output_dir, "project.json"), "w", encoding="utf-8") as f:
                json.dump(project_json, f, ensure_ascii=False, indent=2)

            self.progress_signal.emit(100, "壁纸项目生成完成!")
            self.finished_signal.emit(True, "壁纸项目生成成功", self.output_dir)
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")


class GifRecorderHandler(http.server.SimpleHTTPRequestHandler):
    """GIF录制HTTP处理类 - 支持帧上传和GIF生成"""

    frame_store = {}
    gif_output_path = None
    gif_session_id = None

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if self.path == '/upload-frame':
            self._handle_upload_frame(body)
        elif self.path == '/generate-gif':
            self._handle_generate_gif(body)
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/get-gif':
            self._handle_get_gif()
        else:
            super().do_GET()

    def _handle_upload_frame(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            frame_index = data['frame_index']
            total_frames = data['total_frames']
            data_url = data['data_url']

            header, b64_data = data_url.split(',', 1)
            img_bytes = base64.b64decode(b64_data)

            session = GifRecorderHandler.gif_session_id
            if session not in GifRecorderHandler.frame_store:
                GifRecorderHandler.frame_store[session] = {}
            GifRecorderHandler.frame_store[session][frame_index] = img_bytes

            response = json.dumps({
                'status': 'ok',
                'frame': frame_index,
                'stored': len(GifRecorderHandler.frame_store[session])
            })
            self._send_json(200, response)
        except Exception as e:
            self._send_json(500, json.dumps({'status': 'error', 'message': str(e)}))

    def _handle_generate_gif(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            total_frames = data['total_frames']
            fps = data['fps']
            width = data['width']
            height = data['height']
            bg_color = data.get('bg_color', '#2a2b33')
            duration_ms = int(1000 / fps)

            session = GifRecorderHandler.gif_session_id
            frames_dict = GifRecorderHandler.frame_store.get(session, {})

            if len(frames_dict) < total_frames:
                self._send_json(500, json.dumps({
                    'status': 'error',
                    'message': f'帧数据不完整: 期望{total_frames}帧, 实际{len(frames_dict)}帧'
                }))
                return

            from PIL import Image

            sorted_frames = sorted(frames_dict.items(), key=lambda x: x[0])
            pil_frames = []

            for idx, img_bytes in sorted_frames:
                img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                if img.size != (width, height):
                    img = img.resize((width, height), Image.LANCZOS)
                pil_frames.append(img)

            output_dir = os.path.dirname(GifRecorderHandler.gif_output_path)
            os.makedirs(output_dir, exist_ok=True)
            output_path = GifRecorderHandler.gif_output_path

            if pil_frames:
                first_frame = pil_frames[0]
                first_frame.save(
                    output_path,
                    save_all=True,
                    append_images=pil_frames[1:],
                    duration=duration_ms,
                    loop=0,
                    optimize=False
                )

            GifRecorderHandler.frame_store.pop(session, None)

            filename = os.path.basename(output_path)
            self._send_json(200, json.dumps({
                'status': 'ok',
                'filename': filename,
                'total_frames': len(pil_frames)
            }))
        except Exception as e:
            import traceback
            self._send_json(500, json.dumps({
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }))

    def _handle_get_gif(self):
        if GifRecorderHandler.gif_output_path and os.path.exists(GifRecorderHandler.gif_output_path):
            self.send_response(200)
            self.send_header('Content-Type', 'image/gif')
            self.send_header('Content-Disposition',
                             f'attachment; filename="{os.path.basename(GifRecorderHandler.gif_output_path)}"')
            self.end_headers()
            with open(GifRecorderHandler.gif_output_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, 'GIF not found')

    def _send_json(self, status_code, json_str):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json_str.encode('utf-8'))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = AolaAPI()
        self.current_pet_id = None
        self.current_pet_name = None
        self.current_resources = []
        self.current_saved_files = []
        self._auto_download = False

        self.download_dir = os.path.join(BASE_DIR, "downloads")
        self.wallpapers_dir = os.path.join(BASE_DIR, "wallpapers")

        self.setWindowTitle("奥拉星立绘提取器 v2.0")
        self.setMinimumSize(1100, 720)
        self._build_ui()
        self._apply_style()
        self.update_bg_preview()

    def _apply_style(self):
        # 从 style.qss 文件加载样式，避免代码中长字符串导致 PyInstaller 解析错误
        qss_path = os.path.join(BASE_DIR, "style.qss")
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    qss = f.read()
                self.setStyleSheet(qss)
                return
            except Exception:
                pass
        # 回退: 空样式 (使用 Qt 默认主题)
        self.setStyleSheet("")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # ===== 顶部: 搜索区 =====
        search_box = QGroupBox("搜索宠物")
        sb_layout = QHBoxLayout(search_box)
        sb_layout.addWidget(QLabel("ID或名称:"))
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("输入宠物ID(如5943)或名称(如羲和)")
        self.input_search.returnPressed.connect(self.on_search)
        sb_layout.addWidget(self.input_search, 1)
        self.btn_search = QPushButton("搜索")
        self.btn_search.setObjectName("btnSearch")
        self.btn_search.clicked.connect(self.on_search)
        sb_layout.addWidget(self.btn_search)
        root.addWidget(search_box)

        # ===== 中间: 主工作区 =====
        splitter = QSplitter(Qt.Horizontal)

        # 左侧: 搜索结果列表
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("搜索结果:"))
        self.list_results = QListWidget()
        self.list_results.itemDoubleClicked.connect(self.on_result_double_click)
        ll.addWidget(self.list_results, 1)
        self.btn_detect = QPushButton("检测资源")
        self.btn_detect.clicked.connect(self.on_detect_resources)
        ll.addWidget(self.btn_detect)
        splitter.addWidget(left)

        # 中间: 资源列表 + 信息
        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(0, 0, 0, 0)
        self.label_pet_info = QLabel("宠物信息: (未选择)")
        self.label_pet_info.setWordWrap(True)
        self.label_pet_info.setStyleSheet(
            "padding:10px 14px;"
            "background: #252940;"
            "border: 1px solid #3a5a7a;"
            "border-radius: 8px;"
            "color: #ffffff;")
        ml.addWidget(self.label_pet_info)
        ml.addWidget(QLabel("可用资源:"))
        self.list_resources = QListWidget()
        ml.addWidget(self.list_resources, 1)

        res_btns = QHBoxLayout()
        self.btn_sel_all = QPushButton("全选")
        self.btn_sel_all.clicked.connect(self.on_select_all)
        res_btns.addWidget(self.btn_sel_all)
        self.btn_sel_none = QPushButton("取消全选")
        self.btn_sel_none.clicked.connect(self.on_select_none)
        res_btns.addWidget(self.btn_sel_none)
        self.btn_download_sel = QPushButton("下载选中")
        self.btn_download_sel.setObjectName("btnDownloadSel")
        self.btn_download_sel.clicked.connect(self.on_download_selected)
        res_btns.addWidget(self.btn_download_sel)
        self.btn_download_all = QPushButton("一键全下")
        self.btn_download_all.clicked.connect(self.on_download_all)
        res_btns.addWidget(self.btn_download_all)
        ml.addLayout(res_btns)
        splitter.addWidget(mid)

        # 右侧: 预览区 + 壁纸设置
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("预览:"))
        self.label_preview = QLabel("下载后显示预览")
        self.label_preview.setAlignment(Qt.AlignCenter)
        self.label_preview.setMinimumHeight(200)
        self.label_preview.setStyleSheet(
            "background: #252940;"
            "border: 1px solid #3a5a7a;"
            "border-radius: 8px; color: #cccccc;")
        rl.addWidget(self.label_preview)

        # 壁纸参数设置
        wp_box = QGroupBox("壁纸参数设置")
        wp_form = QFormLayout(wp_box)

        # 背景模式
        self.cbo_bg_mode = QComboBox()
        self.cbo_bg_mode.addItems(["纯色背景", "莫奈渐变", "油画质感", "自动取色", "自定义图片"])
        self.cbo_bg_mode.setToolTip("选择背景样式模式")
        self.cbo_bg_mode.currentIndexChanged.connect(self.on_bg_mode_change)
        wp_form.addRow("背景模式:", self.cbo_bg_mode)

        # 自定义背景图片选择
        self.input_bg_image = QLineEdit()
        self.input_bg_image.setPlaceholderText("选择背景图片路径...")
        self.input_bg_image.textChanged.connect(self.update_bg_preview)
        self.btn_pick_image = QPushButton("浏览")
        self.btn_pick_image.clicked.connect(self.on_pick_bg_image)
        img_row = QHBoxLayout()
        img_row.addWidget(self.input_bg_image)
        img_row.addWidget(self.btn_pick_image)
        self.img_row_widget = QWidget()
        self.img_row_widget.setLayout(img_row)
        wp_form.addRow("背景图片:", self.img_row_widget)
        self.img_row_widget.setVisible(False)

        self.input_bg_color = QLineEdit("#000000")
        self.btn_pick_color = QPushButton("选色")
        self.btn_pick_color.clicked.connect(self.on_pick_color)
        color_row = QHBoxLayout()
        color_row.addWidget(self.input_bg_color)
        color_row.addWidget(self.btn_pick_color)
        wp_form.addRow("背景色:", color_row)

        # 预览当前背景
        self.lbl_bg_preview = QLabel("  背景预览  ")
        self.lbl_bg_preview.setMinimumHeight(40)
        self.lbl_bg_preview.setStyleSheet(
            "border: 1px solid #3a5a7a;"
            "border-radius: 7px;")
        self.lbl_bg_preview.setAlignment(Qt.AlignCenter)
        wp_form.addRow("背景预览:", self.lbl_bg_preview)

        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.1, 5.0)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(1.0)
        wp_form.addRow("缩放:", self.spin_scale)

        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setRange(-2000, 2000)
        self.spin_offset_x.setSingleStep(10)
        wp_form.addRow("水平偏移:", self.spin_offset_x)

        self.spin_offset_y = QSpinBox()
        self.spin_offset_y.setRange(-2000, 2000)
        self.spin_offset_y.setSingleStep(10)
        wp_form.addRow("垂直偏移:", self.spin_offset_y)

        self.btn_use_breath = QPushButton("使用newbreath资源(更小更流畅)")
        self.btn_use_breath.setCheckable(True)
        self.btn_use_breath.setChecked(True)
        self.btn_use_breath.setToolTip("默认用petmovie(newbreath),取消勾选改用petfightassets(战斗立绘)")
        wp_form.addRow(self.btn_use_breath)

        rl.addWidget(wp_box)

        # 壁纸操作按钮
        wp_btns = QHBoxLayout()
        self.btn_preview = QPushButton("预览动态")
        self.btn_preview.setObjectName("btnPreview")
        self.btn_preview.clicked.connect(self.on_preview_spine)
        wp_btns.addWidget(self.btn_preview)
        self.btn_export_wp = QPushButton("导出为壁纸")
        self.btn_export_wp.setObjectName("btnExportWp")
        self.btn_export_wp.clicked.connect(self.on_export_wallpaper)
        wp_btns.addWidget(self.btn_export_wp)
        self.btn_export_gif = QPushButton("导出GIF")
        self.btn_export_gif.setObjectName("btnExportGif")
        self.btn_export_gif.clicked.connect(self.on_export_gif)
        wp_btns.addWidget(self.btn_export_gif)
        rl.addLayout(wp_btns)

        self.btn_open_dir = QPushButton("打开下载目录")
        self.btn_open_dir.clicked.connect(self.open_download_dir)
        rl.addWidget(self.btn_open_dir)

        rl.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([200, 380, 420])
        root.addWidget(splitter, 1)

        # ===== 底部: 日志 + 进度 =====
        log_box = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_box)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)
        root.addWidget(log_box)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.setStatusBar(QStatusBar())
        self.log_msg("软件已就绪,输入ID或名称开始")
        self.statusBar().showMessage("就绪")

    # ============ 工具方法 ============
    def log_msg(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")

    def get_current_pet_id(self):
        if self.current_pet_id:
            return self.current_pet_id
        text = self.input_search.text().strip()
        if text.isdigit():
            return text
        return None

    # ============ 搜索 ============
    def on_search(self):
        keyword = self.input_search.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入ID或名称")
            return
        self.log_msg(f"搜索: {keyword}")
        self.list_results.clear()
        self.btn_search.setEnabled(False)
        self.thread_search = SearchThread(self.api, keyword)
        self.thread_search.result_signal.connect(self.on_search_done)
        self.thread_search.error_signal.connect(self.on_search_error)
        self.thread_search.start()

    def on_search_done(self, results):
        self.btn_search.setEnabled(True)
        for pid, name in results:
            item = QListWidgetItem(f"[{pid}] {name}")
            item.setData(Qt.UserRole, (pid, name))
            self.list_results.addItem(item)
        self.log_msg(f"找到 {len(results)} 个结果")

        # 输入ID(数字)时,自动检测+下载;仅1个结果时自动检测
        keyword = self.input_search.text().strip()
        if keyword.isdigit():
            self._auto_download = True
            self.list_results.setCurrentRow(0)
            self.on_detect_resources()
        elif len(results) == 1:
            self._auto_download = False
            self.list_results.setCurrentRow(0)
            self.on_detect_resources()
            self.statusBar().showMessage(f"已自动检测 [{results[0][0]}] {results[0][1]} 的资源")
        else:
            self._auto_download = False
            self.statusBar().showMessage(f"找到 {len(results)} 个结果,双击查看资源")

    def on_search_error(self, err):
        self.btn_search.setEnabled(True)
        self.log_msg(f"搜索失败: {err}")
        QMessageBox.warning(self, "搜索失败", err)

    def on_result_double_click(self, item):
        pid, name = item.data(Qt.UserRole)
        self.input_search.setText(pid)
        self.current_pet_id = pid
        self.current_pet_name = name
        self.log_msg(f"选择: [{pid}] {name}")
        self.on_detect_resources()

    # ============ 资源检测 ============
    def on_detect_resources(self):
        # 优先取双击选中的,否则用输入框
        item = self.list_results.currentItem()
        if item:
            pid, name = item.data(Qt.UserRole)
            self.current_pet_id = pid
            self.current_pet_name = name
        else:
            pid = self.get_current_pet_id()
            if not pid:
                QMessageBox.warning(self, "提示", "请先选择或输入宠物ID")
                return
            self.current_pet_id = pid
            self.current_pet_name = self.api.get_pet_name(pid) or pid

        self.log_msg(f"检测资源: [{pid}] {self.current_pet_name}")
        self.list_resources.clear()
        self.btn_detect.setEnabled(False)
        self.thread_detect = DetectThread(self.api, pid)
        self.thread_detect.result_signal.connect(self.on_detect_done)
        self.thread_detect.error_signal.connect(self.on_detect_error)
        self.thread_detect.start()

    def on_detect_done(self, resources, info):
        self.btn_detect.setEnabled(True)
        self.current_resources = resources

        # 显示宠物信息
        if info:
            info_text = (f"宠物信息: [{info.get('id','')}] {info.get('name','')}\n"
                         f"属性: {info.get('elements','')}  系别: {info.get('types','')}\n"
                         f"描述: {info.get('description','')[:60]}")
        else:
            info_text = f"宠物信息: [{self.current_pet_id}] {self.current_pet_name}"
        self.label_pet_info.setText(info_text)

        # 显示资源列表
        has_fight = False
        has_breath = False
        for r in resources:
            text = f"[{r['type']}] {r['desc']} - {os.path.basename(r['path'])}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r)
            item.setCheckState(Qt.Checked)
            self.list_resources.addItem(item)
            if r['type'] == 'spine_fight':
                has_fight = True
            elif r['type'] == 'spine_breath':
                has_breath = True

        # 自动选择可用的Spine资源类型(优先newbreath)
        if has_breath:
            self.btn_use_breath.setChecked(True)
        elif has_fight:
            self.btn_use_breath.setChecked(False)

        self.log_msg(f"检测到 {len(resources)} 个资源")
        self.statusBar().showMessage(f"检测到 {len(resources)} 个资源")

        # 输入ID触发的自动下载
        if self._auto_download:
            self._auto_download = False
            self.log_msg("自动下载中...")
            self.statusBar().showMessage("自动下载中...")
            QTimer.singleShot(200, self.on_download_all)

    def on_detect_error(self, err):
        self.btn_detect.setEnabled(True)
        self.log_msg(f"检测失败: {err}")
        QMessageBox.warning(self, "检测失败", err)

    # ============ 全选/取消全选 ============
    def on_select_all(self):
        for i in range(self.list_resources.count()):
            self.list_resources.item(i).setCheckState(Qt.Checked)

    def on_select_none(self):
        for i in range(self.list_resources.count()):
            self.list_resources.item(i).setCheckState(Qt.Unchecked)

    # ============ 下载 ============
    def on_download_selected(self):
        items = []
        for i in range(self.list_resources.count()):
            li = self.list_resources.item(i)
            if li.checkState() == Qt.Checked:
                items.append(li.data(Qt.UserRole))
        if not items:
            QMessageBox.warning(self, "提示", "请勾选要下载的资源")
            return
        self._start_download(items)

    def on_download_all(self):
        if not self.current_resources:
            QMessageBox.warning(self, "提示", "请先检测资源")
            return
        self._start_download(self.current_resources[:])

    def _start_download(self, items):
        pid = self.current_pet_id
        if not pid:
            QMessageBox.warning(self, "提示", "请先选择宠物")
            return
        self.log_msg(f"开始下载 {len(items)} 个资源...")
        self.progress.setValue(0)
        self.thread_download = DownloadThread(
            self.api, pid, self.download_dir, items
        )
        self.thread_download.progress_signal.connect(self.on_download_progress)
        self.thread_download.files_signal.connect(self.on_download_files)
        self.thread_download.finished_signal.connect(self.on_download_done)
        self.thread_download.start()

    def on_download_progress(self, pct, msg):
        self.progress.setValue(pct)
        self.statusBar().showMessage(msg)
        if pct > 0:
            self.log_msg(msg)

    def on_download_files(self, files):
        self.current_saved_files = files

    def on_download_done(self, ok, msg):
        self.log_msg(f"下载{'成功' if ok else '失败'}: {msg}")
        if ok:
            # 显示第一张PNG预览
            for f in self.current_saved_files:
                if f.lower().endswith(".png"):
                    pix = QPixmap(f)
                    if not pix.isNull():
                        scaled = pix.scaled(
                            self.label_preview.size(),
                            Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        self.label_preview.setPixmap(scaled)
                    break
            self.statusBar().showMessage("下载完成")
        else:
            QMessageBox.warning(self, "下载失败", msg)
        self.progress.setValue(0)

    # ============ 壁纸参数 ============
    def on_pick_color(self):
        color = QColorDialog.getColor(QColor(self.input_bg_color.text()))
        if color.isValid():
            self.input_bg_color.setText(color.name())
            self.update_bg_preview()

    def on_pick_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)")
        if path:
            self.input_bg_image.setText(path)
            self.update_bg_preview()

    def on_bg_mode_change(self, index):
        """背景模式切换时更新预览"""
        # 自定义图片模式显示图片选择行
        self.img_row_widget.setVisible(index == 4)
        self.update_bg_preview()

    def update_bg_preview(self):
        """更新背景预览标签"""
        mode = self.cbo_bg_mode.currentIndex()
        if mode == 4:
            # 自定义图片模式
            img_path = self.input_bg_image.text().strip()
            if img_path and os.path.isfile(img_path):
                pix = QPixmap(img_path)
                if not pix.isNull():
                    scaled = pix.scaled(self.lbl_bg_preview.size(),
                                        Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self.lbl_bg_preview.setPixmap(scaled)
                    return
            self.lbl_bg_preview.setText("  请选择背景图片  ")
            self.lbl_bg_preview.setStyleSheet(
                "border: 1px solid #3a5a7a;"
                "border-radius: 7px; min-height: 40px;"
                "color: #cccccc;")
            return
        self.lbl_bg_preview.clear()
        css = self._compute_background_css(self.input_bg_color.text().strip(), mode)
        self.lbl_bg_preview.setStyleSheet(
            "border: 1px solid #3a5a7a;"
            "border-radius: 7px; min-height: 40px; " + css
        )

    def _extract_palette_from_png(self, png_path, num_colors=4):
        """从PNG图片提取主色调"""
        try:
            from PIL import Image
            img = Image.open(png_path).convert('RGBA')
            pixels = []
            w, h = img.size
            step = max(1, (w * h) // 50000)
            for y in range(0, h, step):
                for x in range(0, w, step):
                    r, g, b, a = img.getpixel((x, y))
                    if a > 30:
                        pixels.append((r, g, b))
            if len(pixels) < 10:
                return None

            # 简单量化分桶: 将 RGB 各分成 8 个区间
            buckets = {}
            for r, g, b in pixels:
                key = (r >> 5, g >> 5, b >> 5)
                buckets[key] = buckets.get(key, 0) + 1

            # 取频率最高的颜色
            sorted_colors = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
            palette = []
            for key, _ in sorted_colors[:num_colors]:
                r = (key[0] << 5) | 16
                g = (key[1] << 5) | 16
                b = (key[2] << 5) | 16
                # 饱和度校正: 如果颜色灰暗,增加饱和度
                h_val, s_val, v_val = self._rgb_to_hsv(r, g, b)
                if s_val < 0.3:
                    s_val = 0.5
                if v_val > 0.9:
                    v_val = 0.75
                r, g, b = self._hsv_to_rgb(h_val, s_val, v_val)
                palette.append('#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b)))
            return palette
        except Exception:
            return None

    def _rgb_to_hsv(self, r, g, b):
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        h = s = 0
        v = mx
        d = mx - mn
        if d != 0:
            s = d / mx if mx != 0 else 0
            if mx == r:
                h = ((g - b) / d + (6 if g < b else 0)) / 6
            elif mx == g:
                h = ((b - r) / d + 2) / 6
            else:
                h = ((r - g) / d + 4) / 6
        return h, s, v

    def _hsv_to_rgb(self, h, s, v):
        if s == 0:
            return v * 255, v * 255, v * 255
        h = h * 6
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f) if i % 2 == 0 else v * (1 - s * (1 - f))
        t = v * (1 - s * (1 - f)) if i % 2 == 0 else v * (1 - s * f)
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        return r * 255, g * 255, b * 255

    def _compute_background_css(self, bg_color, mode, png_path=None):
        """根据模式计算CSS背景样式"""
        if mode == 0:  # 纯色
            return f"background: {bg_color};"
        elif mode == 1:  # 莫奈渐变
            palette = self._extract_palette_from_png(png_path) if png_path else None
            if not palette:
                palette = self._monet_palette_from_color(bg_color)
            return self._make_gradient_css(palette, "monet")
        elif mode == 2:  # 油画质感
            palette = self._extract_palette_from_png(png_path) if png_path else None
            if not palette:
                palette = self._oil_palette_from_color(bg_color)
            return self._make_gradient_css(palette, "oil")
        elif mode == 3:  # 自动取色
            palette = self._extract_palette_from_png(png_path) if png_path else None
            if not palette:
                palette = self._monet_palette_from_color(bg_color)
            return self._make_gradient_css(palette, "auto")
        return f"background: {bg_color};"

    def _monet_palette_from_color(self, color_str):
        """从单色生成莫奈风格调色板"""
        c = QColor(color_str)
        h = c.hue() / 360.0
        s = c.saturation() / 255.0
        v = c.value() / 255.0
        if s < 0.1:
            s = 0.4
        if v < 0.15:
            v = 0.5
        if h < 0:
            h = 0.5
        return [
            self._hsv_to_hex(h, max(0.1, s * 0.6), min(0.95, v * 1.1)),
            self._hsv_to_hex((h + 0.08) % 1, max(0.2, s * 0.8), min(1.0, v * 1.2)),
            self._hsv_to_hex((h + 0.15) % 1, max(0.15, s * 0.9), min(0.9, v * 0.95)),
            self._hsv_to_hex((h + 0.45) % 1, max(0.1, s * 0.4), min(0.85, v * 0.85)),
        ]

    def _oil_palette_from_color(self, color_str):
        """从单色生成油画质感调色板"""
        c = QColor(color_str)
        h = c.hue() / 360.0
        s = c.saturation() / 255.0
        v = c.value() / 255.0
        if s < 0.15:
            s = 0.5
        if v < 0.15:
            v = 0.5
        if h < 0:
            h = 0.5
        return [
            self._hsv_to_hex(h, s, min(0.9, v * 0.85)),
            self._hsv_to_hex((h + 0.03) % 1, min(1, s * 1.15), min(0.95, v * 1.05)),
            self._hsv_to_hex((h + 0.12) % 1, max(0.3, s * 0.7), min(1.0, v * 1.15)),
            self._hsv_to_hex((h + 0.28) % 1, max(0.25, s * 0.5), min(0.8, v * 0.75)),
        ]

    def _hsv_to_hex(self, h, s, v):
        r, g, b = self._hsv_to_rgb(h, s, v)
        return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))

    def _make_gradient_css(self, colors, style="monet"):
        """生成CSS渐变样式"""
        if len(colors) < 2:
            return f"background: {colors[0] if colors else '#000000'};"
        if style == "monet":
            # 莫奈: 柔和流动渐变
            angle = 135
            stops = ", ".join(
                f"{c} {100 * i / (len(colors) - 1):.0f}%"
                for i, c in enumerate(colors)
            )
            return (
                f"background: linear-gradient({angle}deg, {stops});"
            )
        elif style == "oil":
            # 油画: 高对比多方向渐变
            c1, c2, c3 = colors[:3]
            return (
                f"background: "
                f"radial-gradient(ellipse at 20% 30%, {c2}88 0%, transparent 50%), "
                f"radial-gradient(ellipse at 80% 70%, {c3}99 0%, transparent 55%), "
                f"linear-gradient(160deg, {c1} 0%, {c2} 60%, {c3} 100%);"
            )
        else:  # auto
            angle = 120
            stops = ", ".join(
                f"{c} {100 * i / (len(colors) - 1):.0f}%"
                for i, c in enumerate(colors)
            )
            return f"background: linear-gradient({angle}deg, {stops});"

    def get_wallpaper_settings(self):
        mode = self.cbo_bg_mode.currentIndex()
        bg_color = self.input_bg_color.text().strip() or "#000000"
        bg_image = self.input_bg_image.text().strip() if mode == 4 else ""
        return {
            "bg_color": bg_color,
            "bg_mode": mode,
            "bg_image": bg_image,
            "bg_css": self._compute_background_css(bg_color, mode),
            "scale": self.spin_scale.value(),
            "offset_x": self.spin_offset_x.value(),
            "offset_y": self.spin_offset_y.value(),
            "resource_type": "spine_breath" if self.btn_use_breath.isChecked() else "spine_fight",
        }

    # ============ 本地HTTP预览服务器 ============
    _preview_server = None

    def _start_preview_server(self, directory, handler_class=None):
        """启动本地HTTP服务器(用于预览,绕过file://纹理限制)"""
        # 停止旧服务器
        if self._preview_server:
            try:
                self._preview_server.shutdown()
                self._preview_server.server_close()
            except Exception:
                pass
            self._preview_server = None
            # 等待端口释放
            import time
            time.sleep(0.2)

        # 找空闲端口（固定范围，避免每次端口耗尽）
        import socket
        port = None
        for try_port in range(11900, 12000):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", try_port))
                port = try_port
                sock.close()
                break
            except OSError:
                sock.close()
                continue
        if port is None:
            # 找不到空闲端口，用系统随机分配
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            sock.close()

        # 创建服务器（使用 ThreadingHTTPServer 支持并发请求，
        # 否则浏览器同时请求 HTML+JS+贴图时会阻塞，导致"未发送任何数据"）
        if handler_class is None:
            # 用显式子类替代 lambda，避免 PyInstaller 打包后 handler 初始化异常
            class _PreviewHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=directory, **kwargs)
                def log_message(self, format, *args):
                    pass  # 静默日志
            handler = _PreviewHandler
        else:
            class _CustomHandler(handler_class):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=directory, **kwargs)
            handler = _CustomHandler
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            server.daemon_threads = True
            server.allow_reuse_address = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._preview_server = server
            self.log_msg(f"HTTP服务器已启动: 127.0.0.1:{port} (目录: {os.path.basename(directory)})")
            return port
        except Exception as e:
            self.log_msg(f"启动HTTP服务器失败: {e}")
            raise

    # ============ 预览动态立绘 ============
    def on_preview_spine(self):
        pid = self.current_pet_id or self.get_current_pet_id()
        if not pid:
            QMessageBox.warning(self, "提示", "请先选择宠物")
            return
        self.current_pet_id = pid

        settings = self.get_wallpaper_settings()
        resource_type = settings["resource_type"]

        # 预览目录(临时)
        preview_dir = os.path.join(self.download_dir, "preview", pid)
        os.makedirs(preview_dir, exist_ok=True)

        self.log_msg(f"准备预览资源(类型: {resource_type})...")
        self.progress.setValue(10)
        success, files = self.api.download_spine_resources(pid, preview_dir, resource_type)
        if not success:
            self.progress.setValue(0)
            QMessageBox.warning(self, "预览失败",
                "Spine资源下载失败,可能此宠物没有动态立绘\n"
                "可尝试勾选「使用newbreath资源」再试")
            return

        self.progress.setValue(60)
        skel_file = files["skeleton"]
        atlas_file = files["atlas"]
        png_file = files["texture"]
        skel_type = "json" if skel_file.lower().endswith(".json") else "binary"

        # 复制 runtime
        src_runtime = os.path.join(BASE_DIR, "web", "spine-webgl.js")
        if os.path.exists(src_runtime):
            shutil.copy(src_runtime, os.path.join(preview_dir, "spine-webgl.js"))

        # 生成预览HTML
        tpl_path = os.path.join(BASE_DIR, "web", "wallpaper_template.html")
        with open(tpl_path, "r", encoding="utf-8") as f:
            tpl = f.read()

        # 预览时可用真实 PNG 提取颜色
        bg_mode = settings.get("bg_mode", 0)
        bg_color = settings.get("bg_color", "#000000")
        bg_image = settings.get("bg_image", "")
        if bg_mode == 4:
            # 自定义图片模式: 复制背景图到预览目录
            if bg_image and os.path.isfile(bg_image):
                shutil.copy(bg_image, os.path.join(preview_dir, os.path.basename(bg_image)))
            bg_css = WallpaperThread._compute_bg_css(bg_color, bg_mode, None, bg_image)
        elif bg_mode > 0 and png_file and os.path.exists(png_file):
            bg_css = WallpaperThread._compute_bg_css(bg_color, bg_mode, png_file)
        else:
            bg_css = settings.get("bg_css", f"background: {bg_color};")

        html = tpl.replace("{{SKEL_FILE}}", os.path.basename(skel_file)) \
                  .replace("{{ATLAS_FILE}}", os.path.basename(atlas_file)) \
                  .replace("{{TEXTURE_FILE}}", os.path.basename(png_file)) \
                  .replace("{{SKEL_TYPE}}", skel_type) \
                  .replace("{{BG_CSS}}", bg_css) \
                  .replace("{{BG_COLOR}}", bg_color) \
                  .replace("{{CAMERA_SCALE}}", str(settings["scale"])) \
                  .replace("{{CAMERA_OFFSET_X}}", str(settings["offset_x"])) \
                  .replace("{{CAMERA_OFFSET_Y}}", str(settings["offset_y"]))

        preview_html = os.path.join(preview_dir, "preview.html")
        with open(preview_html, "w", encoding="utf-8") as f:
            f.write(html)

        self.progress.setValue(100)
        self.log_msg(f"预览已生成: {preview_html}")

        # 用本地HTTP服务器(绕过file://纹理加载限制)
        port = self._start_preview_server(preview_dir)
        url = f"http://127.0.0.1:{port}/preview.html"
        self.log_msg(f"预览服务器: {url}")
        self.statusBar().showMessage("软件内预览中")

        # 在软件内嵌窗口中预览(用 Edge --app 模式,无边框独立窗口)
        self._open_inapp_preview(url)
        self.progress.setValue(0)

    def _open_inapp_preview(self, url):
        """用 Edge/Chrome 的 --app 模式打开软件内嵌预览窗口"""
        import subprocess

        # 候选浏览器列表(优先 Edge,因为 Win10/11 自带)
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

        exe = None
        for path in candidates:
            if os.path.exists(path):
                exe = path
                break

        if exe:
            # --app 模式: 无地址栏的独立窗口,看起来像软件内嵌
            args = [
                "--app=" + url,
                "--window-size=800,600",
                "--no-default-browser-check",
                "--no-first-run",
            ]
            try:
                subprocess.Popen([exe] + args)
                self.log_msg("已在软件内嵌窗口打开预览")
                return
            except Exception as e:
                self.log_msg(f"启动浏览器窗口失败: {e}")

        # 回退: 用默认浏览器
        self.log_msg("未找到 Edge/Chrome,用默认浏览器打开")
        webbrowser.open(url)

    # ============ 导出GIF ============
    def on_export_gif(self):
        """导出GIF动画"""
        pid = self.current_pet_id or self.get_current_pet_id()
        if not pid:
            QMessageBox.warning(self, "提示", "请先选择宠物")
            return
        self.current_pet_id = pid

        settings = self.get_wallpaper_settings()
        resource_type = settings["resource_type"]

        # 预览目录(临时)
        preview_dir = os.path.join(self.download_dir, "gif", pid)
        os.makedirs(preview_dir, exist_ok=True)

        self.log_msg(f"准备GIF导出(类型: {resource_type})...")
        self.progress.setValue(10)
        success, files = self.api.download_spine_resources(pid, preview_dir, resource_type)
        if not success:
            self.progress.setValue(0)
            QMessageBox.warning(self, "导出失败",
                "Spine资源下载失败,可能此宠物没有动态立绘\n"
                "可尝试勾选「使用newbreath资源」再试")
            return

        self.progress.setValue(60)
        skel_file = files["skeleton"]
        atlas_file = files["atlas"]
        png_file = files["texture"]
        skel_type = "json" if skel_file.lower().endswith(".json") else "binary"

        # 复制 runtime
        src_runtime = os.path.join(BASE_DIR, "web", "spine-webgl.js")
        if os.path.exists(src_runtime):
            shutil.copy(src_runtime, os.path.join(preview_dir, "spine-webgl.js"))

        # 生成 GIF 录制 HTML
        tpl_path = os.path.join(BASE_DIR, "web", "gif_template.html")
        with open(tpl_path, "r", encoding="utf-8") as f:
            tpl = f.read()

        # 获取背景色
        bg_color = settings.get("bg_color", "#2a2b33")
        
        # 根据立绘尺寸计算合适的GIF尺寸
        gif_width = 600
        gif_height = 600
        try:
            if os.path.exists(png_file):
                from PIL import Image
                img = Image.open(png_file)
                w, h = img.size
                # 保持宽高比,限制最大边为600
                if w >= h:
                    gif_width = 600
                    gif_height = int(600 * h / w)
                else:
                    gif_height = 600
                    gif_width = int(600 * w / h)
        except Exception:
            pass

        html = tpl.replace("{{SKEL_FILE}}", os.path.basename(skel_file)) \
                  .replace("{{ATLAS_FILE}}", os.path.basename(atlas_file)) \
                  .replace("{{TEXTURE_FILE}}", os.path.basename(png_file)) \
                  .replace("{{SKEL_TYPE}}", skel_type) \
                  .replace("{{BG_COLOR}}", bg_color) \
                  .replace("{{CAMERA_SCALE}}", str(settings["scale"])) \
                  .replace("{{CAMERA_OFFSET_X}}", str(settings["offset_x"])) \
                  .replace("{{CAMERA_OFFSET_Y}}", str(settings["offset_y"])) \
                  .replace("{{GIF_WIDTH}}", str(gif_width)) \
                  .replace("{{GIF_HEIGHT}}", str(gif_height))

        gif_html = os.path.join(preview_dir, "gif_recorder.html")
        with open(gif_html, "w", encoding="utf-8") as f:
            f.write(html)

        self.progress.setValue(100)
        self.log_msg(f"GIF录制页已生成: {gif_html}")

        # 设置GIF录制服务器参数
        gif_output_dir = os.path.join(self.download_dir, "gif_output")
        os.makedirs(gif_output_dir, exist_ok=True)
        gif_filename = f"aola_{pid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gif"
        gif_output_path = os.path.join(gif_output_dir, gif_filename)

        GifRecorderHandler.gif_output_path = gif_output_path
        GifRecorderHandler.gif_session_id = str(uuid.uuid4())
        GifRecorderHandler.frame_store.clear()

        # 用自定义HTTP服务器启动(支持帧上传和GIF生成)
        port = self._start_preview_server(preview_dir, handler_class=GifRecorderHandler)
        url = f"http://127.0.0.1:{port}/gif_recorder.html"
        self.log_msg(f"GIF录制服务器: {url}")
        self.log_msg(f"GIF输出路径: {gif_output_path}")

        self._gif_output_path = gif_output_path

        QMessageBox.information(self, "GIF录制",
            f"GIF录制页面已打开!\n\n"
            f"在打开的页面中:\n"
            f"1. 设置尺寸/时长/FPS\n"
            f"2. 点击「🎬 开始录制GIF」按钮\n"
            f"3. 等待生成完成\n"
            f"4. 点击「下载GIF」保存文件\n\n"
            f"文件也会自动保存到:\n{gif_output_dir}")

        webbrowser.open(url)
        self.progress.setValue(0)

        # 定时检查GIF是否生成完成
        self._gif_check_timer = QTimer()
        self._gif_check_timer.timeout.connect(self._check_gif_result)
        self._gif_check_timer.start(2000)

    def _check_gif_result(self):
        """检查GIF是否生成完成"""
        gif_path = getattr(self, '_gif_output_path', None)
        if gif_path and os.path.exists(gif_path):
            size = os.path.getsize(gif_path)
            if size > 100:
                self._gif_check_timer.stop()
                self.log_msg(f"GIF生成完成: {gif_path} ({size}字节)")
                self.statusBar().showMessage("GIF生成完成")
                if sys.platform == "win32":
                    os.startfile(os.path.dirname(gif_path))

    # ============ 导出壁纸项目 ============
    def on_export_wallpaper(self):
        pid = self.current_pet_id or self.get_current_pet_id()
        if not pid:
            QMessageBox.warning(self, "提示", "请先选择宠物")
            return
        self.current_pet_id = pid
        name = self.current_pet_name or self.api.get_pet_name(pid) or pid

        settings = self.get_wallpaper_settings()
        out_dir = os.path.join(self.wallpapers_dir, f"aola_pet_{pid}")
        os.makedirs(out_dir, exist_ok=True)

        self.log_msg(f"开始生成壁纸项目: {out_dir}")
        self.progress.setValue(0)
        self.thread_wp = WallpaperThread(
            self.api, pid, name, out_dir, settings
        )
        self.thread_wp.progress_signal.connect(self.on_wp_progress)
        self.thread_wp.finished_signal.connect(self.on_wp_done)
        self.thread_wp.start()

    def on_wp_progress(self, pct, msg):
        self.progress.setValue(pct)
        self.statusBar().showMessage(msg)
        self.log_msg(msg)

    def on_wp_done(self, ok, msg, out_dir):
        self.progress.setValue(100 if ok else 0)
        self.log_msg(f"壁纸{'成功' if ok else '失败'}: {msg}")
        if ok:
            if sys.platform == "win32":
                os.startfile(out_dir)
            else:
                webbrowser.open("file:///" + out_dir)
            QMessageBox.information(self, "壁纸生成成功",
                f"壁纸项目已生成到:\n{out_dir}\n\n"
                f"导入 Wallpaper Engine 方法:\n"
                f"1. 打开 Wallpaper Engine\n"
                f"2. 点击「打开壁纸编辑器」\n"
                f"3. 选择「网页壁纸」\n"
                f"4. 文件 → 打开 → 选择 {out_dir} 目录\n"
                f"   或直接把目录拖入 Wallpaper Engine")
        else:
            QMessageBox.warning(self, "壁纸生成失败", msg)
        self.progress.setValue(0)

    # ============ 打开目录 ============
    def open_download_dir(self):
        """打开下载保存目录"""
        d = self.download_dir
        os.makedirs(d, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(d)
        else:
            webbrowser.open("file:///" + d)


def main():
    # 禁用 SSL 警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()