@echo off
chcp 65001 > nul
echo ========================================================
echo        AI Headhunter System Launcher
echo ========================================================

:: 1. Check Python
echo [System Check] Checking for Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo.
        echo [CRITICAL ERROR] Python is NOT installed.
        echo This AI program requires Python to run.
        echo.
        echo Attempting to install Python via Winget...
        winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        
        if %errorlevel% equ 0 (
            echo.
            echo [SUCCESS] Python installed! Please restart this script.
            pause
            exit /b
        ) else (
            echo.
            echo [Winget Failed] Opening Microsoft Store for manual installation...
            start ms-windows-store://pdp/?ProductId=9PJPW5LDXLZ5
            echo.
            echo Please install Python from the Store window that opened.
            echo After installing, CLOSE this window and run 'start.bat' again.
            pause
            exit /b
        )
    )
)
echo [OK] Using python command: %PYTHON_CMD%
echo.

:: 2. Run Ingest
echo [Step 1] Fetching resumes from Notion and Vectorizing...
echo (This may take a moment...)
%PYTHON_CMD% main_ingest.py
if %errorlevel% neq 0 (
    echo [Error] Ingestion failed. Check secrets.json or API limits.
    pause
    exit /b
)

:: 3. Run Matching (Demo)
echo ========================================================
echo [Step 2] Testing Matching Engine...
echo JD: "Ethernet Firmware Engineer (High Speed Interface)"
echo --------------------------------------------------------
%PYTHON_CMD% matcher.py --jd "Ethernet Firmware Engineer, Layer 2/3 protocols, 5 years experience, RoCE"
goto :menu

:run_ui
echo.
echo [Step 3] Launching Web Dashboard...
echo Installing Streamlit (if missing)...
%PYTHON_CMD% -m pip install streamlit -q
echo.
echo Opening Browser...
%PYTHON_CMD% -m streamlit run app.py
goto :menu

:menu
echo.
echo ========================================================
echo [1] Re-Ingest Data (Update DB)
echo [2] Run CMD Search Demo
echo [3] Launch Web Interface (Recommended)
echo [Q] Quit
echo ========================================================
set /p choice="Select Option: "
if "%choice%"=="1" goto :run_ingest
if "%choice%"=="2" goto :run_matcher
if "%choice%"=="3" goto :run_ui
if /i "%choice%"=="q" exit /b
goto :menu

:run_ingest
echo [Step 1] Fetching resumes from Notion and Vectorizing...
%PYTHON_CMD% main_ingest.py
goto :menu

:run_matcher
echo.
echo Search Console:
set /p jd_input="Enter JD Keywords: "
%PYTHON_CMD% matcher.py --jd "%jd_input%"
goto :menu
