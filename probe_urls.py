# -*- coding: utf-8 -*-
"""探测奥拉星H5资源清单文件和宠物立绘URL规律"""
import urllib.request
import ssl

# 绕过SSL验证(环境SSL有问题)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://aola.100bt.com/h5/",
}

def try_url(url):
    """尝试访问URL,返回(状态码,内容前200字符)"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = resp.read()
            return resp.status, len(data), data[:300]
    except urllib.error.HTTPError as e:
        return e.code, 0, b""
    except Exception as e:
        return -1, 0, str(e).encode()

# 1. 探测资源清单文件(常见命名)
print("=" * 60)
print("1. 探测资源清单文件")
print("=" * 60)
manifest_candidates = [
    "https://aola.100bt.com/h5/config.json",
    "https://aola.100bt.com/h5/resconfig.json",
    "https://aola.100bt.com/h5/fileconfig.json",
    "https://aola.100bt.com/h5/assets.json",
    "https://aola.100bt.com/h5/resource.json",
    "https://aola.100bt.com/h5/res/config.json",
    "https://aola.100bt.com/h5/res/resconfig.json",
    "https://aola.100bt.com/h5/res/fileconfig.json",
    "https://aola.100bt.com/h5/main.json",
    "https://aola.100bt.com/h5/index.json",
    "https://aola.100bt.com/h5/version.json",
    "https://aola.100bt.com/h5/res/version.json",
    "https://aola.100bt.com/h5/api/config",
    "https://aola.100bt.com/h5/res/pet.json",
    "https://aola.100bt.com/h5/pet.json",
]
for u in manifest_candidates:
    code, size, head = try_url(u)
    if code == 200 and size > 0:
        print(f"  [HIT] {u}  size={size}")
        print(f"        head: {head[:200]}")
    else:
        print(f"  [miss] {u}  -> {code}")

# 2. 探测宠物立绘常见路径(用ID 10001 试试)
print()
print("=" * 60)
print("2. 探测宠物立绘路径 (ID=10001)")
print("=" * 60)
pet_candidates = [
    "https://aola.100bt.com/h5/res/pet/10001.png",
    "https://aola.100bt.com/h5/res/peticon/10001.png",
    "https://aola.100bt.com/h5/res/petimg/10001.png",
    "https://aola.100bt.com/h5/pet/10001.png",
    "https://aola.100bt.com/h5/peticon/10001.png",
    "https://aola.100bt.com/h5/res/pet/10001/10001.png",
    "https://aola.100bt.com/h5/res/peticon/10001/10001.png",
    "https://aola.100bt.com/h5/res/spine/10001.sk",
    "https://aola.100bt.com/h5/res/spine/10001.json",
    "https://aola.100bt.com/h5/res/pet/10001.sk",
    "https://aola.100bt.com/h5/res/pet/10001.atlas",
]
for u in pet_candidates:
    code, size, head = try_url(u)
    if code == 200 and size > 0:
        kind = "图片" if head[:4] == b"\x89PNG" else "JSON" if head[:1] in (b"{", b"[") else "其他"
        print(f"  [HIT {kind}] {u}  size={size}")
    else:
        print(f"  [miss] {u}  -> {code}")

print()
print("探测完成")
