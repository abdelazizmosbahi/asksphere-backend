#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt > pip_install.log 2>&1
echo "Starting Gunicorn..."
gunicorn --workers=2 --bind=0.0.0.0:$PORT --log-level=debug --access-logfile=- --error-logfile=- app:app
