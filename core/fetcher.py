# -*- coding: utf-8 -*-
"""资源下载器 - 根据宠物ID下载静态立绘和Spine动态资源"""

import os
import time
import requests

from .url_config import UrlConfig


class FetchResult:
    """单次下载结果"""

    def __init__(self, success=False, kind=None, files=None, msg=""):
        self.success = success      # 是否成功
        self.kind = kind            # "static" / "spine"
        self.files = files or []    # 已保存的文件路径列表
        self.msg = msg              # 说明信息

    def __repr__(self):
        return f"<FetchResult success={self.success} kind={self.kind} files={len(self.files)}>"


class Fetcher:
    """资源下载器"""

    def __init__(self, config=None):
        self.cfg = config or UrlConfig()
        self.session = requests.Session()
        # 禁用系统代理(避免SSL代理错误),禁用SSL验证
        self.session.trust_env = False
        self.session.proxies = {}
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": self.cfg.referer,
        })

    # ---------- 底层请求 ----------
    def _get(self, url):
        """发起GET请求,返回Response或None"""
        try:
            resp = self.session.get(url, timeout=self.cfg.timeout, verify=False)
            if resp.status_code == 200 and len(resp.content) > 0:
                return resp
            return None
        except requests.RequestException:
            return None

    def _save(self, resp, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(resp.content)

    def _sleep(self):
        time.sleep(self.cfg.interval)

    # ---------- 静态立绘 ----------
    def fetch_static(self, pet_id, progress_cb=None):
        """下载静态立绘PNG,下载所有有效帧(小图标+大立绘)

        progress_cb(msg) 用于回传进度信息
        """
        if progress_cb:
            progress_cb(f"开始下载静态立绘: ID={pet_id}")

        save_dir = os.path.join(self.cfg.download_dir, "static", str(pet_id))
        saved = []
        labels = {0: "小图标", 1: "大立绘"}

        for i, template in enumerate(self.cfg.static_templates):
            if not template:
                continue
            url = UrlConfig.fill(template, pet_id)
            label = labels.get(i, f"帧{i}")
            if progress_cb:
                progress_cb(f"下载{label}: {url}")

            resp = self._get(url)
            self._sleep()
            if resp is None:
                continue

            # 简单校验是否为图片
            head = resp.content[:8]
            if not (head.startswith(b"\x89PNG") or head.startswith(b"\xff\xd8\xff")
                    or head.startswith(b"RIFF")):
                continue

            filepath = os.path.join(save_dir, f"{pet_id}_{i}.png")
            self._save(resp, filepath)
            saved.append(filepath)

            if progress_cb:
                progress_cb(f"已保存{label}: {filepath} ({len(resp.content)//1024}KB)")

        if saved:
            return FetchResult(
                success=True, kind="static", files=saved,
                msg=f"静态立绘下载成功({len(saved)}张)"
            )

        if progress_cb:
            progress_cb("所有静态URL均失败")
        return FetchResult(success=False, msg="静态立绘下载失败: 所有URL均不可用")

    # ---------- Spine 动态 ----------
    def fetch_spine(self, pet_id, progress_cb=None):
        """下载Spine动态立绘(.sk/.json + .atlas + .png)

        会自动判断用 .sk 还是 .json
        """
        if progress_cb:
            progress_cb(f"开始下载Spine动态立绘: ID={pet_id}")

        save_dir = os.path.join(self.cfg.download_dir, "spine", str(pet_id))
        saved = []

        # 1. 骨骼数据: 先试 .sk, 再试 .json
        skeleton_file = None
        skeleton_is_json = False

        if self.cfg.skeleton_template:
            url = UrlConfig.fill(self.cfg.skeleton_template, pet_id)
            if progress_cb:
                progress_cb(f"尝试骨骼数据(.sk): {url}")
            resp = self._get(url)
            self._sleep()
            if resp is not None:
                skeleton_file = os.path.join(save_dir, f"{pet_id}.sk")
                self._save(resp, skeleton_file)
                saved.append(skeleton_file)
                if progress_cb:
                    progress_cb(f"已保存: {skeleton_file}")

        if skeleton_file is None and self.cfg.skeleton_json_template:
            url = UrlConfig.fill(self.cfg.skeleton_json_template, pet_id)
            if progress_cb:
                progress_cb(f"尝试骨骼数据(.json): {url}")
            resp = self._get(url)
            self._sleep()
            if resp is not None and self._looks_like_json(resp.content):
                skeleton_is_json = True
                skeleton_file = os.path.join(save_dir, f"{pet_id}.json")
                self._save(resp, skeleton_file)
                saved.append(skeleton_file)
                if progress_cb:
                    progress_cb(f"已保存: {skeleton_file}")

        if skeleton_file is None:
            if progress_cb:
                progress_cb("骨骼数据下载失败")
            return FetchResult(success=False, msg="Spine骨骼数据(.sk/.json)下载失败")

        # 2. atlas
        atlas_file = None
        if self.cfg.atlas_template:
            url = UrlConfig.fill(self.cfg.atlas_template, pet_id)
            if progress_cb:
                progress_cb(f"下载图集描述: {url}")
            resp = self._get(url)
            self._sleep()
            if resp is not None:
                atlas_file = os.path.join(save_dir, f"{pet_id}.atlas")
                self._save(resp, atlas_file)
                saved.append(atlas_file)
                if progress_cb:
                    progress_cb(f"已保存: {atlas_file}")

        if atlas_file is None:
            if progress_cb:
                progress_cb("atlas下载失败")
            return FetchResult(success=False, msg="Spine atlas文件下载失败")

        # 3. 图集图片 .png
        texture_file = None
        if self.cfg.texture_template:
            url = UrlConfig.fill(self.cfg.texture_template, pet_id)
            if progress_cb:
                progress_cb(f"下载图集图片: {url}")
            resp = self._get(url)
            self._sleep()
            if resp is not None and resp.content[:4] == b"\x89PNG":
                texture_file = os.path.join(save_dir, f"{pet_id}.png")
                self._save(resp, texture_file)
                saved.append(texture_file)
                if progress_cb:
                    progress_cb(f"已保存: {texture_file}")

        if texture_file is None:
            if progress_cb:
                progress_cb("图集图片下载失败")
            return FetchResult(success=False, msg="Spine图集图片下载失败")

        return FetchResult(
            success=True, kind="spine", files=saved,
            msg=f"Spine资源下载成功({'JSON' if skeleton_is_json else 'SK'}格式)"
        )

    # ---------- 一键下载 ----------
    def fetch_all(self, pet_id, progress_cb=None):
        """同时尝试静态和动态,返回结果列表"""
        results = []
        results.append(self.fetch_static(pet_id, progress_cb))
        results.append(self.fetch_spine(pet_id, progress_cb))
        return results

    # ---------- 辅助 ----------
    @staticmethod
    def _looks_like_json(data):
        """粗略判断是否是JSON文本"""
        if not data:
            return False
        s = data[:64].lstrip()
        return s.startswith(b"{") or s.startswith(b"[")

    def get_spine_resource_dir(self, pet_id):
        """获取某个宠物的Spine资源目录(用于导出壁纸)"""
        return os.path.join(self.cfg.download_dir, "spine", str(pet_id))
