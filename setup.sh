#!/bin/bash
# CloudPaste Setup Script
# This script sets up the development environment

set -e

echo "🚀 CloudPaste Setup"
echo "===================="
echo ""

# Check Python version
echo "📍 Checking Python version..."
python3 --version || (echo "Error: Python 3 not found" && exit 1)
echo ""

# Create virtual environment
echo "📍 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv || {
        echo "Error: Could not create virtual environment"
        echo "You may need to install python3-venv:"
        echo "  sudo apt install python3.13-venv"
        exit 1
    }
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "📍 Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip, setuptools, wheel
echo "📍 Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✓ Upgraded"
echo ""

# Install Python dependencies
echo "📍 Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Check for Node.js
echo "📍 Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found. Frontend dependencies not installed."
    echo "   Install Node.js 18+ and run: cd frontend && npm install"
else
    echo "✓ Node.js $(node --version)"
    echo "📍 Installing frontend dependencies..."
    cd frontend && npm install > /dev/null 2>&1 && cd ..
    echo "✓ Frontend dependencies installed"
fi
echo ""

# Check for Docker
echo "📍 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. You won't be able to start services."
    echo "   Install Docker and run: make docker-up"
else
    echo "✓ Docker installed"
    if ! command -v docker-compose &> /dev/null; then
        echo "⚠️  docker-compose not found."
        echo "   Install docker-compose or use 'docker compose' instead"
    else
        echo "✓ Docker Compose installed"
    fi
fi
echo ""

# Summary
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Start Docker services (if you have Docker):"
echo "   make docker-up"
echo ""
echo "3. Run the development server:"
echo "   make dev"
echo ""
echo "4. Visit the application:"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo "   MinIO Console: http://localhost:9001 (if Docker running)"
echo ""
