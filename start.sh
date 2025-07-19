#!/bin/bash
echo "Starting deployment script"
python -m pip install --upgrade pip
pip install -r /home/site/wwwroot/requirements.txt --verbose
echo "Dependencies installed"
gunicorn --bind=0.0.0.0:8000 --timeout 900 --workers 1 --preload app:app
echo "Gunicorn started"