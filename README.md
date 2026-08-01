# 奥拉星立绘提取器

输入宠物 ID，一键下载奥拉星 H5 端的静态立绘和 Spine 动态立绘，并可将动态立绘导出为可导入 Wallpaper Engine 的网页壁纸。

## 功能

- 输入宠物 ID → 自动下载静态立绘（PNG）
- 自动下载 Spine 动态立绘（.sk/.json + .atlas + .png）
- 界面内预览静态立绘
- 一键导出 Spine 网页壁纸（可直接导入 Wallpaper Engine）
- URL 模板可配置（抓包确认后填入 config.ini 即可）

## 安装

需要 Python 3.10+（64位）。

### 方式一：标准安装（pip 正常时）

```bash
pip install -r requirements.txt
```

### 方式二：PowerShell 安装脚本（pip 有 SSL/网络问题时）

如果 `pip install` 报 SSL 错误（如 `check_hostname requires server_hostname`），
用项目自带的安装脚本（通过 PowerShell 下载 wheel 本地安装，绕过 Python SSL 问题）：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

脚本会自动下载所有 wheel 到 `wheels/` 目录并本地安装。
已验证版本：PyQt5 5.15.11 + PyQt5-Qt5 5.15.2（5.15.15+ 无 Windows wheel）。

## 运行

```bash
python main.py
```

## 使用方法

1. 打开软件，在顶部输入宠物 ID（纯数字）
2. 点击「一键下载」或单独点击「仅静态立绘」/「仅动态立绘」
3. 下载完成后左侧预览静态立绘，右侧查看日志
4. 动态立绘下载成功后，点击「导出为壁纸」生成网页壁纸
5. 导出后会自动打开壁纸文件夹

## 关键：确认 URL 规律（首次使用必看）

软件默认的 URL 模板是**推测值**，可能和实际不同。如果下载失败，需要抓包确认真实 URL：

### 抓包步骤

1. 用 Chrome 打开奥拉星 H5：https://aola.100bt.com/h5/
2. 按 F12 → 切到 Network 面板
3. 在游戏里打开图鉴 / 进入有宠物立绘的场景
4. 在 Network 里筛选 `.png` 或 `.sk` 或 `.atlas`
5. 找到立绘资源，右键 → Copy → Copy link address
6. 观察规律，例如：
   - `https://aola.100bt.com/h5/res/pet/12345.png`
   - `https://aola.100bt.com/h5/res/spine/12345.sk`

### 修改 config.ini

把观察到的真实 URL 填入 config.ini 对应模板，`{id}` 代表宠物 ID：

```ini
[static]
url_template = https://真实路径/{id}.png

[spine]
skeleton_url_template = https://真实路径/{id}.sk
atlas_url_template = https://真实路径/{id}.atlas
texture_url_template = https://真实路径/{id}.png
```

保存后重新运行软件即可。

## 导入 Wallpaper Engine

1. 在软件里「导出为壁纸」后，会生成 `wallpapers/pet_XXXXX/` 文件夹，内含 `index.html` 和资源文件
2. 打开 Wallpaper Engine
3. 点击「打开壁纸编辑器」→ 选择「网页壁纸」类型
4. 文件 → 导入 → 选择刚才生成的 `index.html`
5. 或直接：在 Wallpaper Engine 主界面 → 打开壁纸 → 选择该文件夹的 `index.html`

> 网页壁纸需要联网加载 Spine 运行时（CDN）。如需离线使用，把 `spine-webgl.min.js` 下载到壁纸文件夹并修改 index.html 的 script 路径即可。

## 目录结构

```
项目根目录/
├── main.py                  # 主程序(GUI)
├── config.ini               # URL模板配置(可编辑)
├── requirements.txt         # 依赖清单
├── install.ps1              # 备用安装脚本(pip SSL问题时用)
├── core/
│   ├── url_config.py        # 配置读取
│   ├── fetcher.py           # 资源下载器
│   └── spine_exporter.py    # Spine壁纸生成器
├── web/
│   └── spine_viewer_template.html  # 壁纸HTML模板
├── wheels/                  # wheel缓存(install.ps1用)
├── assets/                  # 下载的资源(运行时生成)
│   ├── static/{id}/{id}.png
│   └── spine/{id}/{id}.sk + .atlas + .png
└── wallpapers/              # 导出的壁纸(运行时生成)
    └── pet_{id}/
        ├── index.html
        ├── skeleton.sk
        ├── texture.atlas
        └── texture.png
```

## 常见问题

**Q: 下载失败怎么办？**
A: 99% 是 URL 模板不对，按上面的「抓包步骤」确认真实 URL 并修改 config.ini。

**Q: 动态立绘导出后壁纸是黑屏？**
A: 可能是 Spine 版本不匹配。奥拉星用的是 Spine 3.8，模板已配 3.8 runtime。如果仍然黑屏，检查浏览器控制台报错，可能需要换 runtime 版本。

**Q: 可以批量下载吗？**
A: 当前版本一次一个 ID。需要批量可在命令行循环调用，或后续扩展批量功能。

**Q: 皮肤立绘怎么下载？**
A: 皮肤的 URL 规律可能和宠物不同（可能带 skin ID 或后缀），抓包确认后在 config.ini 增加对应模板。
