# -*- coding: utf-8 -*-
"""Spine网页壁纸生成器 - 把下载的Spine资源打包成可导入Wallpaper Engine的网页壁纸"""

import os
import shutil

from .url_config import UrlConfig


class SpineExporter:
    """将Spine资源导出为独立网页壁纸文件夹"""

    def __init__(self, config=None):
        self.cfg = config or UrlConfig()
        # HTML模板路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_path = os.path.join(base_dir, "web", "spine_viewer_template.html")

    def export(self, pet_id, skeleton_is_json=False, progress_cb=None):
        """导出网页壁纸

        Args:
            pet_id: 宠物ID
            skeleton_is_json: 骨骼文件是否为json格式(否则为.sk二进制)
            progress_cb: 进度回调

        Returns:
            (success, wallpaper_dir_or_msg)
        """
        src_dir = os.path.join(self.cfg.download_dir, "spine", str(pet_id))
        if not os.path.isdir(src_dir):
            return False, f"找不到Spine资源目录: {src_dir}"

        # 收集资源文件
        skeleton_file = None
        atlas_file = None
        texture_file = None

        for name in os.listdir(src_dir):
            lower = name.lower()
            full = os.path.join(src_dir, name)
            if lower.endswith(".sk") or lower.endswith(".json"):
                skeleton_file = full
            elif lower.endswith(".atlas"):
                atlas_file = full
            elif lower.endswith(".png"):
                texture_file = full

        if not (skeleton_file and atlas_file and texture_file):
            missing = []
            if not skeleton_file: missing.append("骨骼文件(.sk/.json)")
            if not atlas_file: missing.append("atlas文件")
            if not texture_file: missing.append("图集图片(.png)")
            return False, f"资源不完整,缺少: {', '.join(missing)}"

        # 判断骨骼格式
        skel_ext = ".json" if skeleton_file.lower().endswith(".json") else ".sk"

        # 创建壁纸输出目录
        out_dir = os.path.join(self.cfg.wallpaper_dir, f"pet_{pet_id}")
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)

        if progress_cb:
            progress_cb(f"输出目录: {out_dir}")

        # 复制资源(统一重命名,方便HTML引用)
        dst_skel = os.path.join(out_dir, f"skeleton{skel_ext}")
        dst_atlas = os.path.join(out_dir, "texture.atlas")
        dst_png = os.path.join(out_dir, "texture.png")

        shutil.copy2(skeleton_file, dst_skel)
        shutil.copy2(texture_file, dst_png)

        # atlas文件需要修改: 把原始png文件名替换为 texture.png
        with open(atlas_file, "r", encoding="utf-8") as f:
            atlas_content = f.read()
        # atlas第一行是png文件名(如 petmovie6015.png),替换为 texture.png
        original_png_name = os.path.basename(texture_file)
        atlas_content = atlas_content.replace(original_png_name, "texture.png")
        with open(dst_atlas, "w", encoding="utf-8") as f:
            f.write(atlas_content)

        if progress_cb:
            progress_cb("已复制资源文件")

        # 生成 index.html
        html = self._render_html(skel_ext)
        html_path = os.path.join(out_dir, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        if progress_cb:
            progress_cb(f"已生成: {html_path}")
            progress_cb("网页壁纸导出完成!")

        return True, out_dir

    def _render_html(self, skel_ext):
        """根据模板生成HTML"""
        with open(self.template_path, "r", encoding="utf-8") as f:
            tpl = f.read()

        skel_type = "json" if skel_ext == ".json" else "binary"
        return tpl.replace("{{SKEL_FILE}}", f"skeleton{skel_ext}") \
                  .replace("{{ATLAS_FILE}}", "texture.atlas") \
                  .replace("{{PNG_FILE}}", "texture.png") \
                  .replace("{{SKEL_TYPE}}", skel_type)
