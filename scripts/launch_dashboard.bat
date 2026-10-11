@echo off
REM SimuVerify Dashboard Launcher for Windows
echo ======================================================================
echo   Launching SimuVerify Interactive Validation Dashboard
echo ======================================================================
echo.

py -m streamlit run dashboard\app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Trying fallback python launcher...
    python -m streamlit run dashboard\app.py
)

pause
