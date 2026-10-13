@echo off
rem TPM Desk: double-click. Starts the Claude link (your Claude account, through Claude Code)
rem and opens the desk in Edge. The first run installs Python 3.12 for your account if missing.
setlocal
cd /d "%~dp0"
title TPM Desk

rem ---- 1. Python 3.12 (shared with Voice summary) ----
set "PY="
set "NOCC="
for /f "delims=" %%i in ('py -3.12 -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%i"
if defined PY goto :link
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto :link

echo Python 3.12 is not installed. Installing it for your account only (no admin, about 2 minutes)...
set "SETUP=%TEMP%\python-3.12.10-amd64.exe"
curl -L -s -f -o "%SETUP%" https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
if errorlevel 1 (
  echo The download from python.org failed: the network may block it.
  goto :nopython
)
"%SETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0 Shortcuts=0
del "%SETUP%" >nul 2>&1
if exist "%PY%" goto :link
:nopython
echo.
echo Without Python the desk opens, but Claude is not linked. Ask IT for Python 3.12,
echo or see Setup in the desk.
start "" msedge "%~dp0tpm-desk.html"
goto :end

rem ---- 2. Claude link, then the desk ----
:link
where claude >nul 2>&1 && goto :start
if exist "%USERPROFILE%\.local\bin\claude.exe" goto :start
set "NOCC=1"
echo Claude Code is not installed yet: the desk opens, but Claude is not linked.
echo Open Setup in the desk (bottom of the left sidebar) for the one-time steps.
:start
start "TPM Desk - Claude link (keep open)" /min "%PY%" "%~dp0claude_link.py"
timeout /t 2 /nobreak >nul
start "" msedge "%~dp0tpm-desk.html"
if defined NOCC goto :end
exit /b

:end
echo.
pause
