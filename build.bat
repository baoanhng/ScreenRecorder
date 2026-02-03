@echo off
echo Building ScreenRecorder.exe...
echo.

:: Delete old build artifacts
if exist "dist\ScreenRecorder.exe" (
    echo Removing old EXE...
    del /f "dist\ScreenRecorder.exe" 2>nul
)

:: Build the executable using python -m (works without PATH)
python -m PyInstaller --onefile --noconsole --name ScreenRecorder --clean main.py

echo.
if exist "dist\ScreenRecorder.exe" (
    echo Build successful!
    echo Output: dist\ScreenRecorder.exe
) else (
    echo Build failed! Check the error messages above.
    echo.
    echo If PyInstaller is not installed, run:
    echo   pip install pyinstaller
)
echo.
pause
