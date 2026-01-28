@echo off
echo ========================================
echo Launch Multi Web Panels for Tiket.com
echo ========================================
echo.
echo Panel 1: http://127.0.0.1:5001 (Controls Chrome Profile 1)
echo Panel 2: http://127.0.0.1:5002 (Controls Chrome Profile 2)
echo Panel 3: http://127.0.0.1:5003 (Controls Chrome Profile 3)
echo.

REM --- Start Panel 1 ---
echo Starting Panel 1 on Port 5001...
start "Panel 1 (Port 5001)" cmd /k "set PANEL_TIKET_PORT=5001 && python web_panel_tiket.py"

REM --- Start Panel 2 ---
echo Starting Panel 2 on Port 5002...
start "Panel 2 (Port 5002)" cmd /k "set PANEL_TIKET_PORT=5002 && python web_panel_tiket.py"

REM --- Start Panel 3 ---
echo Starting Panel 3 on Port 5003...
start "Panel 3 (Port 5003)" cmd /k "set PANEL_TIKET_PORT=5003 && python web_panel_tiket.py"

echo.
echo waiting for servers to start...
timeout /t 3 >nul
echo.
echo Opening browsers...
start http://127.0.0.1:5001
start http://127.0.0.1:5002
start http://127.0.0.1:5003

echo.
echo All panels launched!
echo Configure each panel to connect to its respective Chrome Debugger Address:
echo.
echo [Panel 1] -> Debugger: 127.0.0.1:9222 | User Data: C:\selenium\ChromeProfile
echo [Panel 2] -> Debugger: 127.0.0.1:9223 | User Data: C:\selenium\ChromeProfile2
echo [Panel 3] -> Debugger: 127.0.0.1:9224 | User Data: C:\selenium\ChromeProfile3
echo.
pause
