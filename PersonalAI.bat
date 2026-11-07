@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PAI_HOME=F:\MainProjects\PersonalAi"
set "OLLAMA_DIR=F:\AI\ollama"
set "OLLAMA_MODELS=F:\AI\models"
set "OLLAMA_URL=http://127.0.0.1:11434/api/tags"
set "APP_URL=http://127.0.0.1:8000/api/status"
set "UI_URL=http://127.0.0.1:8000/"
set "CURL=%SystemRoot%\System32\curl.exe"
set "WAIT=%SystemRoot%\System32\timeout.exe"

"%CURL%" -s -m 2 "%OLLAMA_URL%" >nul 2>&1
if not errorlevel 1 goto ollama_ok

echo Starting Ollama...
start "Ollama" /min "%OLLAMA_DIR%\ollama.exe" serve
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
  start "" "%UI_URL%"
  exit /b 0
)

echo Starting PersonalAI...
cd /d "%PAI_HOME%"
"%PAI_HOME%\.venv\Scripts\python.exe" main.py
exit /b %errorlevel%

:ollama_fail
echo.
echo Ollama did not start. Check that %OLLAMA_DIR%\ollama.exe exists.
pause
exit /b 1
