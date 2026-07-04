# Guía de Backup - Base de Datos PostgreSQL

**Fecha:** 04 de Julio de 2026  
**Sistema:** SistemaPreventaOficial  
**Tipo de BD:** PostgreSQL  
**Puerto:** 5432

---

## Verificación Realizada

### ✓ Base de Datos Confirmada
- **Motor:** PostgreSQL
- **Nombre BD Oficial:** `sistema_preventa_oficial`
- **Nombre BD Prueba:** `sistema_preventa_prueba` (por deducción)
- **Usuario:** `sistema_user`
- **Host:** localhost
- **Puerto:** 5432

### ✓ Credenciales del Servidor
```
DB_NAME=sistema_preventa_oficial
DB_USER=sistema_user
DB_PASSWORD=Preventa2026Oficial!
DB_HOST=localhost
DB_PORT=5432
```

### ✓ Tablas en la BD
Total: 18 tablas
- auth_group
- auth_group_permissions
- auth_permission
- auth_user
- auth_user_groups
- auth_user_user_permissions
- clientes_cliente
- django_admin_log
- django_content_type
- django_migrations
- django_session
- pedidos_detallepedido
- pedidos_devolucionitem
- pedidos_devolucionpedido
- pedidos_pedido
- productos_movimientoinventario
- productos_producto
- usuarios_perfilusuario

### ✓ Estado de Datos (04/07/2026)
- Clientes: 0 registros
- Usuarios: 1 registro (admin)
- Productos: 0 registros
- Pedidos: 0 registros

---

## Paso 1: Hacer Backup de la BD Oficial

### En el Servidor Hostinger

```bash
# Conectar al servidor
ssh root@187.127.45.61

# Navegar a la carpeta del proyecto
cd /home/guilder/projects/SistemaPreventaOficial

# Crear carpeta de backups si no existe
mkdir -p backups

# Hacer backup con fecha
pg_dump -U sistema_user -h localhost -d sistema_preventa_oficial > backups/backup_oficial_$(date +%Y%m%d_%H%M%S).sql

# Ejemplo de salida esperada:
# backup_oficial_20260704_082700.sql (archivo creado sin mensajes)
```

### Verificar que el backup se creó

```bash
ls -lh backups/
# Deberías ver algo como:
# -rw-r--r-- 1 root root 2.5M Jul  4 08:27 backup_oficial_20260704_082700.sql
```

---

## Paso 2: Descargar el Backup a tu PC

### Desde tu Terminal Windows

```powershell
# Crear carpeta de backups en tu PC
mkdir C:\Users\GUILDER\Desktop\backups

# Descargar el archivo desde el servidor
# Reemplaza la fecha por la actual
scp root@187.127.45.61:/home/guilder/projects/SistemaPreventaOficial/backups/backup_oficial_20260704_082700.sql C:\Users\GUILDER\Desktop\backups\

# Verificar que se descargó
dir C:\Users\GUILDER\Desktop\backups\
```

---

## Paso 3: Restaurar en la BD de Prueba

### Si quieres copiar la BD Oficial a Prueba en el SERVIDOR

```bash
# En el servidor, conectado con SSH

# Opción A: Restaurar directamente (reemplaza todo)
psql -U sistema_user -h localhost -d sistema_preventa_prueba < /home/guilder/projects/SistemaPreventaOficial/backups/backup_oficial_20260704_082700.sql

# Opción B: Crear un dump limpio primero (más seguro)
pg_dump -U sistema_user -h localhost -d sistema_preventa_oficial --no-privileges --no-owner > clean_backup.sql
psql -U sistema_user -h localhost -d sistema_preventa_prueba < clean_backup.sql
```

### Reiniciar Gunicorn de Prueba

```bash
# En el servidor
cd /home/guilder/projects/SistemaPreventaPrueba
source venv/bin/activate

# Encontrar el PID del proceso en puerto 8002
ps aux | grep "8002" | grep -v grep

# Matar el proceso (reemplaza XXXX con el PID)
kill XXXX

# Reiniciar Gunicorn
gunicorn --workers 3 --bind 127.0.0.1:8002 --timeout 60 --access-logfile - --error-logfile - sistemaPreventa.wsgi:application --daemon
```

---

## Paso 4: Verificar que la Restauración Funcionó

### En el Servidor

```bash
# Conectar a la BD de prueba
psql -U sistema_user -h localhost -d sistema_preventa_prueba

# Ver el conteo de tablas
SELECT COUNT(*) as total_tablas FROM information_schema.tables WHERE table_schema='public';

# Ver datos copiados
SELECT 'clientes' as tabla, COUNT(*) as registros FROM clientes_cliente 
UNION ALL 
SELECT 'usuarios' as tabla, COUNT(*) as registros FROM auth_user 
UNION ALL 
SELECT 'productos' as tabla, COUNT(*) as registros FROM productos_producto;

# Salir
\q
```

---

## Paso 5: Usar el Backup Localmente (OPCIONAL)

