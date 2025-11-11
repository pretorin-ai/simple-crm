#!/bin/bash

# Simple CRM Development Launcher
# This script starts both the backend and frontend services

set -e

echo "🚀 Starting Simple CRM Development Environment"
echo "=============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install backend dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing backend dependencies..."
    pip install -q -r requirements.txt
    touch venv/.installed
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update SECRET_KEY in backend/.env for production use!"
fi

# Start backend in background
echo "🔧 Starting backend server on http://localhost:8000..."
python run.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../backend.pid

cd ..

# Frontend setup
echo "📦 Setting up frontend..."

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Check for .env.local file
if [ ! -f ".env.local" ]; then
    echo "⚠️  No .env.local file found. Copying from .env.local.example..."
    cp .env.local.example .env.local
fi

# Give backend a moment to start
sleep 2

echo "🎨 Starting frontend server on http://localhost:5173..."
echo ""
echo "=============================================="
echo "✅ Simple CRM is starting!"
echo "=============================================="
echo ""
echo "📍 Frontend: http://localhost:5173"
echo "📍 Backend:  http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "💡 For demo credentials, see README.md"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=============================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -f backend.pid ]; then
        kill $(cat backend.pid) 2>/dev/null || true
        rm backend.pid
    fi
    echo "✅ All services stopped"
    exit 0
}

trap cleanup INT TERM

# Start frontend (this will run in foreground)
npm run dev

# If npm run dev exits, cleanup
cleanup
