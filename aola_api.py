# -*- coding: utf-8 -*-
"""奥拉星H5 API模块

功能:
- get_pet_name(pet_id)      根据ID查询宠物名称
- search_pets_by_name(name) 按名称搜索宠物
- get_pet_resources(pet_id) 查询某宠物所有可用资源
- download_resource(path, out_dir) 下载单个资源
"""

import os
import json
import requests

BASE_URL = "https://aola.100bt.com/h5/"

# 资源路径模板
PET_SPINE_PATH = "petfightassets/spine/pet{id}/pet{id}.{ext}"   # 战斗Spine立绘
PET_ICON_PATH = "peticon/newlarge/type1/peticon{id}/peticon{id}_{frame}.png"  # 静态立绘
PET_MOVIE_PATH = "peticon/newbreath/petmovie{id}/petmovie{id}.{ext}"  # newbreath动态立绘
PET_EGG_PATH = "petegg/egg{id}.png"  # 宠物蛋

# 宠物字典URL
PET_DICT_URL = BASE_URL + "data/petdictionarydata.json"
# 资源清单URL
VERSION_URL = BASE_URL + "version.json"


class AolaAPI:
    """奥拉星H5资源API"""

    def __init__(self):
        self.session = requests.Session()
        # 禁用系统代理(避免SSL代理错误)
        self.session.trust_env = False
        self.session.proxies = {}
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Referer": BASE_URL,
        })
        self._dict_cache = None       # 宠物字典缓存
        self._version_cache = None    # 版本清单缓存

    # ============ 宠物字典 ============
    def _load_dict(self):
        """加载宠物字典(带缓存)"""
        if self._dict_cache is not None:
            return self._dict_cache
        try:
            r = self.session.get(PET_DICT_URL, timeout=20, verify=False)
            if r.status_code == 200:
                data = r.json()
                # 字典格式: {"data": {"1": ["1","兔小子",...], "2": [...]}}
                self._dict_cache = data.get("data", data) if isinstance(data, dict) else data
                return self._dict_cache
        except Exception:
            pass
        self._dict_cache = {}
        return self._dict_cache

    def get_pet_name(self, pet_id):
        """根据ID查询宠物名称

        Returns:
            名称字符串,找不到返回None
        """
        d = self._load_dict()
        info = d.get(str(pet_id))
        if info and len(info) > 1:
            return info[1]  # 第2个元素是名称
        return None

    def get_pet_info(self, pet_id):
        """根据ID查询宠物完整信息

        Returns:
            dict含 name/属性/描述 等,找不到返回None
        """
        d = self._load_dict()
        info = d.get(str(pet_id))
        if not info:
            return None
        # 字段含义参考抓包: [id,名称,编号,星级,属性,系别,进化等级,...,描述,...]
        return {
            "id": info[0] if len(info) > 0 else "",
            "name": info[1] if len(info) > 1 else "",
            "number": info[2] if len(info) > 2 else "",
            "star": info[3] if len(info) > 3 else "",
            "elements": info[4] if len(info) > 4 else "",
            "types": info[5] if len(info) > 5 else "",
            "evolve_level": info[6] if len(info) > 6 else "",
            "description": info[10] if len(info) > 10 else "",
        }

    def search_pets_by_name(self, keyword):
        """按名称搜索宠物(模糊匹配)

        Args:
            keyword: 搜索关键词

        Returns:
            list of (id, name) 元组
        """
        d = self._load_dict()
        results = []
        for pid, info in d.items():
            if len(info) > 1:
                name = info[1]
                if keyword in name or keyword in str(pid):
                    results.append((pid, name))
        return results

    def get_all_pets(self):
        """获取所有宠物列表

        Returns:
            list of (id, name)
        """
        d = self._load_dict()
        return [(pid, info[1]) for pid, info in d.items() if len(info) > 1]

    # ============ 资源查询 ============
    def _load_version(self):
        """加载版本清单(带缓存)"""
        if self._version_cache is not None:
            return self._version_cache
        try:
            r = self.session.get(VERSION_URL, timeout=20, verify=False)
            if r.status_code == 200:
                self._version_cache = r.json()
                return self._version_cache
        except Exception:
            pass
        self._version_cache = {}
        return self._version_cache

    def get_pet_resources(self, pet_id):
        """查询某宠物所有可用资源

        检查静态立绘、newbreath动态立绘、宠物蛋是否存在

        Returns:
            list of dict: [{"type","path","ext","desc"}, ...]
        """
        resources = []
        pid = str(pet_id)

        # 1. 静态立绘 (peticon)
        for frame in [0, 1]:
            path = PET_ICON_PATH.format(id=pid, frame=frame)
            if self._check_resource(path):
                desc = "静态小图标" if frame == 0 else "静态大立绘"
                resources.append({
                    "type": "static",
                    "path": path,
                    "ext": "png",
                    "desc": desc,
                    "frame": frame
                })

        # 2. newbreath 动态立绘 (petmovie)
        for ext in ["json", "atlas", "png"]:
            path = PET_MOVIE_PATH.format(id=pid, ext=ext)
            if self._check_resource(path):
                resources.append({
                    "type": "spine_breath",
                    "path": path,
                    "ext": ext,
                    "desc": "newbreath动态立绘"
                })

        # 3. 宠物蛋 (petegg) — 部分宠物有
        path = PET_EGG_PATH.format(id=pid)
        if self._check_resource(path):
            resources.append({
                "type": "petegg",
                "path": path,
                "ext": "png",
                "desc": "宠物蛋"
            })

        return resources

    def _check_resource(self, path):
        """检查资源是否存在(HEAD请求)"""
        url = BASE_URL + path
        try:
            r = self.session.head(url, timeout=8, verify=False,
                                  allow_redirects=True)
            return r.status_code == 200
        except Exception:
            return False

    # ============ 下载 ============
    @staticmethod
    def make_session():
        """创建独立请求会话 (并发下载时各线程使用, 避免共享 Session 跨线程竞争)"""
        s = requests.Session()
        s.trust_env = False
        s.proxies = {}
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Referer": BASE_URL,
        })
        return s

    def download_resource(self, path, out_dir, filename=None, session=None):
        """下载单个资源到本地

        Args:
            path: 资源相对路径(如 petfightassets/spine/pet5943/pet5943.png)
            out_dir: 输出目录
            filename: 自定义文件名(默认用原文件名)
            session: 独立会话(并发下载时传入, 默认用自身 Session)

        Returns:
            保存的文件路径,失败返回None
        """
        url = BASE_URL + path
        try:
            r = (session or self.session).get(url, timeout=30, verify=False)
            if r.status_code == 200 and len(r.content) > 0:
                os.makedirs(out_dir, exist_ok=True)
                name = filename or os.path.basename(path)
                filepath = os.path.join(out_dir, name)
                with open(filepath, "wb") as f:
                    f.write(r.content)
                return filepath
        except Exception:
            pass
        return None

    def download_spine_resources(self, pet_id, out_dir, resource_type="spine_breath"):
        """下载某宠物的Spine三件套资源

        Args:
            pet_id: 宠物ID
            out_dir: 输出目录
            resource_type: "spine_breath" 目前只用 newbreath

        Returns:
            (success, files_dict) files_dict含 skeleton/atlas/texture 路径
        """
        pid = str(pet_id)
        files = {}

        if resource_type == "spine_breath":
            path_template = PET_MOVIE_PATH
            name_prefix = f"petmovie{pid}"
        else:
            path_template = PET_MOVIE_PATH
            name_prefix = f"petmovie{pid}"

        # 下载 .json (骨骼)
        path = path_template.format(id=pid, ext="json")
        f = self.download_resource(path, out_dir, f"{name_prefix}.json")
        if f:
            files["skeleton"] = f
        else:
            # 尝试 .sk
            path = path_template.format(id=pid, ext="sk")
            f = self.download_resource(path, out_dir, f"{name_prefix}.sk")
            if f:
                files["skeleton"] = f

        # 下载 .atlas
        path = path_template.format(id=pid, ext="atlas")
        f = self.download_resource(path, out_dir, f"{name_prefix}.atlas")
        if f:
            files["atlas"] = f

        # 下载 .png (主纹理)
        path = path_template.format(id=pid, ext="png")
        f = self.download_resource(path, out_dir, f"{name_prefix}.png")
        if f:
            files["texture"] = f

        # 下载 atlas 引用的附加纹理页 (多页 atlas, 如 petmovie60222.png)
        atlas_path = files.get("atlas")
        if atlas_path:
            main_name = f"{name_prefix}.png"
            base_rel = path_template.format(id=pid, ext="png")  # 主纹理相对路径
            dir_rel = base_rel.rsplit("/", 1)[0] + "/"
            try:
                with open(atlas_path, "r", encoding="utf-8") as af:
                    for line in af:
                        name = line.strip()
                        if name.endswith(".png") and name != main_name:
                            # 附加纹理 URL = 主纹理目录 + atlas 引用的文件名
                            extra = self.download_resource(dir_rel + name, out_dir, name)
                            if not extra:
                                print(f"[AolaAPI] 附加纹理下载失败: {dir_rel + name}")
            except Exception as e:
                print(f"[AolaAPI] 解析 atlas 附加纹理失败: {e}")

        success = "skeleton" in files and "atlas" in files and "texture" in files
        return success, files
