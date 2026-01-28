@echo off
setlocal
echo ========================================
echo Launch Additional Chrome Profiles
echo ========================================
echo.
echo Use this to launch separate Chrome instances for multi-account war.
echo Each profile has its own login session and history.
echo.
echo [1] Profile 1 (Main) - Port 9222
echo [2] Profile 2        - Port 9223
echo [3] Profile 3        - Port 9224
echo [4] Profile 4        - Port 9225
echo.

set /p choice="Enter profile number [1-4]: "

if "%choice%"=="1" (
    set PORT=9222
    set DIR=ChromeProfile
) else if "%choice%"=="2" (
    set PORT=9223
    set DIR=ChromeProfile2
) else if "%choice%"=="3" (
    set PORT=9224
    set DIR=ChromeProfile3
) else if "%choice%"=="4" (
    set PORT=9225
    set DIR=ChromeProfile4
) else (
    echo Invalid choice.
    pause
    exit /b
)

if not exist "C:\selenium\%DIR%" (
    echo Creating C:\selenium\%DIR% ...
    mkdir "C:\selenium\%DIR%"
)

echo.
echo Launching Chrome (Profile %choice%) on Port %PORT%...
echo.
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=%PORT% --user-data-dir="C:\selenium\%DIR%"

echo Done!
echo.
echo To run automation for this profile via TERMINAL:
echo python auto_buy.py --debugger "127.0.0.1:%PORT%" --user-data-dir "C:\selenium\%DIR%" --url "URL_TIKET_DISINI" --package "NAMA_TIKET" --open-new-tab
echo.
pause
