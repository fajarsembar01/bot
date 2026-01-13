@echo off
REM Start web panel for bot_simple

cd /d "%~dp0"

echo Cleaning old caches...
if exist "%USERPROFILE%\.wdm" rmdir /s /q "%USERPROFILE%\.wdm"
if exist "%LOCALAPPDATA%\selenium" rmdir /s /q "%LOCALAPPDATA%\selenium"
if exist "%USERPROFILE%\.cache\selenium" rmdir /s /q "%USERPROFILE%\.cache\selenium"
if exist "logs" rmdir /s /q "logs"

echo Starting panel...
python -m pip install -q -r requirements.txt

REM Start panel in a new window (keep window open if error)
start "" cmd /k "python web_panel.py"

REM Open browser
timeout /t 1 >nul
start "" http://127.0.0.1:5000
