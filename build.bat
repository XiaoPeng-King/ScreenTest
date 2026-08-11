@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/3] 安装依赖...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo 依赖安装失败
    exit /b 1
)

echo [2/3] 使用 PyInstaller 打包...
python -m PyInstaller --noconfirm --onefile --windowed --name ScreenTest --clean screentest.py
if errorlevel 1 (
    echo 打包失败
    exit /b 1
)

echo [3/3] 完成
echo.
echo EXE 路径: %~dp0dist\ScreenTest.exe
if exist "dist\ScreenTest.exe" (
    for %%A in ("dist\ScreenTest.exe") do echo 文件大小: %%~zA 字节
)
pause
