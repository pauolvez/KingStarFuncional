@echo off
call venv\Scripts\activate
uvicorn app.main:app --port 8001