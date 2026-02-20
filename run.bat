@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%PYTHONPATH%
python apps\gui\gui_motors.py
pause
