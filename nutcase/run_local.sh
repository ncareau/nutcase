#!/usr/bin/bash

export FLASK_APP=./app/nutcase_app.py
export CONFIG_PATH=~/nutcase/nutcase/config
export LOG_LEVEL=DEBUG
flask run -h 0.0.0.0
