# -*- coding: utf-8 -*-
from cx_Freeze import setup, Executable
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

build_exe_options = {
    "packages": ["PIL", "PIL.Image", "requests", "json", "shutil", "threading"],
    "include_files": [
        (os.path.join(BASE_DIR, "web"), "web"),
        (os.path.join(BASE_DIR, "style.qss"), "style.qss"),
        (os.path.join(BASE_DIR, "config.ini"), "config.ini"),
    ],
    "excludes": ["tkinter", "unittest", "pydoc"],
}

setup(
    name="AolaPetTool",
    version="1.0",
    description="奥拉星立绘提取器",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            target_name="奥拉星立绘提取器.exe",
            base="Win32GUI",
        )
    ],
)
