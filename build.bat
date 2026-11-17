@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   P4can-unlock-more 打包
echo   重建页面 -^> 编译 -^> 出 OTA 包 + 完整包
echo ============================================
echo.
python tools\more\pack_ota.py %*
echo.
if errorlevel 1 (
  echo [失败] 检查上面的输出
) else (
  echo [完成] 产物在 dist\
)
pause
