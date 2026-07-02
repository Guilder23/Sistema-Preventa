#!/bin/bash
set -e

# Variables de configuración
PROJECT_NAME="SistemaPreventaOficial"
PROJECT_DIR="/home/guilder/projects/$PROJECT_NAME"
REPO_URL="https://github.com/Guilder23/Sistema-Preventa.git"
REPO_BRANCH="dev"
DB_NAME="sistema_preventa_oficial"
DB_USER="sistema_user"
DB_PASSWORD="Preventa2026Oficial!"
DOMAIN="187.127.45.61"
APP_PORT="8001"

echo "=========================================="
echo "DEPLOY SISTEMA PREVENTA - HOSTINGER"
echo "=========================================="
echo ""

# 1. Crear carpeta del proyecto
echo "[1/10] Creando carpeta del proyecto..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 2. Clonar repositorio
echo "[2/10] Clonando repositorio desde rama $REPO_BRANCH..."
git clone -b "$REPO_BRANCH" "$REPO_URL" .

# 3. Crear venv
echo "[3/10] Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependencias
echo "[4/10] Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn whitenoise

# 5. Crear base de datos PostgreSQL
echo "[5/10] Creando base de datos PostgreSQL..."
sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET default_transaction_deferrable TO on;
ALTER ROLE $DB_USER SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
EOF

# 6. Crear archivo .env para producción
echo "[6/10] Creando archivo .env para producción..."
cat > "$PROJECT_DIR/.env" << EOF
# Configuración de Producción
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1

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
DEFAULT_FROM_EMAIL=noreply@sistema-preventa.com

# CSRF y Seguridad
CSRF_TRUSTED_ORIGINS=http://$DOMAIN,http://www.$DOMAIN,http://localhost,http://127.0.0.1
EOF

chmod 600 "$PROJECT_DIR/.env"

# 7. Ejecutar migraciones
echo "[7/10] Ejecutando migraciones..."
cd "$PROJECT_DIR"
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

# 8. Crear usuario superadmin
echo "[8/10] Creando usuario administrador..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@sistema-preventa.com', 'AdminPreventa2026!')
    print("Usuario admin creado correctamente")
else:
    print("Usuario admin ya existe")
EOF

# 9. Configurar Gunicorn y Systemd
echo "[9/10] Configurando Gunicorn y Systemd..."
sudo tee /etc/systemd/system/sistema-preventa.service > /dev/null << EOF
[Unit]
Description=Sistema Preventa Django Application
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

# 10. Configurar Nginx
echo "[10/10] Configurando Nginx..."
sudo tee /etc/nginx/sites-available/sistema-preventa > /dev/null << EOF
upstream sistema_preventa {
    server 127.0.0.1:$APP_PORT;
}

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

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
        proxy_pass http://sistema_preventa;
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

# Habilitar sitio en Nginx
sudo ln -sf /etc/nginx/sites-available/sistema-preventa /etc/nginx/sites-enabled/sistema-preventa

# Eliminar configuración por defecto si existe
sudo rm -f /etc/nginx/sites-enabled/default

# Verificar sintaxis Nginx
sudo nginx -t

# Recargar configuración
sudo systemctl daemon-reload
sudo systemctl enable sistema-preventa
sudo systemctl start sistema-preventa
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "✓ DEPLOY COMPLETADO EXITOSAMENTE"
echo "=========================================="
echo ""
echo "Información del proyecto:"
echo "  Ubicación: $PROJECT_DIR"
echo "  URL: http://$DOMAIN"
echo "  Base de datos: $DB_NAME"
echo "  Usuario admin: admin"
echo "  Contraseña admin: AdminPreventa2026!"
echo ""
echo "Comandos útiles:"
echo "  Ver logs: journalctl -u sistema-preventa -f"
echo "  Ver estado: systemctl status sistema-preventa"
echo "  Reiniciar: systemctl restart sistema-preventa"
echo ""
