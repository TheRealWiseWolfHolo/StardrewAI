#!/bin/bash

# Stardew Valley AI Assistant - Quick Launch Script
# This script sets up and runs the Stardew Valley AI assistant

set -e  # Exit on any error

echo "🌟 Stardew Valley AI Assistant - Quick Launch"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

print_status "Python 3 found"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip."
    exit 1
fi

print_status "pip3 found"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    if [ -f ".env.example" ]; then
        print_info "Copying .env.example to .env"
        cp .env.example .env
        print_warning "Please edit .env file and add your OpenAI API key"
        print_info "Then run this script again"
        exit 1
    else
        print_error ".env.example file not found"
        exit 1
    fi
fi

# Check if OpenAI API key is set
if grep -q "your-openai-api-key-here" .env; then
    print_error "Please set your OpenAI API key in the .env file"
    print_info "Edit .env and replace 'your-openai-api-key-here' with your actual API key"
    exit 1
fi

print_status ".env file configured"

# Check if virtual environment should be created
if [ "$1" = "--venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    print_status "Virtual environment activated"
fi

# Install dependencies
print_info "Installing dependencies..."
pip3 install -r requirements.txt

print_status "Dependencies installed"

# Run setup
print_info "Running setup script..."
python3 setup.py

print_status "Setup completed successfully!"

print_info "The web interface should now be available at: http://localhost:8000"
print_info "Press Ctrl+C to stop the server"
