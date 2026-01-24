@echo off

Echo Ticketmaster Helper Bot
Echo =======================
Echo.

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
pushd "%SCRIPT_DIR%"

if exist "%ROOT_DIR%\venv" (
    Echo Activating virtual environment...
    call "%ROOT_DIR%\venv\Scripts\activate"
)

Echo Installing dependencies...
pip install -q -r "%ROOT_DIR%\requirements.txt"

if not exist ".env" (
    Echo No .env found, creating from template...
    copy env_template.txt .env
)

Echo Starting bot...
python bot_ticketmaster.py %*

popd
