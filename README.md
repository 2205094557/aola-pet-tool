# 奥拉星立绘提取器

输入宠物 ID，一键下载奥拉星 H5 端的静态立绘和 Spine 动态立绘（newbreath 呼吸动画），支持批量搜索、多种背景样式、GIF 录制，并可导出为 Wallpaper Engine 网页壁纸。

## 功能

### 资源下载
- 输入宠物 ID → 自动下载静态立绘（PNG）+ newbreath 呼吸动态立绘（Spine 三件套）
- 宠物蛋资源检测与下载
- 字典缺失的 ID 也能通过资源存在性兜底搜索（显示为 `#ID`）

### 批量搜索
- 支持区间输入（如 `5000-6000`）、逗号分隔（如 `5000,5001,5002`）、混合格式（如 `5000-5010,6000`）
- 可选「检测资源」模式，仅显示有可用资源的宠物
- 字典快速筛选 + 服务器资源实时检测

### 背景样式
- 纯色 / 莫奈渐变 / 油画 / 极光渐变 / 光斑散景 / 噪点颗粒 / 毛玻璃
- 自动取色：从立绘 PNG 提取主色调生成配色方案
- 自定义图片背景

### GIF 录制
- 可调节尺寸、时长、FPS
- 背景与预览一致（渐变/极光/散景/噪点/毛玻璃/图片均支持）
- 录制完成后自动保存到 `downloads/gif_output/`

### Wallpaper Engine 导出
- 一键导出网页壁纸，可直接导入 Wallpaper Engine
- 支持缩放、水平/垂直偏移调节
- 导出后保留背景样式

## 使用方法

### 方式一：直接运行 exe（推荐）

下载 `dist/AolaPetTool.exe`，双击即可运行，无需安装 Python。

### 方式二：从源码运行

```bash
pip install -r requirements.txt
python main.py
```

### 基本操作

1. 在顶部输入宠物 ID（纯数字），或勾选「批量模式」输入 ID 区间
2. 点击搜索，左侧列表显示结果
3. 选中宠物后下载静态立绘 / newbreath 动态立绘
4. 下载完成后可预览、调节缩放和位置、选择背景样式
5. 点击「导出为壁纸」生成 Wallpaper Engine 网页壁纸
6. 点击「导出为 GIF」录制动态立绘 GIF

### 导入 Wallpaper Engine

1. 软件中「导出为壁纸」后会生成 `wallpapers/pet_XXXXX/` 文件夹
2. 打开 Wallpaper Engine → 打开壁纸编辑器 → 选择「网页壁纸」
3. 文件 → 导入 → 选择生成的 `index.html`

## 项目结构

```
项目根目录/
├── main.py                  # 主程序(GUI + 业务逻辑)
├── aola_api.py              # 奥拉星 API 交互(资源检测/下载)
├── config.ini               # URL模板配置
├── style.qss                # Qt 界面样式表
├── requirements.txt         # 依赖清单
├── AolaPetTool.spec         # PyInstaller 打包配置
├── web/
│   ├── wallpaper_template.html   # 壁纸HTML模板
│   ├── gif_template.html         # GIF录制HTML模板
│   └── spine-webgl.js            # Spine 运行时(已内嵌)
├── downloads/               # 下载的资源(运行时生成)
│   ├── static/{id}/{id}.png
│   ├── spine/{id}/  (json + atlas + png)
│   └── gif_output/          # GIF 输出目录
└── wallpapers/              # 导出的壁纸(运行时生成)
    └── pet_{id}/
        ├── index.html
        ├── spine.json
        ├── spine.atlas
        └── spine.png
```

## 打包

```bash
pyinstaller AolaPetTool.spec --noconfirm
```

生成 `dist/AolaPetTool.exe`（约 46 MB，单文件，已内嵌所有资源）。

## 技术栈

- Python 3.10+ / PyQt5
- Spine WebGL Runtime 3.8（动态立绘渲染）
- Pillow（图片处理/主色调提取/GIF生成）
- PyInstaller（打包为 exe）

## 常见问题

**Q: 搜不到某个宠物 ID？**
A: 宠物字典可能未收录新宠物。勾选批量模式 +「检测资源」，或直接搜该 ID，软件会检测服务器上是否存在资源。

**Q: 动态立绘预览是黑屏？**
A: 确保网络可访问奥拉星 H5 资源服务器。软件需要联网加载 Spine 资源。

**Q: GIF 录制不完整？**
A: GIF 尺寸已自动按立绘比例计算，camera 会按目标 canvas 独立计算缩放，确保完整录制。如仍有问题可手动调整录制尺寸。

**Q: 导出壁纸后背景不生效？**
A: 软件内预览和壁纸导出使用相同的背景计算逻辑。Wallpaper Engine 中如需调节，使用右侧控制面板的缩放和偏移即可。
