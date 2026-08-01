# -*- coding: utf-8 -*-
"""URL配置管理 - 读取 config.ini, 管理资源URL模板"""

import os
import configparser


class UrlConfig:
    """读取并管理 config.ini 中的 URL 模板"""

    def __init__(self, config_path=None):
        if config_path is None:
            # 默认与 main.py 同目录下的 config.ini
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config.ini")
        self.config_path = config_path
        self.cfg = configparser.ConfigParser()
        # 保持键名小写敏感(允许大写URL)
        self.cfg.optionxform = str
        self.cfg.read(config_path, encoding="utf-8")

    # ---------- 网络相关 ----------
    @property
    def referer(self):
        return self.cfg.get("network", "referer", fallback="https://aola.100bt.com/h5/")

    @property
    def timeout(self):
        return self.cfg.getint("network", "timeout", fallback=15)

    @property
    def interval(self):
        return self.cfg.getfloat("network", "interval", fallback=0.3)

    # ---------- 静态立绘 ----------
    @property
    def static_templates(self):
        """返回所有静态立绘URL模板列表(按优先级)"""
        templates = []
        for key in ("url_template", "url_template_alt1", "url_template_alt2"):
            if self.cfg.has_option("static", key):
                val = self.cfg.get("static", key).strip()
                if val:
                    templates.append(val)
        return templates

    # ---------- Spine 动态 ----------
    @property
    def skeleton_template(self):
        return self.cfg.get("spine", "skeleton_url_template", fallback="").strip()

    @property
    def skeleton_json_template(self):
        return self.cfg.get("spine", "skeleton_json_url_template", fallback="").strip()

    @property
    def atlas_template(self):
        return self.cfg.get("spine", "atlas_url_template", fallback="").strip()

    @property
    def texture_template(self):
        return self.cfg.get("spine", "texture_url_template", fallback="").strip()

    # ---------- 输出目录 ----------
    @property
    def download_dir(self):
        d = self.cfg.get("output", "download_dir", fallback="./assets")
        return self._abs(d)

    @property
    def wallpaper_dir(self):
        d = self.cfg.get("output", "wallpaper_dir", fallback="./wallpapers")
        return self._abs(d)

    def _abs(self, path):
        if os.path.isabs(path):
            return path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.normpath(os.path.join(base_dir, path))

    # ---------- 工具 ----------
    @staticmethod
    def fill(template, pet_id):
        """把模板里的 {id} 替换为 pet_id"""
        return template.replace("{id}", str(pet_id))

    def ensure_dirs(self):
        """确保输出目录存在"""
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.wallpaper_dir, exist_ok=True)
