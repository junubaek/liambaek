$env:PYTHONPATH = (Get-Item .).FullName
Write-Host "Starting FastAPI Backend on port 8000 (Logs: fastapi.log)..."
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000" -NoNewWindow -RedirectStandardOutput "fastapi.log" -RedirectStandardError "fastapi_err.log"

Write-Host "Starting Streamlit Frontend on port 8501 (Logs: streamlit.log)..."
Start-Process -FilePath "python" -ArgumentList "-m", "streamlit", "run", "app/ui/dashboard.py", "--server.port", "8501", "--server.address", "0.0.0.0" -NoNewWindow -RedirectStandardOutput "streamlit.log" -RedirectStandardError "streamlit_err.log"

Write-Host "Services started. Waiting 5s for initialization..."
Start-Sleep -Seconds 5
Get-NetTCPConnection -LocalPort 8000, 8501 -ErrorAction SilentlyContinue
