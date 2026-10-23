@echo off
echo ===============================================================================
echo Starting AI Website Accessibility Auditor - Services Launcher
echo ===============================================================================

echo [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "A11y Backend" cmd /k ".\.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000 --reload"

echo [2/2] Launching Streamlit Interactive Dashboard on http://localhost:8501 ...
start "A11y Dashboard" cmd /k ".\.venv\Scripts\python -m streamlit run frontend/app.py"

echo ===============================================================================
echo Services started!
echo - API Documentation: http://127.0.0.1:8000/docs
echo - Streamlit Dashboard: http://localhost:8501
echo ===============================================================================
pause
