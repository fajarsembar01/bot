@echo off
echo ========================================
echo Launch Chrome with Remote Debugging
echo ========================================
echo.

REM Create ChromeProfile directory if not exists
if not exist "C:\selenium\ChromeProfile" (
    echo Creating ChromeProfile directory...
    mkdir "C:\selenium\ChromeProfile"
    echo Directory created: C:\selenium\ChromeProfile
    echo.
)

echo Launching Chrome with remote debugging on port 9222...
echo.
echo IMPORTANT:
echo - DO NOT close this Chrome window while automation is running
echo - Login to Tiket.com in this Chrome window
echo - Keep this window open in background
echo.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\ChromeProfile"

echo.
echo Chrome launched successfully!
echo Remote debugging port: 9222
echo User data directory: C:\selenium\ChromeProfile
echo.
echo Next steps:
echo 1. Login to Tiket.com in the Chrome window that just opened
echo 2. Keep Chrome running (don't close it)
echo 3. Run web panel and configure debugger settings
echo.
pause