### Si quieres probar en tu PC

```bash
# 1. Descargar PostgreSQL en tu PC (si no lo tienes)
# Descarga desde: https://www.postgresql.org/download/windows/

# 2. Crear una BD local para pruebas
createdb -U postgres sistema_preventa_local

# 3. Restaurar el backup localmente
psql -U postgres -d sistema_preventa_local < C:\Users\GUILDER\Desktop\backups\backup_oficial_20260704_082700.sql

# 4. Conectar a ella
psql -U postgres -d sistema_preventa_local

# Ver datos
SELECT COUNT(*) FROM clientes_cliente;
SELECT COUNT(*) FROM productos_producto;

\q
```

---

## Paso 6: Usar el Backup en Otro Hostinger (FUTURO)

### Si deployas en otro servidor

```bash
# En el nuevo servidor, después de clonar el proyecto:

# 1. Crear la base de datos vacía
createdb -U postgres sistema_preventa_oficial

# 2. Restaurar el backup
psql -U postgres -d sistema_preventa_oficial < /ruta/al/backup_oficial_20260704_082700.sql

# 3. Cambiar propietario (importante)
psql -U postgres -c "ALTER DATABASE sistema_preventa_oficial OWNER TO sistema_user;"

# 4. Actualizar credenciales en .env del nuevo servidor
# Edit .env con las credenciales del nuevo servidor

# 5. Reiniciar la aplicación
cd /ruta/proyecto
source venv/bin/activate
python manage.py check
gunicorn ...
```

---

## Automatizar Backups (SCRIPT)

### Crear un Script de Backup Automático

**Archivo:** `backup.sh`

```bash
#!/bin/bash

# Configuración
DB_USER="sistema_user"
DB_HOST="localhost"
DB_NAME="sistema_preventa_oficial"
BACKUP_DIR="/home/guilder/projects/SistemaPreventaOficial/backups"
BACKUP_FILE="backup_oficial_$(date +\%Y\%m\%d_\%H\%M\%S).sql"
RETENTION_DAYS=30

# Crear carpeta si no existe
mkdir -p $BACKUP_DIR

# Hacer backup
echo "Iniciando backup de $DB_NAME..."
pg_dump -U $DB_USER -h $DB_HOST -d $DB_NAME > $BACKUP_DIR/$BACKUP_FILE

# Comprimir para ahorrar espacio
gzip $BACKUP_DIR/$BACKUP_FILE

echo "Backup completado: $BACKUP_FILE.gz"

# Limpiar backups antiguos (opcional)
find $BACKUP_DIR -name "backup_oficial_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backups antiguos (>$RETENTION_DAYS días) eliminados"
```

### Usar el Script

```bash
# Hacer ejecutable
chmod +x backup.sh

# Ejecutar manualmente
./backup.sh

# Ejecutar automáticamente cada día a las 3 AM
crontab -e

# Agregar esta línea:
0 3 * * * /home/guilder/projects/SistemaPreventaOficial/backup.sh
```

---

## Comandos Rápidos de Referencia

### Hacer Backup
```bash
pg_dump -U sistema_user -h localhost -d sistema_preventa_oficial > backup.sql
```

### Restaurar Backup
```bash
psql -U sistema_user -h localhost -d sistema_preventa_oficial < backup.sql
```

### Ver Tamaño de la BD
```bash
psql -U sistema_user -h localhost -d sistema_preventa_oficial -c "SELECT pg_size_pretty(pg_database_size('sistema_preventa_oficial'));"
```

### Listar todas las BDs
```bash
psql -U sistema_user -h localhost -l
```

### Descargar desde Servidor
```powershell
scp root@187.127.45.61:/home/guilder/projects/SistemaPreventaOficial/backups/backup.sql C:\Users\GUILDER\Desktop\backups\
```

---

## Recomendaciones

✓ **Hacer backup ANTES de cambios importantes**  
✓ **Guardar backups en al menos 2 lugares** (servidor + tu PC)  
✓ **Probar restauraciones periódicamente** para confirmar que funcionan  
✓ **Comprimir backups antiguos** para ahorrar espacio  
✓ **Usar contraseña fuerte** para acceso a PostgreSQL  
✓ **Documentar los backups** (qué contenían, cuándo se hicieron)

---

## Troubleshooting

### Error: "pg_dump: command not found"
```bash
# Instalar PostgreSQL client tools
apt-get install postgresql-client
```

### Error: "permission denied" al escribir backup
```bash
# Cambiar permisos de la carpeta
chmod 755 /home/guilder/projects/SistemaPreventaOficial/backups
```

### Error: "role 'sistema_user' does not exist"
```bash
# Verificar credenciales en .env
cat .env | grep DB_
```

### El archivo .sql es muy grande
```bash
# Comprimir el backup
gzip backup.sql
# Resultado: backup.sql.gz (mucho más pequeño)

# Para restaurar desde comprimido
gunzip backup.sql.gz
```

---

**Última actualización:** 04/07/2026 - 08:30 UTC
