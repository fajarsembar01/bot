@echo off

Echo Starting Tiket.com panel...

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
pushd "%SCRIPT_DIR%"

if exist "%ROOT_DIR%\\venv" (
    call "%ROOT_DIR%\\venv\\Scripts\\activate"
)

set PORT=%PANEL_TIKET_PORT%
if "%PORT%"=="" (
  set PORT=5001
)

pip install -q -r "%ROOT_DIR%\\requirements.txt"
set PANEL_TIKET_PORT=%PORT%
python web_panel_tiket.py

popd
