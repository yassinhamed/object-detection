#!/bin/bash
# Video Client Launcher for Linux/Mac
# Automatically discovers and connects to the video server

cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python3."
    exit 1
fi

echo ""
echo "========================================"
echo "📥 Video Recording Client"
echo "========================================"
echo ""
echo "Auto-discovering server on local network..."
echo ""

# Start the client without arguments (auto-discovery)
python3 video_client.py

