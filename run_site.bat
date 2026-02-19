@echo off
chcp 65001 > nul
echo [Info] Installing Streamlit...
py -m pip install streamlit --upgrade --quiet
echo.
echo [Info] Launching AI Recruiter...
echo If the browser does not open, please visit: http://localhost:8501
echo.
py -m streamlit run app.py
pause
