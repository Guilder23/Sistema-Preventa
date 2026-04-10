#!/usr/bin/env bash
set -e

python manage.py migrate
python manage.py create_default_admin
