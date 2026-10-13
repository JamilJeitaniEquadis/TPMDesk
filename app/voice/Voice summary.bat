@echo off
rem Voice summary: double-click. The first run installs what is missing, then it listens.
setlocal
cd /d "%~dp0"
title Voice summary

rem ---- 1. Python (the "python" Store shortcut does not count) ----
set "PY="
for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%i"
if defined PY goto :packages
for /f "delims=" %%i in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%i"
if defined PY goto :packages
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto :packages

echo Python is not installed. Installing Python 3.12 for your account only (no admin, about 2 minutes)...
set "SETUP=%TEMP%\python-3.12.10-amd64.exe"
curl -L -s -f -o "%SETUP%" https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
if errorlevel 1 (
  echo The download from python.org failed: the network may block it.
  goto :manual
)
"%SETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0 Shortcuts=0
del "%SETUP%" >nul 2>&1
if exist "%PY%" (
  echo Python installed.
  goto :packages
)
:manual
echo.
echo Python could not be installed automatically.
echo Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"),
echo or from the Company Portal / Software Center, then double-click this file again.
goto :end

rem ---- 2. Packages (only the first time) ----
:packages
"%PY%" -c "import soundcard, faster_whisper, anthropic" >nul 2>&1
if not errorlevel 1 goto :key
echo Installing the voice packages (first time only, a few minutes)...
"%PY%" -m pip install --disable-pip-version-check --user -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo The packages could not be installed. Send the lines above to Claude.
  goto :end
)

rem ---- 3. Anthropic API key (only the first time) ----
:key
set "NOSUM="
if defined ANTHROPIC_API_KEY goto :run
echo.
echo Paste your Anthropic API key (console.anthropic.com, starts with sk-ant-),
set /p "KEY=or press Enter to only get the transcript: "
if not defined KEY (
  set "NOSUM=--no-summary"
  goto :run
)
setx ANTHROPIC_API_KEY "%KEY%" >nul
set "ANTHROPIC_API_KEY=%KEY%"
echo Key saved for next time.

rem ---- 4. Listen ----
:run
echo.
set "TITLE="
set /p "TITLE=What are you listening to (Enter to skip)? "
"%PY%" voice_summary.py --title "%TITLE%" %NOSUM%

:end
echo.
pause
