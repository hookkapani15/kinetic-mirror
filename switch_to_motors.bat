@echo off
REM Quick script to switch to motors branch (THIS PC)
echo Switching to motors branch...
git checkout motors
git pull origin motors
echo.
echo You are now on the motors branch (THIS PC)
echo Ready to work on motor features!
echo.
pause

