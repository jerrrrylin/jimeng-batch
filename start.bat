@echo off
REM Jimeng Batch Generator Launcher
REM Double-click to start processing queue.json

cd /d "%~dp0"

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.12+ first.
    pause
    exit /b 1
)

REM Check dependencies on first run
python -c "import playwright" 2>nul
if errorlevel 1 (
    echo [SETUP] First run: installing dependencies...
    pip install -r requirements.txt
    playwright install chromium
)

REM Run main program
python jimeng_automation.py config.yaml

echo.
echo [DONE] Press any key to close.
pause >nul