#!/usr/bin/env bash
set -e
echo "Checking Python..."
python3 --version

echo ""
echo "Installing/updating dependencies (this can take a minute)..."
python3 -m pip install --upgrade -r requirements.txt

echo ""
echo "Launching WP Pro Ultra locally at http://localhost:8501 ..."
python3 -m streamlit run app.py
