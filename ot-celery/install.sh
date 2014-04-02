#!/bin/sh
pip install -U celery[redis]
pip install -r requirements.txt
python setup.py develop
