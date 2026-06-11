@echo off
cd /d "%~dp0"
echo 停止旧进程...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo.
echo Business Insight Daily 重启中...
echo   http://localhost:8099
echo.
python server.py
pause
