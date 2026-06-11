@echo off
cd /d "%~dp0"
echo [1/3] 拼接友商洞察页面...
copy /b parts\p0.html + parts\p1.html + parts\p2.html + parts\p3.html + parts\p4.html + parts\p5.html + parts\p6.html competitors.html >nul
echo [2/3] 页面生成完成 (competitors.html)
echo [3/3] 启动服务器于 http://localhost:8099
echo.
python server.py --port 8099
pause
