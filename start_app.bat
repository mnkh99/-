@echo off
setlocal
cd /d "%~dp0"

echo Starting I Don't Know Less Than You...
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3.14 app.py
  if %errorlevel%==0 goto :done
  py app.py
  if %errorlevel%==0 goto :done
)

where python >nul 2>nul
if %errorlevel%==0 (
  python app.py
  if %errorlevel%==0 goto :done
)

echo Python was not found.
echo Install Python, then run this file again.
pause

:done
endlocal
