#!/bin/bash
python -m pip install --upgrade pip
pip install -r /home/site/wwwroot/requirements.txt
gunicorn --bind=0.0.0.0:8000 app:app