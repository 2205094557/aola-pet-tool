# 奥拉星立绘提取器 - 依赖安装脚本
# 用途: 当 pip install 因 SSL/网络问题失败时,用此脚本通过 PowerShell 下载 wheel 本地安装
# 用法: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$dl = ".\wheels"
New-Item -ItemType Directory -Force -Path $dl | Out-Null

# 固定版本(经过验证可用)
$pkgs = @(
    @{name="PyQt5";       ver="5.15.11";  pattern="*win_amd64*"},
    @{name="PyQt5-Qt5";   ver="5.15.2";   pattern="*win_amd64*"},
    @{name="PyQt5-sip";   ver="";         pattern="*cp310*win_amd64*"},
    @{name="requests";    ver="";         pattern="*py3*none*any*"},
    @{name="urllib3";     ver="";         pattern="*py3*none*any*"},
    @{name="charset-normalizer"; ver="";  pattern="*cp310*win_amd64*"},
    @{name="idna";        ver="";         pattern="*py3*none*any*"},
    @{name="certifi";     ver="";         pattern="*py3*none*any*"},
    @{name="Pillow";      ver="";         pattern="*cp310*win_amd64*"}
)

foreach ($p in $pkgs) {
    $name = $p.name
    $ver = $p.ver
    $pattern = $p.pattern
    Write-Host "=== $name ==="

    if ($ver -ne "") {
        $j = Invoke-RestMethod "https://pypi.org/pypi/$name/$ver/json"
    } else {
        $j = Invoke-RestMethod "https://pypi.org/pypi/$name/json"
    }

    $f = $j.urls | Where-Object { $_.filename -like $pattern } | Select-Object -First 1
    if ($f) {
        $out = Join-Path $dl $f.filename
        if (-not (Test-Path $out)) {
            Write-Host "  下载 $($f.filename) ..."
            Invoke-WebRequest -Uri $f.url -OutFile $out
        } else {
            Write-Host "  已存在 $($f.filename)"
        }
    } else {
        Write-Host "  WARNING: 未找到匹配的 wheel ($pattern)"
    }
}

Write-Host "`n=== 本地安装 ==="
python -m pip install --no-index --find-links $dl PyQt5==5.15.11 PyQt5-Qt5==5.15.2 PyQt5-sip requests Pillow
Write-Host "`n=== 安装完成 ==="
Write-Host "运行: python main.py"
