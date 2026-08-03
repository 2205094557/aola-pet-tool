"""
超分放大模块 — waifu2x-ncnn-vulkan (GPU 深度学习超分)
- 放大 Spine 图集纹理并同步更新 Atlas 坐标
- 独立 CLI 引擎: https://github.com/nihui/waifu2x-ncnn-vulkan
- 引擎存放: 软件目录 tools/waifu2x-ncnn-vulkan/<版本目录>/waifu2x-ncnn-vulkan.exe
"""

import os, re, subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==================== 算法列表 ====================

ALGORITHMS = {
    "waifu2x":  "Waifu2x (GPU)",
    "realcugan": "Real-CUGAN (GPU)",
    "realesr": "Real-ESRGAN (GPU)",
}

# ==================== waifu2x-ncnn-vulkan ====================

def find_w2x_exe() -> str:
    """定位 waifu2x-ncnn-vulkan.exe, 找不到返回空字符串"""
    base = os.path.join(BASE_DIR, "tools", "waifu2x-ncnn-vulkan")
    if not os.path.isdir(base):
        return ""
    for name in os.listdir(base):
        p = os.path.join(base, name, "waifu2x-ncnn-vulkan.exe")
        if os.path.isfile(p):
            return p
    return ""


def upscale_waifu2x(png_path: str, scale: int = 2,
                    denoise: int = 3, timeout: int = 600) -> str:
    """
    用 waifu2x-ncnn-vulkan 放大 PNG (GPU/Vulkan 加速)。

    scale:   1/2/4 倍
    denoise: 0~3 降噪级别 (3 最强降噪, 默认 3: 纹理压缩噪点/杂色最少)
    返回输出路径 (原文件名_2x.png / _4x.png)。失败抛出异常。
    """
    exe = find_w2x_exe()
    if not exe:
        raise FileNotFoundError(
            "未找到 waifu2x-ncnn-vulkan 引擎\n"
            "请将 waifu2x-ncnn-vulkan-windows 解压到软件目录 tools/waifu2x-ncnn-vulkan/ 下"
        )
    base, ext = os.path.splitext(png_path)
    out_path = f"{base}_{scale}x{ext}"
    cmd = [exe, "-i", png_path, "-o", out_path,
           "-s", str(scale), "-n", str(denoise), "-g", "0"]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0 or not os.path.isfile(out_path):
        err = result.stderr.decode("utf-8", errors="replace")[-800:] if result.stderr else ""
        raise RuntimeError(f"waifu2x 放大失败 (exit={result.returncode})\n{err}")
    return out_path


def upscale_image(png_path: str, scale: int, algorithm: str) -> str:
    """
    用指定算法放大 PNG，返回输出路径。
    algorithm: "waifu2x" | "realcugan" | "realesr"
    """
    if algorithm == "waifu2x":
        return upscale_waifu2x(png_path, scale=scale)
    if algorithm == "realcugan":
        return upscale_realcugan(png_path, scale=scale)
    if algorithm == "realesr":
        return upscale_realesr(png_path, scale=scale)
    raise ValueError(f"未知算法: {algorithm}，可选: {list(ALGORITHMS.keys())}")


# ==================== realcugan-ncnn-vulkan ====================

def find_realcugan_exe() -> str:
    """定位 realcugan-ncnn-vulkan.exe, 找不到返回空字符串"""
    base = os.path.join(BASE_DIR, "tools", "realcugan-ncnn-vulkan")
    if not os.path.isdir(base):
        return ""
    for name in os.listdir(base):
        p = os.path.join(base, name, "realcugan-ncnn-vulkan.exe")
        if os.path.isfile(p):
            return p
    return ""


