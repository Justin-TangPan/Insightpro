@echo off
cd /d "%~dp0"
copy /b parts\p0.html + parts\p1.html + parts\p2.html + parts\p3.html + parts\p4.html + parts\p5.html + parts\p6.html competitors.html
echo competitors.html generated successfully.
