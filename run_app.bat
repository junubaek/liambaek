@echo off
set PYTHONPATH=.
python -m streamlit run app/ui/dashboard.py --server.port 8501
pause
