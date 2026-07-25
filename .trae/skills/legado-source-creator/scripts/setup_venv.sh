#!/bin/bash
echo "Setting up Legado Client virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest pytest-cov
echo ""
echo "Virtual environment setup complete."
echo "Run: source .venv/bin/activate"