def upscale_realcugan(png_path: str, scale: int = 4,
                      noise: int = -1, timeout: int = 600) -> str:
    """
    用 realcugan-ncnn-vulkan 放大 PNG (GPU/Vulkan 加速, 专为动漫优化)。

    scale: 2/3/4 倍
    noise: 降噪级别。-1 = conservative 无降噪 (默认, 最锐利, 适合清晰立绘);
           0~3 = 降噪级别 (数值越高越平滑模糊, 仅适合有噪点的老图)。
           注意: 引擎 -n 为降噪级别而非模型名, 模型目录用 -m 指定;
           使用 models-se (高保真变体, 含 up2x/up3x/up4x 全倍率档位),
           models-pro 目录仅有 2x 模型, 4x 会因缺 up4x 模型崩溃。
    返回输出路径 (原文件名_2x.png / _4x.png)。失败抛出异常。

    注意: 引擎对带透明通道图的 alpha 处理不可靠, 因此拆分处理:
    RGB 走 AI 放大, alpha 用 PIL 常规插值放大后合并 (避免边缘脏色/模糊)。
    """
    exe = find_realcugan_exe()
    if not exe:
        raise FileNotFoundError(
            "未找到 realcugan-ncnn-vulkan 引擎\n"
            "请将 realcugan-ncnn-vulkan-windows 解压到软件目录 tools/realcugan-ncnn-vulkan/ 下"
        )
    from PIL import Image

    base, ext = os.path.splitext(png_path)
    out_path = f"{base}_{scale}x{ext}"

    def _run_engine(in_path: str, out_path: str):
        cmd = [exe, "-i", in_path, "-o", out_path,
               "-m", "models-se", "-n", str(noise), "-s", str(scale), "-g", "0"]
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0 or not os.path.isfile(out_path):
            err = result.stderr.decode("utf-8", errors="replace")[-800:] if result.stderr else ""
            raise RuntimeError(f"realcugan 放大失败 (exit={result.returncode})\n{err}")

    with Image.open(png_path) as src:
        src.load()
        # 无透明通道的图 (RGB/L) 直接放大
        if src.mode in ("RGB", "L"):
            _run_engine(png_path, out_path)
            return out_path
        # 统一转 RGBA: 处理 RGBA / P(调色板带透明) / LA 等模式
        rgba = src.convert("RGBA")
        alpha = rgba.getchannel("A")
        rgb = rgba.convert("RGB")

    tmp_rgb = os.path.join(os.path.dirname(png_path), "_cugan_rgb_tmp.png")
    tmp_a = os.path.join(os.path.dirname(png_path), "_cugan_a_tmp.png")
    rgb.save(tmp_rgb)
    alpha.save(tmp_a)
    try:
        # AI 放大 RGB (不带 alpha, 避免透明区脏色污染)
        _run_engine(tmp_rgb, out_path)
        # alpha 用 PIL 常规插值放大 (alpha 只需平滑边缘, 无需 AI 超分)
        with Image.open(tmp_a) as im:
            new_a = im.resize((rgba.width * scale, rgba.height * scale), Image.LANCZOS)
        with Image.open(out_path) as im:
            new_rgb = im.convert("RGB")
        new_img = new_rgb.convert("RGBA")
        new_img.putalpha(new_a)
        new_img.save(out_path)
        return out_path
    finally:
        for p in (tmp_rgb, tmp_a):
            if os.path.exists(p):
                os.remove(p)


# ==================== upscayl-ncnn (Real-ESRGAN) ====================

def find_upscayl_exe() -> str:
    """
    定位 Real-ESRGAN 引擎 exe (原版 realesrgan-ncnn-vulkan), 找不到返回空字符串。
    注: upscayl-bin fork 因 RGB 通道错乱(红->绿/蓝->红)已弃用删除。
    """
    base = os.path.join(BASE_DIR, "tools", "realesrgan-ncnn-vulkan")
    if os.path.isdir(base):
        for name in os.listdir(base):
            p = os.path.join(base, name, "realesrgan-ncnn-vulkan.exe")
            if os.path.isfile(p):
                return p
    return ""


def upscale_realesr(png_path: str, scale: int = 2,
                    timeout: int = 600) -> str:
    """
    用 realesrgan-ncnn-vulkan (Real-ESRGAN) 放大 PNG (GPU/Vulkan)。

    scale: 2/3/4 倍 (2x/3x 用 animevideov3 轻量模型, 4x 用动漫立绘专用 x4plus-anime)
    返回输出路径 (原文件名_2x.png 等)。失败抛出异常。

    注意: 引擎对带透明通道图的 alpha 处理不可靠, 因此拆分处理:
    RGB 走 AI 放大, alpha 用 PIL 常规插值放大后合并。
    """
    from PIL import Image

    exe = find_upscayl_exe()
    if not exe:
        raise FileNotFoundError(
            "未找到 Real-ESRGAN 引擎\n"
            "请将 realesrgan-ncnn-vulkan-windows 解压到软件目录 tools/realesrgan-ncnn-vulkan/ 下"
        )
    # 模型按倍率选择: 2x 用轻量 animevideov3 (大图快), 4x 用动漫立绘专用 x4plus-anime (质量最佳)
    if scale == 2:
        model = "realesr-animevideov3-x2"
    elif scale == 3:
        model = "realesr-animevideov3-x3"
    elif scale == 4:
        model = "realesrgan-x4plus-anime"
    else:
        raise ValueError(f"Real-ESRGAN 仅支持 2x/3x/4x 放大, 收到: {scale}")
    base, ext = os.path.splitext(png_path)
    out_path = f"{base}_{scale}x{ext}"

    def _run_engine(in_path: str, out_path: str):
        # -j 2:2:2: 大图(放大后 4K+)推荐配置, 加速 decode/proc/save 三阶段
        cmd = [exe, "-i", in_path, "-o", out_path,
               "-n", model, "-s", str(scale), "-g", "0",
               "-j", "2:2:2"]
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode != 0 or not os.path.isfile(out_path):
            err = result.stderr.decode("utf-8", errors="replace")[-800:] if result.stderr else ""
            raise RuntimeError(f"Real-ESRGAN 放大失败 (exit={result.returncode})\n{err}")

    with Image.open(png_path) as src:
        src.load()
        # 无透明通道的图 (RGB/L) 直接放大
        if src.mode in ("RGB", "L"):
            _run_engine(png_path, out_path)
            return out_path
        # 统一转 RGBA: 处理 RGBA / P(调色板带透明) / LA 等模式
        rgba = src.convert("RGBA")
        alpha = rgba.getchannel("A")
        rgb = rgba.convert("RGB")

    tmp_rgb = os.path.join(os.path.dirname(png_path), "_esr_rgb_tmp.png")
    tmp_a = os.path.join(os.path.dirname(png_path), "_esr_a_tmp.png")
    rgb.save(tmp_rgb)
    alpha.save(tmp_a)
    try:
        # AI 放大 RGB (不带 alpha, 避免通道污染)
        _run_engine(tmp_rgb, out_path)
        # alpha 用 PIL 常规插值放大 (alpha 只需平滑边缘, 无需 AI 超分)
        with Image.open(tmp_a) as im:
            new_a = im.resize((rgba.width * scale, rgba.height * scale), Image.LANCZOS)
        with Image.open(out_path) as im:
            new_rgb = im.convert("RGB")
        new_img = new_rgb.convert("RGBA")
        new_img.putalpha(new_a)
        new_img.save(out_path)
        return out_path
    finally:
        for p in (tmp_rgb, tmp_a):
            if os.path.exists(p):
                os.remove(p)


