@echo off
rem Double-click: transcribes what the laptop plays. Ctrl+C when done.
cd /d "%~dp0"
set /p TITLE=What are you listening to (Enter to skip)? 
python voice_summary.py --title "%TITLE%"
pause
