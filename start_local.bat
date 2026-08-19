@echo off
title Khởi động Stocklytics (Host Local)
color 0A

echo ==================================================
echo      KHOI DONG STOCKLYTICS - HOST LOCAL
echo ==================================================
echo.

:: Chuyển đến thư mục gốc chứa file bat
cd /d "%~dp0"

echo [1/2] Dang khoi dong Backend (FastAPI)...
start "Stocklytics Backend" cmd /k "cd backend && set PYTHONIOENCODING=utf-8 && call venv\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Dang khoi dong Frontend (React/Vite)...
start "Stocklytics Frontend" cmd /k "cd frontend && npm run dev -- --host"

echo.
echo ==================================================
echo  XONG! Ca 2 Server da duoc bat o 2 cua so moi.
echo ==================================================
echo.
echo De truy cap tu dien thoai hoac may tinh khac cung mang WiFi:
echo 1. Ban hay mo CMD (Command Prompt) moi va go lenh: ipconfig
echo 2. Tim dong "IPv4 Address", ban se thay IP cua may tinh (Vi du: 192.168.1.15)
echo 3. Tren dien thoai, go vao trinh duyet: http://<IPv4 Address>:5173
echo.
pause
