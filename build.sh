#!/usr/bin/env bash
set -o errexit

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate || true

# Recopilar archivos estaticos
python manage.py collectstatic --no-input || true

# Crear usuarios por defecto
python create_default_users.py || true
