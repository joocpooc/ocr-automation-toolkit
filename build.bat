@echo off
echo Building lairbot executable...
"C:\Users\victh\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe" --onefile --windowed --name lairbot main.py
echo.
echo Done. Find lairbot.exe in the dist\ folder.
pause
