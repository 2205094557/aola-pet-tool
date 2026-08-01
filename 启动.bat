@echo off
chcp 65001 >nul
title 奥拉星立绘提取器

echo ============================================
echo   奥拉星立绘提取器 v2.0
echo ============================================
echo.

REM 检查 Python 是否安装
python -c "import sys" 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 安装依赖（如果需要）
echo [首次运行会自动安装依赖，请耐心等待...]
python -m pip install PyQt5 requests Pillow --quiet 2>nul

REM 启动软件
echo [正在启动软件...]
python main.py

if errorlevel 1 (
    echo.
    echo [错误] 软件运行失败
    pause
)
