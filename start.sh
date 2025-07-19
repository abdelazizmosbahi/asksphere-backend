#!/bin/bash
touch /home/LogFiles/Application/start_sh_debug.txt
echo "start.sh executed at $(date) from $(pwd)" > /home/LogFiles/Application/start_sh_debug.txt
APP_PATH="$(dirname "$(realpath "$0")")"
echo "Starting deployment at $(date) from $APP_PATH" | tee -a /home/LogFiles/Application/asksphere.log
set -e
ls -la "$APP_PATH" | tee -a /home/LogFiles/Application/asksphere.log

# Ensure log directory
mkdir -p /home/LogFiles/Application
chmod -R 777 /home/LogFiles/Application

# Install dependencies
/usr/bin/python3 -m pip install --upgrade pip | tee -a /home/LogFiles/Application/asksphere.log
/usr/bin/python3 -m pip install -r "$APP_PATH/requirements.txt" --verbose 2>&1 | tee -a /home/LogFiles/Application/asksphere.log

# Start gunicorn
/usr/bin/python3 -m gunicorn --bind=0.0.0.0:8000 --timeout 900 --workers 1 --preload --chdir "$APP_PATH" app:app 2>&1 | tee -a /home/LogFiles/Application/asksphere.log