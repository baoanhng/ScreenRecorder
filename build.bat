@echo off
echo Building Screen Recorder...

REM Use user-installed pyinstaller
set PATH=%APPDATA%\Python\Python312\Scripts;%PATH%

pyinstaller --onefile --noconsole --name ScreenRecorder --icon=NONE main.py

echo.
echo Build complete! Check the dist folder for ScreenRecorder.exe
pause
