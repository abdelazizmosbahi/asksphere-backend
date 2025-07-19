#!/bin/bash
echo "Starting deployment script at $(date)"
set -e  # Exit on any error
echo "Current directory: $(pwd)"
ls -la /home/site/wwwroot

# Upgrade pip
echo "Upgrading pip"
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies from /home/site/wwwroot/requirements.txt"
/usr/bin/python3 -m pip install -r /home/site/wwwroot/requirements.txt --verbose

# Verify gunicorn installation
echo "Verifying gunicorn installation"
/usr/bin/python3 -m pip show gunicorn

# Start gunicorn
echo "Starting gunicorn"
/usr/bin/python3 -m gunicorn --bind=0.0.0.0:8000 --timeout 900 --workers 1 --preload app:app 2>&1 | tee -a /home/LogFiles/Application/asksphere.log
echo "Gunicorn started at $(date)"