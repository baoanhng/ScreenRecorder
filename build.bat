@echo off
echo Building ScreenRecorder.exe...
echo.

:: Ensure pyinstaller is available
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install --user pyinstaller
)

:: Build the executable
pyinstaller --onefile --noconsole --name ScreenRecorder --clean main.py

echo.
if exist "dist\ScreenRecorder.exe" (
    echo Build successful!
    echo Output: dist\ScreenRecorder.exe
) else (
    echo Build failed!
)
echo.
pause
