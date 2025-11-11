@echo off
REM Simple CRM Development Launcher for Windows
REM This script starts both the backend and frontend services

echo.
echo ========================================
echo Starting Simple CRM Development Environment
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed. Please install Node.js first.
    pause
    exit /b 1
)

REM Backend setup
echo Setting up backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install backend dependencies if needed
if not exist "venv\.installed" (
    echo Installing backend dependencies...
    pip install -q -r requirements.txt
    type nul > venv\.installed
)

REM Check for .env file
if not exist ".env" (
    echo No .env file found. Copying from .env.example...
    copy .env.example .env
    echo Please update SECRET_KEY in backend\.env for production use!
)

REM Start backend in background
echo Starting backend server on http://localhost:8000...
start /B python run.py > ..\backend.log 2>&1

cd ..

REM Frontend setup
echo Setting up frontend...

REM Install frontend dependencies if needed
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

REM Check for .env.local file
if not exist ".env.local" (
    echo No .env.local file found. Copying from .env.local.example...
    copy .env.local.example .env.local
)

REM Give backend a moment to start
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Simple CRM is starting!
echo ========================================
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo For demo credentials, see README.md
echo.
echo Press Ctrl+C to stop all services
echo ========================================
echo.

REM Start frontend (this will run in foreground)
call npm run dev

echo.
echo Services stopped
pause
