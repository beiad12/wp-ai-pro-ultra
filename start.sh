#!/bin/bash

echo ""
echo "============================================"
echo " WP AI Pro Ultra — Mac/Linux Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found."
    echo "Install it from https://python.org or via: brew install python3"
    exit 1
fi

echo "[OK] Python found: $(python3 --version)"
echo ""
echo "Installing dependencies..."
echo ""

pip3 install --upgrade streamlit google-generativeai anthropic openai requests beautifulsoup4 apscheduler pandas python-dotenv

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Install failed. Try: sudo pip3 install ..."
    exit 1
fi

echo ""
echo "============================================"
echo " Done! Launching app..."
echo "============================================"
echo ""

# Open browser after 3 seconds
(sleep 3 && open "http://localhost:8501" 2>/dev/null || xdg-open "http://localhost:8501" 2>/dev/null) &

# Launch
streamlit run app.py --server.port 8501 --server.headless false --browser.gatherUsageStats false
