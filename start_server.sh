#!/bin/bash
# Start Video Server on Linux/Mac
# This allows receivers to browse and download recordings from your PC

cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python3."
    exit 1
fi

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    IP_ADDR=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "localhost")
else
    # Linux
    IP_ADDR=$(hostname -I | awk '{print $1}' || echo "localhost")
fi

echo ""
echo "========================================"
echo "📹 Video Recording Server"
echo "========================================"
echo ""
echo "Server will start on:"
echo "  Local: http://localhost:8000"
echo "  Network: http://$IP_ADDR:8000"
echo ""
echo "Receiver can connect using:"
echo "  python3 video_client.py $IP_ADDR:8000"
echo ""
echo "Or open in browser:"
echo "  http://$IP_ADDR:8000"
echo ""

# Start the server
python3 video_server.py --host 0.0.0.0 --port 8000
