@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PAI_HOME=%~dp0"
if "%PAI_HOME:~-1%"=="\" set "PAI_HOME=%PAI_HOME:~0,-1%"

set "CURL=%SystemRoot%\System32\curl.exe"
set "WAIT=%SystemRoot%\System32\timeout.exe"

set "PORT=8000"
if exist "%PAI_HOME%\config.json" (
  for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "$j = Get-Content '%PAI_HOME%\config.json' -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json; if ($j -and $j.app -and $j.app.port) { [string]$j.app.port }"`) do set "PORT=%%p"
)

set "OLLAMA_URL=http://127.0.0.1:11434/api/tags"
set "APP_URL=http://127.0.0.1:%PORT%/api/ping"
set "UI_URL=http://127.0.0.1:%PORT%/"

"%CURL%" -s -m 2 "%OLLAMA_URL%" >nul 2>&1
if not errorlevel 1 goto ollama_ok

set "OLLAMA_EXE="
where ollama >nul 2>&1
if not errorlevel 1 (
  set "OLLAMA_EXE=ollama"
) else if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
  set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
) else if exist "C:\Program Files\Ollama\ollama.exe" (
  set "OLLAMA_EXE=C:\Program Files\Ollama\ollama.exe"
) else if exist "%PAI_HOME%\ollama\ollama.exe" (
  set "OLLAMA_EXE=%PAI_HOME%\ollama\ollama.exe"
)

if not defined OLLAMA_EXE goto ollama_missing

if exist "%PAI_HOME%\ollama-models\" (
  set "OLLAMA_MODELS="
  for /f "usebackq delims=" %%m in (`powershell -NoProfile -Command "$p = Get-Item -LiteralPath '%PAI_HOME%\ollama-models' -ErrorAction SilentlyContinue; if ($p -and $p.Target) { $p.Target }"`) do set "OLLAMA_MODELS=%%m"
  if not defined OLLAMA_MODELS set "OLLAMA_MODELS=%PAI_HOME%\ollama-models"
)

echo Starting Ollama...
start "Ollama" /min "%OLLAMA_EXE%" serve
set /a tries=0

:wait_ollama
set /a tries+=1
if !tries! gtr 60 goto ollama_fail
"%CURL%" -s -m 2 "%OLLAMA_URL%" >nul 2>&1
if errorlevel 1 (
  "%WAIT%" /t 2 /nobreak >nul
  goto wait_ollama
)

:ollama_ok
"%CURL%" -s -m 2 "%APP_URL%" >nul 2>&1
if not errorlevel 1 (
  echo PersonalAI is already running. Opening %UI_URL%
  if exist "%PAI_HOME%\.venv\Scripts\python.exe" (
    "%PAI_HOME%\.venv\Scripts\python.exe" "%PAI_HOME%\open_ui.py" "%UI_URL%"
  ) else (
    start "" "%UI_URL%"
  )
  exit /b 0
)

set "VENV_PY=%PAI_HOME%\.venv\Scripts\python.exe"

if exist "%VENV_PY%" (
  "%VENV_PY%" --version >nul 2>&1
  if not errorlevel 1 goto venv_ok
  echo This copy of the app came from another PC.
  echo Rebuilding its Python environment...
  rmdir /s /q "%PAI_HOME%\.venv" >nul 2>&1
)

set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto no_python

echo First run setup: creating the Python environment and installing packages.
echo This can take several minutes...
%PY% -m venv "%PAI_HOME%\.venv"
if errorlevel 1 goto setup_fail
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r "%PAI_HOME%\requirements.txt"
if errorlevel 1 goto setup_fail

:venv_ok
echo Starting PersonalAI...
cd /d "%PAI_HOME%"
"%VENV_PY%" main.py
exit /b %errorlevel%

:ollama_missing
echo.
echo Ollama was not found on this PC.
echo Install it from ollama.com, or copy a portable install into:
echo   %PAI_HOME%\ollama
pause
exit /b 1

:ollama_fail
echo.
echo Ollama did not start in time. Check that it is installed correctly.
pause
exit /b 1

:no_python
echo.
echo Python was not found on this PC. Install Python 3.12+ from python.org
echo and tick "Add python.exe to PATH" during setup.
pause
exit /b 1

:setup_fail
echo.
echo Environment setup failed. Check your internet connection and try again.
pause
exit /b 1
