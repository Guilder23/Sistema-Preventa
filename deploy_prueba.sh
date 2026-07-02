#!/bin/bash
set -e

# Variables de configuración del deploy de prueba
PROJECT_NAME="SistemaPreventaPrueba"
PROJECT_DIR="/home/guilder/projects/$PROJECT_NAME"
REPO_URL="https://github.com/Guilder23/Sistema-Preventa.git"
REPO_BRANCH="dev"
DB_NAME="sistema_preventa_prueba"
DB_USER="sistema_user_prueba"
DB_PASSWORD="Preventa2026Prueba!"
DOMAIN="187.127.45.61"
APP_PORT="8002"
NGINX_PORT="8081"
SERVICE_NAME="sistema-preventa-prueba"
NGINX_SITE="sistema-preventa-prueba"

echo "=========================================="
echo "DEPLOY SISTEMA PREVENTA PRUEBA - HOSTINGER"
echo "=========================================="
echo ""

# 1. Crear carpeta del proyecto
echo "[1/11] Creando carpeta del proyecto..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 2. Clonar repositorio o actualizarlo
if [ -d ".git" ]; then
  echo "[2/11] Actualizando repositorio existente..."
  git fetch origin "$REPO_BRANCH"
  git reset --hard "origin/$REPO_BRANCH"
else
  echo "[2/11] Clonando repositorio desde rama $REPO_BRANCH..."
  git clone -b "$REPO_BRANCH" "$REPO_URL" .
fi

# 3. Crear venv
echo "[3/11] Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependencias
echo "[4/11] Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn whitenoise

# 5. Crear base de datos PostgreSQL y usuario
echo "[5/11] Creando base de datos PostgreSQL..."
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';")
if [ "$DB_EXISTS" != "1" ]; then
  sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";"
  echo "  - Base de datos $DB_NAME creada"
else
  echo "  - Base de datos $DB_NAME ya existe"
fi

USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';")
if [ "$USER_EXISTS" != "1" ]; then
  sudo -u postgres psql -c "CREATE USER \"$DB_USER\" WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"
  sudo -u postgres psql -c "ALTER ROLE \"$DB_USER\" SET client_encoding TO 'utf8';"
  sudo -u postgres psql -c "ALTER ROLE \"$DB_USER\" SET default_transaction_isolation TO 'read committed';"
  sudo -u postgres psql -c "ALTER ROLE \"$DB_USER\" SET default_transaction_deferrable TO on;"
  echo "  - Usuario $DB_USER creado"
else
  echo "  - Usuario $DB_USER ya existe"
fi

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";"
sudo -u postgres psql -c "ALTER DATABASE \"$DB_NAME\" OWNER TO \"$DB_USER\";"

# 6. Crear archivo .env para producción de prueba
echo "[6/11] Creando archivo .env para producción..."
cat > "$PROJECT_DIR/.env" << EOF
# Configuración de Producción de prueba
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1

# Base de datos PostgreSQL
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432

# Email (configurable)
EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@sistema-preventa-prueba.com
EOF

chmod 600 "$PROJECT_DIR/.env"

# 7. Ejecutar migraciones
echo "[7/11] Ejecutando migraciones..."
cd "$PROJECT_DIR"
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

# 8. Crear usuario superadmin de prueba
echo "[8/11] Creando usuario administrador de prueba..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin_prueba').exists():
    User.objects.create_superuser('admin_prueba', 'admin_prueba@sistema-preventa.com', 'AdminPreventa2026!')
    print("Usuario admin_prueba creado correctamente")
else:
    print("Usuario admin_prueba ya existe")
EOF

# 9. Configurar Gunicorn y Systemd para prueba
echo "[9/11] Configurando Gunicorn y Systemd..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=Sistema Preventa Django Application (Prueba)
After=network.target

[Service]
Type=notify
User=guilder
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:$APP_PORT \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    sistemaPreventa.wsgi:application

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# 10. Configurar Nginx para prueba
echo "[10/11] Configurando Nginx..."
sudo tee /etc/nginx/sites-available/$NGINX_SITE > /dev/null << EOF
upstream sistema_preventa_prueba {
    server 127.0.0.1:$APP_PORT;
}

server {
    listen $NGINX_PORT;
    listen [::]:$NGINX_PORT;
    server_name $DOMAIN;

    client_max_body_size 50M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://sistema_preventa_prueba;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/$NGINX_SITE /etc/nginx/sites-enabled/$NGINX_SITE

# No eliminamos el sitio oficial; mantenemos ambos activos.

# 11. Recargar servicios
echo "[11/11] Recargando servicios..."
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "✓ DEPLOY PRUEBA COMPLETADO EXITOSAMENTE"
echo "=========================================="
echo ""
echo "Información del proyecto de prueba:"
echo "  Ubicación: $PROJECT_DIR"
echo "  URL: http://$DOMAIN:$NGINX_PORT"
echo "  Base de datos: $DB_NAME"
echo "  Usuario admin: admin_prueba"
echo "  Contraseña admin: AdminPreventa2026!"
echo ""
echo "Comandos útiles:"
echo "  Ver logs: journalctl -u $SERVICE_NAME -f"
echo "  Ver estado: systemctl status $SERVICE_NAME"
echo "  Reiniciar: systemctl restart $SERVICE_NAME"
echo ""