# ==================== Atlas 坐标缩放 ====================

def _scale_int_pair(text: str, scale: float) -> str:
    parts = text.split(',')
    a = int(int(parts[0].strip()) * scale)
    b = int(int(parts[1].strip()) * scale)
    return f'{a},{b}'

def update_atlas_text(atlas_text: str, scale: float) -> str:
    """将 atlas 文本中所有坐标值和尺寸按 scale 缩放"""
    result = []
    for line in atlas_text.split('\n'):
        stripped = line.rstrip()
        # 匹配顶层 size (无缩进, 纹理尺寸) 与缩进坐标行 (子图 size/xy/orig/offset),
        # indent 组保留原缩进, 非坐标行 (rotate/index/filter 等) 原样保留
        m = re.match(r'^(\s*)(size|xy|orig|offset):\s*(\d+)\s*,\s*(\d+)\s*$', stripped)
        if m:
            indent, key, v1, v2 = m.groups()
            result.append(f'{indent}{key}: {_scale_int_pair(f"{v1},{v2}", scale)}')
        else:
            result.append(line)
    return '\n'.join(result)


# ==================== 一体化: 纹理 + Atlas 同步放大 ====================

def _atlas_texture_names(atlas_text: str) -> list:
    """提取 atlas 文本引用的所有纹理文件名 (页面行, 无缩进且以 .png 结尾)"""
    names = []
    for line in atlas_text.split('\n'):
        s = line.rstrip()
        if re.match(r'^[^\s:]+\.png$', s):
            names.append(s)
    return names


def upscale_spine_assets(png_path: str, atlas_path: str,
                         scale: int = 2,
                         algorithm: str = "waifu2x",
                         inplace: bool = True) -> tuple:
    """
    放大 Spine 纹理图并同步更新 Atlas (支持多页 atlas)。

    algorithm: 超分算法 key (见 ALGORITHMS)

    如果 inplace=True:  原文件→.bak，放大后的文件覆盖原路径，返回原路径。
    如果 inplace=False: 创建 _{scale}x 后缀新文件，返回新路径。
    """
    if scale <= 1:
        return png_path, atlas_path

    # 读取原始 atlas
    with open(atlas_path, "r", encoding="utf-8") as f:
        atlas_text = f.read()

    atlas_dir = os.path.dirname(atlas_path)
    # atlas 引用的所有纹理页 (多页 atlas 需逐页放大)
    tex_names = _atlas_texture_names(atlas_text)
    if not tex_names:
        tex_names = [os.path.basename(png_path)]

    # 放大所有纹理页
    new_pngs = {}
    for name in tex_names:
        tex_path = os.path.join(atlas_dir, name)
        if os.path.isfile(tex_path):
            new_pngs[name] = upscale_image(tex_path, scale, algorithm)

    # 非 inplace: atlas 引用放大后的新文件名; inplace: 保持原名
    if not inplace:
        for name, new_png in new_pngs.items():
            atlas_text = atlas_text.replace(name, os.path.basename(new_png))

    # 缩放坐标
    atlas_text = update_atlas_text(atlas_text, scale)

    # 写入
    base_atlas, ext = os.path.splitext(atlas_path)
    new_atlas = f"{base_atlas}_{scale}x{ext}"
    with open(new_atlas, "w", encoding="utf-8") as f:
        f.write(atlas_text)

    if inplace:
        # 备份所有原纹理页 + atlas
        for name in new_pngs:
            orig = os.path.join(atlas_dir, name)
            bak = orig + ".bak"
            if os.path.exists(bak):
                os.remove(bak)
            os.rename(orig, bak)
        bak = atlas_path + ".bak"
        if os.path.exists(bak):
            os.remove(bak)
        os.rename(atlas_path, bak)
        # 放大后的文件覆盖原路径
        for name, new_png in new_pngs.items():
            os.rename(new_png, os.path.join(atlas_dir, name))
        os.rename(new_atlas, atlas_path)
        return png_path, atlas_path
    else:
        return new_pngs.get(os.path.basename(png_path), png_path), new_atlas
