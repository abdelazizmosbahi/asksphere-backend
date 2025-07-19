#!/bin/bash
echo "Starting deployment script at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
set -e  # Exit on any error
echo "Current directory: $(pwd)" | tee -a /home/LogFiles/Application/asksphere.log
echo "Listing files in /home/site/wwwroot:" | tee -a /home/LogFiles/Application/asksphere.log
ls -la /home/site/wwwroot | tee -a /home/LogFiles/Application/asksphere.log

# Ensure log directory is writable
mkdir -p /home/LogFiles/Application
chmod -R 777 /home/LogFiles/Application

# Upgrade pip
echo "Upgrading pip at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -m pip install --upgrade pip | tee -a /home/LogFiles/Application/asksphere.log

# Install dependencies
echo "Installing dependencies from /home/site/wwwroot/requirements.txt at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -m pip install -r /home/site/wwwroot/requirements.txt --verbose 2>&1 | tee -a /home/LogFiles/Application/asksphere.log

# Verify gunicorn installation
echo "Verifying gunicorn installation at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -m pip show gunicorn | tee -a /home/LogFiles/Application/asksphere.log

# Test Python imports
echo "Testing Python imports at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -c "import logging; logging.basicConfig(filename='/home/LogFiles/Application/asksphere.log', level=logging.DEBUG); logging.info('Testing imports'); from app import app; logging.info('App imported successfully')" 2>&1 | tee -a /home/LogFiles/Application/asksphere.log

# Preload AI models (lazy-loaded in app)
echo "Preloading AI models (if needed) at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -c "import logging; logging.basicConfig(filename='/home/LogFiles/Application/asksphere.log', level=logging.DEBUG); from app.utils.ai_content_filter import AIContentFilter; from app.models import CommunityValidator; logging.info('AIContentFilter and CommunityValidator imported')" 2>&1 | tee -a /home/LogFiles/Application/asksphere.log

# Start gunicorn
echo "Starting gunicorn at $(date)" | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -m gunicorn --bind=0.0.0.0:8000 --timeout 900 --workers 1 --preload app:app 2>&1 | tee -a /home/LogFiles/Application/asksphere.log
echo "Gunicorn started at $(date)" | tee -a /home/LogFiles/Application/asksphere.log