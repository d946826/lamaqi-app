@echo off
chcp 65001 > nul
echo ========================================
echo    抓包转换器 - 手机端打包工具
echo ========================================
echo.

:: 检查Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/4] 正在安装依赖...
pip install -r requirements.txt -q

:: 安装buildozer
echo [2/4] 正在安装buildozer...
pip install buildozer -q

:: 初始化buildozer配置(如果不存在)
if not exist "buildozer.spec" (
    echo [3/4] 初始化buildozer配置...
    buildozer init
) else (
    echo [3/4] buildozer配置已存在，跳过初始化
)

:: 构建APK
echo [4/4] 正在构建APK...
echo.
echo [提示] 首次构建需要下载Android SDK，可能会比较慢
echo        请耐心等待...
echo.

buildozer android debug

if exist "bin\sniff_converter-1.0.0-arm64-v8a_armeabi-v7a-debug.apk" (
    echo.
    echo ========================================
    echo    打包成功！
    echo ========================================
    echo.
    echo APK文件位置: bin\sniff_converter-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
    echo.
    echo 正在打开目录...
    explorer bin
) else (
    echo.
    echo [错误] 打包失败，请检查错误信息
)

pause
