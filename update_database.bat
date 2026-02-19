@echo off
chcp 65001
echo ========================================================
echo       Antigravity Resume Updater (One-Click)
echo ========================================================
echo.
echo [Step 1/2] Uploading New Files to Notion...
python c:\Users\cazam\Downloads\안티그래비티\pdf_to_notion.py
if %errorlevel% neq 0 (
    echo [ERROR] Step 1 Failed!
    pause
    exit /b %errorlevel%
)

echo.
echo [Step 2/2] Processing & Indexing Data for Search...
python c:\Users\cazam\Downloads\안티그래비티\main_ingest.py
if %errorlevel% neq 0 (
    echo [ERROR] Step 2 Failed!
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================================
echo       All Done! New resumes are now searchable.
echo ========================================================
pause
