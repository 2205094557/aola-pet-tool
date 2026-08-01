# -*- coding: utf-8 -*-
"""cx_Freeze 打包脚本"""

import sys
from cx_Freeze import setup, Executable

# 基础配置
build_exe_options = {
    "packages": ["PyQt5", "PIL", "requests", "json", "threading", "http.server", "socketserver", "webbrowser"],
    "includes": ["PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"],
    "excludes": ["tkinter", "test", "distutils"],
    "include_files": [
        ("web", "web"),
        ("style.qss", "style.qss"),
    ],
    "optimize": 1,
    "silent": True,
}

# 可执行文件配置
base = None
if sys.platform == "win32":
    base = "gui"  # GUI 模式：不显示命令行窗口

target = Executable(
    script="main.py",
    base=base,
    target_name="奥拉星立绘提取器.exe",
)

setup(
    name="aola-spine-extractor",
    version="2.0",
    description="OlaXing pet spine extractor",
    options={"build_exe": build_exe_options},
    executables=[target],
)
