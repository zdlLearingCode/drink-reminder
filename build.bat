@echo off
chcp 65001 >nul
echo 正在打包喝水提醒程序...
pip install pyinstaller -q
pyinstaller --onefile --windowed --name "DrinkWater" drink_water.py
echo.
echo 打包完成！exe 文件在 dist\DrinkWater.exe
pause
