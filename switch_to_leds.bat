@echo off
REM Quick script to switch to leds branch (OTHER PC)
echo Switching to leds branch...
git checkout leds
git pull origin leds
echo.
echo You are now on the leds branch (OTHER PC)
echo Ready to work on LED features!
echo.
pause

